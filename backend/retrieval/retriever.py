"""Hybrid retrieval: structural (graph) first for structural questions, with a
semantic fallback; otherwise semantic — itself hybrid: vector candidates
re-ranked with BM25 (lexical) via reciprocal-rank fusion."""
from __future__ import annotations

import logging
import re
from typing import Optional

from .cypher_generator import CypherGenerator
from .lexical import rerank_hybrid
from .router import QueryRouter

logger = logging.getLogger(__name__)

# Vector candidate pool for BM25 re-ranking (bounded so latency stays flat).
_POOL_MULTIPLIER = 5
_POOL_MAX = 50

# Caps for whole-file context injection: local LLMs choke on unbounded prompts.
_EXPLICIT_FILE_MAX = 2
_EXPLICIT_FILE_CHARS = 6000

_FILE_MENTION = re.compile(
    r"([a-zA-Z0-9_/\\.-]+\.(?:py|ts|tsx|js|jsx|go|java|c|cpp|h|hpp|cs|rs|md|txt))"
)


def _norm_path(p: str) -> str:
    return p.replace("\\", "/").lower()


def _scope_to_latest_repo(chroma_result: dict) -> dict:
    """Drop candidates from previously ingested repos and duplicate chunks.

    The Chroma collection is shared across ingests, so a search can surface
    chunks from repos analyzed weeks ago. Metadata carries absolute file
    paths; keep only those under the latest repo path. If nothing survives
    (e.g. the repo dir moved), fall back to the unscoped result.
    """
    import os

    metas = (chroma_result.get("metadatas") or [[]])[0]
    if not metas:
        return chroma_result

    try:
        from api.routes_files import _latest_repo_path
        repo_path = _latest_repo_path()
    except Exception:
        repo_path = None
    if not repo_path:
        return chroma_result
    repo_norm = _norm_path(os.path.abspath(repo_path))

    keep: list[int] = []
    seen: set[tuple] = set()
    for i, m in enumerate(metas):
        fp = _norm_path(str(m.get("file_path") or ""))
        if repo_norm not in fp:
            continue
        key = (fp, m.get("name"))
        if key in seen:
            continue
        seen.add(key)
        keep.append(i)
    if not keep:
        return chroma_result

    out = dict(chroma_result)
    for key in ("ids", "documents", "metadatas", "distances"):
        rows = chroma_result.get(key)
        if rows and rows[0]:
            out[key] = [[rows[0][i] for i in keep if i < len(rows[0])]]
    return out


class HybridRetriever:
    def __init__(self, graph_client, vector_store, cypher_gen: CypherGenerator,
                 router: Optional[QueryRouter] = None) -> None:
        self.graph = graph_client
        self.vectors = vector_store
        self.cypher_gen = cypher_gen
        self.router = router or QueryRouter()

    def retrieve(self, question: str, top_k: int = 10) -> dict:
        result = self._retrieve_core(question, top_k)
        result["explicit_files"] = self._get_explicit_files(question)
        return result

    def _get_explicit_files(self, question: str) -> list[dict]:
        import os
        from api.routes_files import _latest_repo_path, _walk_files

        matches = _FILE_MENTION.findall(question)
        if not matches:
            return []

        repo_path = _latest_repo_path()
        if not repo_path or not os.path.isdir(repo_path):
            return []

        explicit_files: list[dict] = []
        all_files = _walk_files(repo_path, None, 20000)
        for m in sorted(set(matches)):
            if len(explicit_files) >= _EXPLICIT_FILE_MAX:
                break
            m_lower = m.lower().replace("\\", "/")
            for f in all_files:
                f_norm = f.replace("\\", "/")
                if f_norm.lower().endswith(m_lower):
                    full_path = os.path.join(repo_path, f)
                    try:
                        with open(full_path, "r", encoding="utf-8", errors="replace") as file_obj:
                            content = file_obj.read(_EXPLICIT_FILE_CHARS + 1)
                        if len(content) > _EXPLICIT_FILE_CHARS:
                            content = content[:_EXPLICIT_FILE_CHARS] + "\n... [truncated]"
                        explicit_files.append({"path": f_norm, "content": content})
                    except Exception:
                        pass
                    break
        return explicit_files

    def _retrieve_core(self, question: str, top_k: int = 10) -> dict:
        if self.router.classify(question) == "structural":
            cypher = None
            try:
                cypher = self.cypher_gen.generate_cypher(question)
                results = self.graph.query(cypher)
                if results:
                    return {"strategy": "structural", "cypher": cypher, "results": results}
            except Exception as exc:
                # Fall through to semantic on any generation/query failure, but
                # never silently: log so unsafe-Cypher rejections and backend
                # errors are visible instead of masquerading as "no results".
                logger.warning(
                    "structural retrieval failed (cypher=%r); falling back to semantic: %s",
                    cypher, exc,
                )
            # structural produced nothing usable -> semantic fallback
            return {"strategy": "semantic", "fallback_from": "structural",
                    "attempted_cypher": cypher, "results": self._semantic(question, top_k)}

        return {"strategy": "semantic", "results": self._semantic(question, top_k)}

    def _semantic(self, question: str, top_k: int) -> dict:
        """Vector search over a wider pool, re-ranked with BM25 (RRF fusion).

        No metadata filter here: Chroma's ``where`` has no substring operator
        ($contains matches nothing on scalar metadata), so filename-constrained
        questions are handled by BM25 re-ranking plus explicit file injection.
        The collection accumulates chunks from every past ingest, so candidates
        are scoped to the latest repo (and deduped) before re-ranking.
        """
        pool = min(max(top_k * _POOL_MULTIPLIER, top_k), _POOL_MAX)
        candidates = self.vectors.search(question, top_k=pool)
        candidates = _scope_to_latest_repo(candidates)
        return rerank_hybrid(question, candidates, top_k)

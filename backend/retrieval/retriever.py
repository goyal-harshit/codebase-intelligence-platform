"""Hybrid retrieval: structural (graph) first for structural questions, with a
semantic fallback; otherwise semantic — itself hybrid: vector candidates
re-ranked with BM25 (lexical) via reciprocal-rank fusion."""
from __future__ import annotations

import logging
from typing import Optional

from .cypher_generator import CypherGenerator
from .lexical import rerank_hybrid
from .router import QueryRouter

logger = logging.getLogger(__name__)

# Vector candidate pool for BM25 re-ranking (bounded so latency stays flat).
_POOL_MULTIPLIER = 5
_POOL_MAX = 50


class HybridRetriever:
    def __init__(self, graph_client, vector_store, cypher_gen: CypherGenerator,
                 router: Optional[QueryRouter] = None) -> None:
        self.graph = graph_client
        self.vectors = vector_store
        self.cypher_gen = cypher_gen
        self.router = router or QueryRouter()

    def retrieve(self, question: str, top_k: int = 10) -> dict:
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
        """Vector search over a wider pool, re-ranked with BM25 (RRF fusion)."""
        pool = min(max(top_k * _POOL_MULTIPLIER, top_k), _POOL_MAX)
        candidates = self.vectors.search(question, top_k=pool)
        return rerank_hybrid(question, candidates, top_k)

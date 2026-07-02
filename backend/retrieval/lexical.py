"""BM25 lexical scoring + reciprocal-rank fusion for the semantic path.

Chroma's vector search is strong on paraphrase ("where is auth handled?") but
weak on exact identifiers ("get_jwt_strategy"). Okapi BM25 over the candidate
documents is the complement, so the semantic path fetches a wider candidate
pool and re-ranks it by fusing both orderings (RRF). Pure Python — the corpus
is only the candidate pool (≤ ~50 docs), so no index or dependency is needed.

The fused result keeps Chroma's response shape (parallel lists under
``documents`` / ``metadatas`` / ``ids`` / ``distances``) so answer generation
and source extraction downstream are unaffected.
"""
from __future__ import annotations

import math
import re

_K1 = 1.5
_B = 0.75
_RRF_K = 60  # standard damping constant; rank 0 contributes 1/60

_TOKEN = re.compile(r"[A-Za-z]+|\d+")
_CAMEL = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")


def tokenize(text: str) -> list[str]:
    """Code-aware tokens: splits snake_case and camelCase, lowercases."""
    return [t.lower() for t in _TOKEN.findall(_CAMEL.sub(" ", text))]


def bm25_scores(query: str, documents: list[str]) -> list[float]:
    """Okapi BM25 score of *query* against each document."""
    corpus = [tokenize(d) for d in documents]
    n = len(corpus)
    if n == 0:
        return []
    avg_len = sum(len(d) for d in corpus) / n or 1.0

    df: dict[str, int] = {}
    for doc in corpus:
        for term in set(doc):
            df[term] = df.get(term, 0) + 1

    scores = [0.0] * n
    for term in set(tokenize(query)):
        d_f = df.get(term)
        if not d_f:
            continue
        idf = math.log((n - d_f + 0.5) / (d_f + 0.5) + 1)
        for i, doc in enumerate(corpus):
            tf = doc.count(term)
            if tf:
                norm = tf * (_K1 + 1) / (tf + _K1 * (1 - _B + _B * len(doc) / avg_len))
                scores[i] += idf * norm
    return scores


def rerank_hybrid(query: str, chroma_result: dict, top_k: int) -> dict:
    """Fuse vector order (as returned) with BM25 order via RRF; truncate to
    *top_k* keeping Chroma's parallel-list shape. No-op on empty results."""
    documents = (chroma_result.get("documents") or [[]])[0]
    if len(documents) <= 1:
        return chroma_result

    bm25 = bm25_scores(query, documents)
    # Rank positions: vector rank is the incoming order; BM25 rank by score.
    bm25_rank = {i: r for r, i in enumerate(sorted(range(len(documents)),
                                                   key=lambda i: -bm25[i]))}
    fused = sorted(
        range(len(documents)),
        key=lambda i: -(1 / (_RRF_K + i) + 1 / (_RRF_K + bm25_rank[i])),
    )[:top_k]

    out = dict(chroma_result)
    for key in ("ids", "documents", "metadatas", "distances"):
        rows = chroma_result.get(key)
        if rows and rows[0]:
            out[key] = [[rows[0][i] for i in fused if i < len(rows[0])]]
    return out

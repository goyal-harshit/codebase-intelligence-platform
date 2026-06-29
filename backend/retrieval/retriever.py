"""Hybrid retrieval: structural (graph) first for structural questions, with a
semantic (vector) fallback; semantic-only otherwise."""
from __future__ import annotations

import logging
from typing import Optional

from .cypher_generator import CypherGenerator
from .router import QueryRouter

logger = logging.getLogger(__name__)


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
            sem = self.vectors.search(question, top_k=top_k)
            return {"strategy": "semantic", "fallback_from": "structural",
                    "attempted_cypher": cypher, "results": sem}

        return {"strategy": "semantic", "results": self.vectors.search(question, top_k=top_k)}

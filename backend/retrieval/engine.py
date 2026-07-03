"""End-to-end query engine: retrieve -> answer -> cite.

This is the single entry point the API (Phase 7) will call.
"""
from __future__ import annotations

from typing import Optional

from .answer import AnswerGenerator
from .cypher_generator import CypherGenerator
from .retriever import HybridRetriever
from .router import QueryRouter


class QueryEngine:
    def __init__(self, graph_client, vector_store, llm,
                 router: Optional[QueryRouter] = None) -> None:
        self.retriever = HybridRetriever(
            graph_client, vector_store, CypherGenerator(llm), router or QueryRouter()
        )
        self.answerer = AnswerGenerator(llm)

    def answer(self, question: str, top_k: int = 10, history: str = "") -> dict:
        retrieval = self.retriever.retrieve(question, top_k=top_k)
        answer = self.answerer.generate(question, retrieval, history=history)
        return {
            "question": question,
            "strategy": retrieval["strategy"],
            "answer": answer,
            "sources": extract_sources(retrieval),
            "cypher": retrieval.get("cypher"),
        }


def extract_sources(retrieval: dict) -> list[str]:
    """Best-effort list of file paths cited by the retrieved context."""
    seen: list[str] = []

    def add(path: Optional[str]) -> None:
        if path and path not in seen:
            seen.append(path)

    if retrieval.get("explicit_files"):
        for ef in retrieval["explicit_files"]:
            add(ef.get("path"))

    if retrieval.get("strategy") == "structural":
        for row in retrieval.get("results") or []:
            if isinstance(row, dict):
                add(row.get("file") or row.get("file_path"))
    else:
        results = retrieval.get("results") or {}
        for meta in (results.get("metadatas") or [[]])[0]:
            add(meta.get("file_path"))
    return seen

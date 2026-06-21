"""Turns retrieved context into a cited natural-language answer via the LLM."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from llm import LLMClient

ANSWER_PROMPT = """You are a senior software architect analyzing a codebase.
Answer the question using ONLY the provided context. Cite file paths and function names.
If the context doesn't contain the answer, say so clearly.

Question: {question}

Context:
{context}

Answer (be concise, cite sources):"""


class AnswerGenerator:
    def __init__(self, llm: "LLMClient") -> None:
        self.llm = llm

    def generate(self, question: str, retrieval_result: dict) -> str:
        context = self.format_context(retrieval_result)
        prompt = ANSWER_PROMPT.format(question=question, context=context)
        return self.llm.generate(prompt, temperature=0.3)

    @staticmethod
    def format_context(retrieval_result: dict) -> str:
        if retrieval_result.get("strategy") == "structural":
            results = retrieval_result.get("results") or []
            return "\n".join(str(r) for r in results[:20])
        # semantic: Chroma returns parallel lists nested one level deep
        results = retrieval_result.get("results") or {}
        docs = (results.get("documents") or [[]])[0]
        metas = (results.get("metadatas") or [[]])[0]
        return "\n---\n".join(
            f"File: {m.get('file_path')}\nFunction: {m.get('name')}\nCode:\n{d[:500]}"
            for d, m in zip(docs, metas)
        )

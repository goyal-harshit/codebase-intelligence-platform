"""Turns retrieved context into a cited natural-language answer via the LLM."""
from __future__ import annotations

from typing import TYPE_CHECKING

import prompts as _prompts

if TYPE_CHECKING:
    from llm import LLMClient

# Loaded from backend/prompt_templates/answer.txt (Phase 4, bug #4).
ANSWER_PROMPT = _prompts.load("answer")


class AnswerGenerator:
    def __init__(self, llm: "LLMClient") -> None:
        self.llm = llm

    def generate(self, question: str, retrieval_result: dict, history: str = "") -> str:
        context = self.format_context(retrieval_result)
        prompt = _prompts.render(
            "answer", question=question, context=context, history=history
        )
        return self.llm.generate(prompt, temperature=0.3)

    @staticmethod
    def format_context(retrieval_result: dict) -> str:
        parts = []
        
        explicit = retrieval_result.get("explicit_files") or []
        for ef in explicit:
            parts.append(f"--- EXPLICIT FILE REQUESTED BY USER ---\nFile: {ef['path']}\nCode:\n{ef['content']}\n--- END EXPLICIT FILE ---")
            
        if retrieval_result.get("strategy") == "structural":
            results = retrieval_result.get("results") or []
            if results:
                parts.append("\n".join(str(r) for r in results[:20]))
        else:
            # semantic: Chroma returns parallel lists nested one level deep
            results = retrieval_result.get("results") or {}
            docs = (results.get("documents") or [[]])[0]
            metas = (results.get("metadatas") or [[]])[0]
            if docs:
                parts.append("\n---\n".join(
                    f"File: {m.get('file_path')}\nFunction: {m.get('name')}\nCode:\n{d[:500]}"
                    for d, m in zip(docs, metas)
                ))
                
        return "\n\n".join(parts)

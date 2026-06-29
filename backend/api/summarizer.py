"""AI summarization core (Phase 4): render the summarize prompt and call the LLM.

Kept separate from the route so it unit-tests with a fake LLM and no graph/server.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Sequence

import prompts as _prompts

if TYPE_CHECKING:
    from llm import LLMClient

# Bound the context fed to the model so a huge file can't blow up the prompt.
MAX_CONTEXT_CHARS = 8000


def context_from_entities(rows: Sequence[dict]) -> str:
    """Build a compact context from a file's contained entities (graph rows)."""
    lines = []
    for r in rows:
        name = r.get("name") or "?"
        loc = r.get("loc")
        lines.append(f"- {name}" + (f" ({loc} loc)" if loc else ""))
    return "\n".join(lines)


def summarize(llm: "LLMClient", target: str, context: str, kind: str = "file") -> str:
    prompt = _prompts.render(
        "summarize", target=target, context=context[:MAX_CONTEXT_CHARS], kind=kind
    )
    return llm.generate(prompt, temperature=0.3)

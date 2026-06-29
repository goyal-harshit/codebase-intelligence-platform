"""AI code review core (Phase 4): LLM commentary on a diff.

Separated from the route for fake-LLM unit testing. Extends the risk-detection
theme from whole-repo scanning to per-change review.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

import prompts as _prompts

if TYPE_CHECKING:
    from llm import LLMClient

# Cap the diff fed to the model so an enormous changeset can't blow up the prompt.
MAX_DIFF_CHARS = 16000


def review_diff(llm: "LLMClient", diff: str, context: str = "") -> str:
    prompt = _prompts.render("code_review", diff=diff[:MAX_DIFF_CHARS], context=context)
    return llm.generate(prompt, temperature=0.2)

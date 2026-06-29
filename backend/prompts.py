"""Versioned prompt templates (Phase 4, fixes FULL_STACK_GAP_PLAN.md bug #4).

Prompts live as plain-text files under ``backend/prompt_templates/`` instead of
inline string literals, so iterating on a prompt is a file edit (and a reviewable
git diff) rather than a code change + redeploy.

Two substitution styles, because some templates contain literal braces:
* ``render(name, **kw)`` — ``str.format`` substitution (use for templates whose
  only braces are ``{placeholders}``).
* ``load(name)`` — raw text; the caller does its own ``.replace`` (used by the
  Cypher few-shot, whose schema examples contain literal ``{...}``).
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

_DIR = Path(__file__).resolve().parent / "prompt_templates"


@lru_cache
def load(name: str) -> str:
    """Return the raw template text for ``name`` (without the .txt suffix)."""
    return (_DIR / f"{name}.txt").read_text(encoding="utf-8")


def render(name: str, **kwargs: object) -> str:
    """Load ``name`` and fill its ``{placeholders}`` via str.format."""
    return load(name).format(**kwargs)


def reset_cache() -> None:
    """Drop cached template text (used by tests that edit templates on disk)."""
    load.cache_clear()

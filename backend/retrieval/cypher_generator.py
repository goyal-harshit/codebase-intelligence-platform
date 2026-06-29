"""LLM-backed English->Cypher translation with few-shot prompting."""
from __future__ import annotations

import re
from typing import TYPE_CHECKING

import prompts as _prompts

if TYPE_CHECKING:
    from llm import LLMClient

# Any clause that could mutate the graph, the schema, or read off-disk. The LLM
# is only ever asked for read queries, so the presence of any of these means the
# response is malformed or adversarial and must not be executed.
_WRITE_CLAUSE = re.compile(
    r"\b(CREATE|MERGE|DELETE|DETACH|SET|REMOVE|DROP|FOREACH|LOAD\s+CSV|CALL"
    r"|GRANT|REVOKE|USE)\b",
    re.IGNORECASE,
)
# A read query must begin with one of these clauses.
_READ_START = re.compile(r"^\s*(OPTIONAL\s+MATCH|MATCH|WITH|UNWIND|RETURN)\b", re.IGNORECASE)


class UnsafeCypherError(ValueError):
    """The generated Cypher is not a safe, read-only query."""


def assert_read_only(cypher: str) -> str:
    """Reject anything that is not a single read-only query.

    Defends against a jailbroken/garbled model emitting graph-mutating Cypher:
    only MATCH/OPTIONAL MATCH/WITH/UNWIND/RETURN-led queries with no write
    clause and no statement separator are allowed through to the database.
    """
    text = (cypher or "").strip()
    if not text:
        raise UnsafeCypherError("empty cypher")
    if ";" in text.rstrip(";"):
        raise UnsafeCypherError("multiple statements are not allowed")
    if not _READ_START.match(text):
        raise UnsafeCypherError("query must start with a read clause (MATCH/WITH/UNWIND/RETURN)")
    if _WRITE_CLAUSE.search(text):
        raise UnsafeCypherError("write/admin clauses are not allowed")
    return text.rstrip(";").strip()

# Loaded from backend/prompt_templates/cypher_fewshot.txt (Phase 4, bug #4). The
# few-shot schema examples contain literal braces, so callers substitute the
# question via str.replace, never str.format.
CYPHER_FEWSHOT = _prompts.load("cypher_fewshot")


class CypherGenerator:
    def __init__(self, llm: "LLMClient") -> None:
        self.llm = llm

    def generate_cypher(self, question: str) -> str:
        prompt = CYPHER_FEWSHOT.replace("{question}", question)
        raw = self.llm.generate(prompt)
        # Validate before returning so unsafe Cypher never reaches the database;
        # the retriever treats a raised error as "structural failed" and falls
        # back to semantic search.
        return assert_read_only(self._clean(raw))

    @staticmethod
    def _clean(raw: str) -> str:
        text = raw.replace("```cypher", "").replace("```", "").strip()
        # Strip a leading "A:" the model sometimes echoes from the few-shot.
        if text.lower().startswith("a:"):
            text = text[2:].strip()
        return text

"""Routes a question to structural (graph) vs semantic (vector) retrieval."""
from __future__ import annotations

STRUCTURAL_KEYWORDS = {
    "calls", "called by", "imports", "imported by", "inherits",
    "depends on", "dependency", "references", "uses", "affected by",
    "blast radius", "impact", "who calls", "what calls",
}


class QueryRouter:
    def classify(self, question: str) -> str:
        q = question.lower()
        if any(kw in q for kw in STRUCTURAL_KEYWORDS):
            return "structural"
        return "semantic"

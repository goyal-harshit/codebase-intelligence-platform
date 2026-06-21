"""LLM-backed English->Cypher translation with few-shot prompting."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from llm import LLMClient

CYPHER_FEWSHOT = """You translate English questions about a codebase into Cypher graph queries.
Schema: (:File)-[:CONTAINS]->(:Function|:Class)
        (:Function)-[:CALLS]->(:Function)
        (:File)-[:IMPORTS]->(:Module)
        (:Class)-[:INHERITS_FROM]->(:Class)

Examples:
Q: "What functions call validate_user?"
A: MATCH (f:Function)-[:CALLS]->(t:Function {name:'validate_user'}) RETURN f.name AS name, f.file_path AS file

Q: "Which classes inherit from BaseModel?"
A: MATCH (c:Class)-[:INHERITS_FROM]->(b:Class {name:'BaseModel'}) RETURN c.name AS name

Q: "What does auth.py import?"
A: MATCH (f:File {path:'auth.py'})-[:IMPORTS]->(m:Module) RETURN m.name AS name

Now translate this question. Return ONLY the Cypher query, nothing else.
Q: "{question}"
A:"""


class CypherGenerator:
    def __init__(self, llm: "LLMClient") -> None:
        self.llm = llm

    def generate_cypher(self, question: str) -> str:
        prompt = CYPHER_FEWSHOT.replace("{question}", question)
        raw = self.llm.generate(prompt)
        return self._clean(raw)

    @staticmethod
    def _clean(raw: str) -> str:
        text = raw.replace("```cypher", "").replace("```", "").strip()
        # Strip a leading "A:" the model sometimes echoes from the few-shot.
        if text.lower().startswith("a:"):
            text = text[2:].strip()
        return text

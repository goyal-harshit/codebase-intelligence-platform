"""Tests that LLM-generated Cypher is constrained to read-only queries."""
import pytest

from retrieval.cypher_generator import (
    CypherGenerator,
    UnsafeCypherError,
    assert_read_only,
)


def test_allows_read_queries():
    q = "MATCH (f:Function)-[:CALLS]->(t:Function {name:'x'}) RETURN f.name AS name"
    assert assert_read_only(q) == q


def test_strips_trailing_semicolon():
    assert assert_read_only("MATCH (n) RETURN n;") == "MATCH (n) RETURN n"


@pytest.mark.parametrize("q", [
    "CREATE (n:Evil) RETURN n",
    "MATCH (n) DETACH DELETE n",
    "MATCH (n) SET n.pwned = 1 RETURN n",
    "MATCH (n) REMOVE n.name RETURN n",
    "MERGE (n:X) RETURN n",
    "DROP DATABASE codebase",
    "MATCH (n) RETURN n; DROP DATABASE codebase",  # injection via 2nd statement
    "CALL db.labels()",
    "LOAD CSV FROM 'http://x' AS row RETURN row",
    "",
])
def test_rejects_writes_and_injection(q):
    with pytest.raises(UnsafeCypherError):
        assert_read_only(q)


class _FakeLLM:
    def __init__(self, reply: str) -> None:
        self.reply = reply

    def generate(self, prompt: str) -> str:
        return self.reply


def test_generator_rejects_unsafe_model_output():
    gen = CypherGenerator(_FakeLLM("MATCH (n) DETACH DELETE n"))
    with pytest.raises(UnsafeCypherError):
        gen.generate_cypher("delete everything")


def test_generator_returns_clean_read_query():
    gen = CypherGenerator(_FakeLLM("```cypher\nA: MATCH (n) RETURN n\n```"))
    assert gen.generate_cypher("all nodes") == "MATCH (n) RETURN n"

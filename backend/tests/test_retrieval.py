"""Phase 6 tests.

Offline with fakes for the LLM, graph, and vector store — validates routing,
Cypher cleaning, the structural->semantic fallback, context formatting, and
source extraction. A gated OLLAMA_INTEGRATION test hits a live model.
"""
import os

import pytest

from retrieval import (
    AnswerGenerator,
    CypherGenerator,
    HybridRetriever,
    QueryEngine,
    QueryRouter,
    extract_sources,
)


class FakeLLM:
    def __init__(self, response="MATCH (n) RETURN n"):
        self.response = response
        self.prompts = []

    def generate(self, prompt, temperature=0.2):
        self.prompts.append(prompt)
        return self.response


class FakeGraph:
    def __init__(self, rows=None, raises=False):
        self.rows = rows or []
        self.raises = raises
        self.queries = []

    def query(self, command, params=None, language="cypher"):
        self.queries.append(command)
        if self.raises:
            raise RuntimeError("bad cypher")
        return self.rows


class FakeVectors:
    def __init__(self, result=None):
        self.result = result or {"documents": [[]], "metadatas": [[]]}
        self.searches = []

    def search(self, query, top_k=10, filters=None):
        self.searches.append((query, top_k))
        return self.result


# -- router ----------------------------------------------------------------

def test_router_structural_vs_semantic():
    r = QueryRouter()
    assert r.classify("who calls validate_user?") == "structural"
    assert r.classify("what depends on auth?") == "structural"
    assert r.classify("where are passwords handled?") == "semantic"


# -- cypher generation -----------------------------------------------------

def test_cypher_strips_fences_and_label():
    llm = FakeLLM("```cypher\nA: MATCH (f:Function) RETURN f.name\n```")
    out = CypherGenerator(llm).generate_cypher("list functions")
    assert out == "MATCH (f:Function) RETURN f.name"
    assert "list functions" in llm.prompts[0]  # question injected into few-shot


# -- hybrid retriever ------------------------------------------------------

def test_structural_query_used_when_it_returns_rows():
    graph = FakeGraph(rows=[{"name": "f", "file": "a.py"}])
    retr = HybridRetriever(graph, FakeVectors(), CypherGenerator(FakeLLM()))
    out = retr.retrieve("who calls f?")
    assert out["strategy"] == "structural"
    assert out["cypher"] and out["results"]


def test_falls_back_to_semantic_when_graph_errors():
    graph = FakeGraph(raises=True)
    vectors = FakeVectors()
    retr = HybridRetriever(graph, vectors, CypherGenerator(FakeLLM()))
    out = retr.retrieve("who calls f?")
    assert out["strategy"] == "semantic" and out["fallback_from"] == "structural"
    assert vectors.searches  # semantic search was invoked


def test_falls_back_when_structural_empty():
    graph = FakeGraph(rows=[])
    vectors = FakeVectors()
    retr = HybridRetriever(graph, vectors, CypherGenerator(FakeLLM()))
    out = retr.retrieve("what calls f?")
    assert out["strategy"] == "semantic"


def test_semantic_question_skips_graph():
    graph = FakeGraph(rows=[{"name": "x"}])
    retr = HybridRetriever(graph, FakeVectors(), CypherGenerator(FakeLLM()))
    out = retr.retrieve("where is auth handled?")
    assert out["strategy"] == "semantic"
    assert graph.queries == []  # graph untouched


# -- answer formatting -----------------------------------------------------

def test_format_context_structural_and_semantic():
    ag = AnswerGenerator(FakeLLM())
    struct = ag.format_context({"strategy": "structural", "results": [{"name": "f"}]})
    assert "'name': 'f'" in struct
    sem = ag.format_context({
        "strategy": "semantic",
        "results": {"documents": [["def f(): ..."]],
                    "metadatas": [[{"file_path": "a.py", "name": "f"}]]},
    })
    assert "a.py" in sem and "def f()" in sem


# -- sources + engine ------------------------------------------------------

def test_extract_sources_dedupes():
    retrieval = {"strategy": "structural",
                 "results": [{"file": "a.py"}, {"file": "a.py"}, {"file": "b.py"}]}
    assert extract_sources(retrieval) == ["a.py", "b.py"]


def test_engine_answer_end_to_end():
    graph = FakeGraph(rows=[{"name": "f", "file": "a.py"}])

    class _PromptAwareLLM:
        # The Cypher step must now return a valid read-only query (it is
        # validated before execution); the answer step returns prose.
        def generate(self, prompt, temperature=0.2):
            if "into Cypher" in prompt:
                return "MATCH (f:Function)-[:CALLS]->(t:Function {name:'f'}) RETURN f.name AS name, f.file_path AS file"
            return "It is in a.py"

    engine = QueryEngine(graph, FakeVectors(), _PromptAwareLLM())
    result = engine.answer("who calls f?")
    assert result["strategy"] == "structural"
    assert result["answer"] == "It is in a.py"
    assert result["sources"] == ["a.py"]


@pytest.mark.skipif(
    not os.getenv("OLLAMA_INTEGRATION"),
    reason="set OLLAMA_INTEGRATION=1 with a running Ollama to run",
)
def test_integration_ollama_generates():
    from llm import OllamaClient

    out = OllamaClient().generate("Say 'ok' and nothing else.")
    assert isinstance(out, str) and out

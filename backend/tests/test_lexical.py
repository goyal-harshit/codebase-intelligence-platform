"""BM25 lexical layer + hybrid (vector ∪ BM25) re-ranking."""
from retrieval import HybridRetriever, CypherGenerator
from retrieval.lexical import bm25_scores, rerank_hybrid, tokenize


def test_tokenize_splits_code_identifiers():
    assert tokenize("get_jwt_strategy") == ["get", "jwt", "strategy"]
    assert tokenize("HybridRetriever.retrieve()") == ["hybrid", "retriever", "retrieve"]


def test_bm25_prefers_exact_identifier_match():
    docs = [
        "helper that formats dates for reports",
        "def get_jwt_strategy(): return JWTStrategy(secret)",
        "class UserManager handles registration",
    ]
    scores = bm25_scores("where is get_jwt_strategy defined?", docs)
    assert scores.index(max(scores)) == 1


def test_bm25_empty_corpus():
    assert bm25_scores("anything", []) == []


def _chroma(docs, metas=None):
    return {
        "ids": [[f"id{i}" for i in range(len(docs))]],
        "documents": [docs],
        "metadatas": [metas or [{"i": i} for i in range(len(docs))]],
        "distances": [[i * 0.1 for i in range(len(docs))]],
    }


def test_rerank_promotes_lexical_match_and_keeps_shape():
    # Vector order puts the exact-identifier doc last; fusion should lift it.
    docs = [
        "authentication and session helpers",
        "user login and password hashing",
        "def get_jwt_strategy(): return JWTStrategy(AUTH_SECRET)",
    ]
    out = rerank_hybrid("get_jwt_strategy", _chroma(docs), top_k=2)
    assert len(out["documents"][0]) == 2
    assert any("get_jwt_strategy" in d for d in out["documents"][0])
    # Parallel lists stay aligned with the reordered documents.
    top_doc_idx = docs.index(out["documents"][0][0])
    assert out["ids"][0][0] == f"id{top_doc_idx}"
    assert out["metadatas"][0][0] == {"i": top_doc_idx}


def test_rerank_noop_on_empty_or_single():
    empty = {"documents": [[]], "metadatas": [[]]}
    assert rerank_hybrid("q", empty, 5) is empty
    single = _chroma(["only doc"])
    assert rerank_hybrid("q", single, 5) is single


def test_retriever_semantic_path_uses_pool_and_truncates():
    class FakeLLM:
        def generate(self, prompt, temperature=0.2):
            return "MATCH (n) RETURN n"

    class FakeVectors:
        def __init__(self):
            self.searches = []

        def search(self, query, top_k=10, filters=None):
            self.searches.append(top_k)
            docs = [f"document number {i}" for i in range(top_k)]
            return _chroma(docs)

    vectors = FakeVectors()
    r = HybridRetriever(graph_client=None, vector_store=vectors,
                        cypher_gen=CypherGenerator(FakeLLM()))
    out = r.retrieve("where are passwords handled?", top_k=4)
    assert out["strategy"] == "semantic"
    assert vectors.searches == [20]  # 4 * pool multiplier
    assert len(out["results"]["documents"][0]) == 4

"""Phase 3 tests.

Unit tests run offline with a deterministic fake embedder and a fake Chroma
collection — no model download, no server. A live integration test (real model
+ Chroma) is gated behind CHROMA_INTEGRATION.
"""
import os

import pytest

from ast_parser import CodeEntity
from vector_db import CodeChunker, VectorStoreBuilder


class FakeEmbedder:
    """Deterministic 4-dim vectors derived from text length — no ML deps."""

    def __init__(self):
        self.calls = []

    def encode(self, texts):
        texts = list(texts)
        self.calls.append(texts)
        return [[float(len(t)), 1.0, 0.0, 0.0] for t in texts]


class FakeCollection:
    def __init__(self):
        self.upserts = []
        self.queries = []

    def upsert(self, ids, embeddings, documents, metadatas):
        self.upserts.append(
            {"ids": ids, "embeddings": embeddings,
             "documents": documents, "metadatas": metadatas}
        )

    def query(self, query_embeddings, n_results, where=None):
        self.queries.append({"emb": query_embeddings, "n": n_results, "where": where})
        return {"ids": [["x"]], "documents": [["doc"]], "metadatas": [[{"name": "x"}]]}


class StatefulFakeCollection(FakeCollection):
    """Remembers upserted metadata so ``.get`` behaves like real Chroma —
    exercises the unchanged-chunk skip instead of its lookup-failure fallback."""

    def __init__(self):
        super().__init__()
        self.store = {}

    def upsert(self, ids, embeddings, documents, metadatas):
        super().upsert(ids, embeddings, documents, metadatas)
        for id_, meta in zip(ids, metadatas):
            self.store[id_] = meta

    def get(self, ids, include=None):
        found = [i for i in ids if i in self.store]
        return {"ids": found, "metadatas": [self.store[i] for i in found]}


SAMPLE = [
    CodeEntity(id="f1", type="function", name="validate_password", file_path="auth.py",
               language="python", line_start=1, line_end=5, signature="validate_password(pw)",
               docstring="Check a user password.", cyclomatic_complexity=3,
               lines_of_code=5, raw_code="def validate_password(pw): ..."),
    CodeEntity(id="f2", type="function", name="hash_token", file_path="auth.py",
               language="python", line_start=7, line_end=9),
    CodeEntity(id="c1", type="class", name="User", file_path="models.py",
               language="python", line_start=1, line_end=30),
]


def test_chunk_contains_signal_and_metadata():
    chunk = CodeChunker().chunk_entity(SAMPLE[0])
    assert chunk["id"] == "f1"
    assert "validate_password" in chunk["text"]
    assert "auth.py" in chunk["text"]
    assert "Check a user password." in chunk["text"]
    assert chunk["metadata"] == {
        "entity_type": "function", "name": "validate_password",
        "file_path": "auth.py", "language": "python",
        "complexity": 3, "loc": 5,
    }


def test_embed_and_store_batches():
    emb, coll = FakeEmbedder(), FakeCollection()
    builder = VectorStoreBuilder(embedder=emb, collection=coll)
    stored = builder.embed_and_store(SAMPLE, batch_size=2)
    assert stored == 3
    assert len(coll.upserts) == 2  # 2 + 1
    # ids round-trip and embeddings line up with documents
    all_ids = [i for u in coll.upserts for i in u["ids"]]
    assert all_ids == ["f1", "f2", "c1"]
    for u in coll.upserts:
        assert len(u["embeddings"]) == len(u["ids"]) == len(u["documents"])


def test_reingest_skips_unchanged_chunks():
    emb, coll = FakeEmbedder(), StatefulFakeCollection()
    builder = VectorStoreBuilder(embedder=emb, collection=coll)
    assert builder.embed_and_store(SAMPLE) == 3

    emb.calls.clear()
    progress = []
    embedded = builder.embed_and_store(
        SAMPLE, on_progress=lambda done, total: progress.append((done, total))
    )
    assert embedded == 0
    assert emb.calls == []  # the model was never touched
    assert progress[-1] == (3, 3)  # skipped chunks still reach 100%


def test_reingest_reembeds_only_changed_chunk():
    import dataclasses

    emb, coll = FakeEmbedder(), StatefulFakeCollection()
    builder = VectorStoreBuilder(embedder=emb, collection=coll)
    builder.embed_and_store(SAMPLE)

    emb.calls.clear()
    coll.upserts.clear()
    changed = [dataclasses.replace(SAMPLE[0], raw_code="def validate_password(pw): return None")] + SAMPLE[1:]
    assert builder.embed_and_store(changed) == 1
    assert [i for u in coll.upserts for i in u["ids"]] == ["f1"]


def test_search_embeds_query_and_passes_filter():
    emb, coll = FakeEmbedder(), FakeCollection()
    builder = VectorStoreBuilder(embedder=emb, collection=coll)
    builder.search("password validation", top_k=7, filters={"language": "python"})
    assert coll.queries[0]["n"] == 7
    assert coll.queries[0]["where"] == {"language": "python"}
    # query text was embedded exactly once, as a single-item list
    assert emb.calls[-1] == ["password validation"]


def test_import_does_not_require_chroma_or_torch():
    # Importing the package must not pull heavy deps; only .collection access does.
    import vector_db  # noqa: F401


@pytest.mark.skipif(
    not os.getenv("CHROMA_INTEGRATION"),
    reason="set CHROMA_INTEGRATION=1 with a live Chroma + model to run",
)
def test_integration_semantic_search():
    builder = VectorStoreBuilder(collection_name="codebase_test")
    builder.embed_and_store(SAMPLE)
    results = builder.search("function that validates user passwords", top_k=3)
    top_names = [m["name"] for m in results["metadatas"][0]]
    assert "validate_password" in top_names

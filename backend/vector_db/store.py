"""ChromaDB-backed vector store: embed parsed entities and semantically search.

The embedder and the Chroma collection are both injectable so unit tests run
offline (no model download, no server). In production both are created lazily
from env config: CHROMA_HOST (default localhost), CHROMA_PORT (8000).
"""
from __future__ import annotations

import hashlib
import os
from typing import TYPE_CHECKING, Callable, Iterable, Optional

from .chunker import CodeChunker
from .embedder import Embedder, SentenceTransformerEmbedder

if TYPE_CHECKING:
    from ast_parser import CodeEntity

COLLECTION_NAME = "codebase_embeddings"


class VectorStoreBuilder:
    def __init__(
        self,
        embedder: Optional[Embedder] = None,
        collection=None,
        host: Optional[str] = None,
        port: Optional[int] = None,
        collection_name: str = COLLECTION_NAME,
    ) -> None:
        self.embedder: Embedder = embedder or SentenceTransformerEmbedder()
        self.chunker = CodeChunker()
        self.collection_name = collection_name
        self._collection = collection
        self._host = host or os.getenv("CHROMA_HOST", "localhost")
        self._port = port or int(os.getenv("CHROMA_PORT", "8000"))

    @property
    def collection(self):
        """Lazily connect to Chroma and get-or-create the collection."""
        if self._collection is None:
            import chromadb

            client = chromadb.HttpClient(host=self._host, port=self._port)
            self._collection = client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"},
            )
        return self._collection

    def embed_and_store(
        self,
        entities: Iterable[CodeEntity],
        batch_size: int = 128,
        on_progress: Optional[Callable[[int, int], None]] = None,
    ) -> int:
        """Embed chunks and upsert them; returns the number actually embedded.

        Embedding is the pipeline's slowest step (CPU-only model, minutes for a
        large repo), and re-ingesting a repo mostly re-feeds identical text —
        so each chunk carries a content hash in its metadata and chunks whose
        stored hash already matches are skipped without touching the model.
        ``on_progress(done, total)`` counts skipped chunks as done so the
        percentage stays truthful either way.
        """
        chunks = [self.chunker.chunk_entity(e) for e in entities]
        total = len(chunks)
        done = 0
        embedded = 0
        for i in range(0, total, batch_size):
            batch = chunks[i:i + batch_size]
            for c in batch:
                c["metadata"]["content_sha1"] = hashlib.sha1(
                    c["text"].encode("utf-8")
                ).hexdigest()
            unchanged = self._unchanged_ids(batch)
            fresh = [c for c in batch if c["id"] not in unchanged]
            if fresh:
                texts = [c["text"] for c in fresh]
                embeddings = self.embedder.encode(texts)
                self.collection.upsert(
                    ids=[c["id"] for c in fresh],
                    embeddings=embeddings,
                    documents=texts,
                    metadatas=[c["metadata"] for c in fresh],
                )
                embedded += len(fresh)
            done += len(batch)
            if on_progress:
                on_progress(done, total)
        return embedded

    def _unchanged_ids(self, batch: list[dict]) -> set[str]:
        """Ids in ``batch`` whose stored content hash matches the current one.

        A lookup failure must never break ingestion — fall back to "nothing
        matches" so everything is (re-)embedded.
        """
        try:
            existing = self.collection.get(
                ids=[c["id"] for c in batch], include=["metadatas"]
            )
            stored = {
                id_: (meta or {}).get("content_sha1")
                for id_, meta in zip(existing["ids"], existing["metadatas"])
            }
        except Exception:
            return set()
        return {
            c["id"]
            for c in batch
            if stored.get(c["id"]) and stored[c["id"]] == c["metadata"]["content_sha1"]
        }

    def search(self, query: str, top_k: int = 10, filters: Optional[dict] = None):
        query_embedding = self.embedder.encode([query])
        return self.collection.query(
            query_embeddings=query_embedding,
            n_results=top_k,
            where=filters,
        )

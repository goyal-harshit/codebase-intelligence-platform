"""ChromaDB-backed vector store: embed parsed entities and semantically search.

The embedder and the Chroma collection are both injectable so unit tests run
offline (no model download, no server). In production both are created lazily
from env config: CHROMA_HOST (default localhost), CHROMA_PORT (8000).
"""
from __future__ import annotations

import os
from typing import TYPE_CHECKING, Iterable, Optional

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

    def embed_and_store(self, entities: Iterable[CodeEntity], batch_size: int = 64) -> int:
        chunks = [self.chunker.chunk_entity(e) for e in entities]
        stored = 0
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]
            texts = [c["text"] for c in batch]
            embeddings = self.embedder.encode(texts)
            self.collection.upsert(
                ids=[c["id"] for c in batch],
                embeddings=embeddings,
                documents=texts,
                metadatas=[c["metadata"] for c in batch],
            )
            stored += len(batch)
        return stored

    def search(self, query: str, top_k: int = 10, filters: Optional[dict] = None):
        query_embedding = self.embedder.encode([query])
        return self.collection.query(
            query_embeddings=query_embedding,
            n_results=top_k,
            where=filters,
        )

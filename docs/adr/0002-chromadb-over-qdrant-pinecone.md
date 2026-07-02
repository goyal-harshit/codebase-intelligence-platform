# ADR 0002: ChromaDB over Qdrant / Pinecone

## Status

Accepted (v1.0, shipped). `PROJECT_PLAN.md` §3 marks this as a deliberate,
do-not-churn substitution.

## Context

The platform needs a vector store for code-chunk embeddings with cosine similarity
search. Pinecone is a paid managed service — excluded outright by the ₹0 constraint.
Qdrant is free and self-hostable, but the workload here is modest: one collection
(`codebase_embeddings`), batch upserts during ingestion, top-k search at query time.

## Decision

Use ChromaDB, self-hosted as a single Docker container (`chroma` service in
`docker-compose.yml`, host port 8003). The integration is deliberately thin:
`backend/vector_db/store.py` connects with `chromadb.HttpClient` using
`CHROMA_HOST`/`CHROMA_PORT`, creates the collection with `{"hnsw:space": "cosine"}`,
and exposes `embed_and_store` / `search`. The embedder and collection are injectable,
so the test suite runs offline with fakes (no model download, no server).

## Consequences

- Zero cost, one container, no auth/cluster configuration to manage.
- The Chroma API surface used is small (get_or_create_collection, upsert, query), so
  swapping to Qdrant later would touch only `backend/vector_db/store.py`.
- Trade-off: Chroma lacks Qdrant's advanced filtering, quantization, and horizontal
  scaling — acceptable for single-repo, single-node scale.
- Gotcha: inside the compose network Chroma is `chroma:8000`; from the host it is
  `localhost:8003`. Misconfiguring `CHROMA_PORT` is a known foot-gun.

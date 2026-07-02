# Documentation

Docs for the Codebase Intelligence Platform (roadmap v1.1/v1.2 — see `PROJECT_PLAN.md`).

## Contents

- [Architecture](architecture.md) — services, AI pipeline (AST → graph → embeddings →
  hybrid retrieval → local LLM), auth layers, background jobs, request/data-flow diagram.
- [API Guide](api-guide.md) — auth flows, every `/api/v1` route grouped by area, curl
  examples, Swagger at `/docs`.
- [Deployment at ₹0](deployment-free-tier.md) — local `docker compose up` (recommended)
  and honest free-tier cloud options (Vercel / Render / Fly / Neon / Upstash), including
  the "no free GPU" reality for the LLM.

## Architecture Decision Records

- [ADR 0001 — Local-first, zero-budget stack](adr/0001-local-first-zero-budget.md)
- [ADR 0002 — ChromaDB over Qdrant / Pinecone](adr/0002-chromadb-over-qdrant-pinecone.md)
- [ADR 0003 — ArcadeDB over Neo4j](adr/0003-arcadedb-over-neo4j.md)
- [ADR 0004 — Ollama and open-weight LLMs](adr/0004-ollama-open-weight-llms.md)
- [ADR 0005 — FastAPI-Users for auth](adr/0005-fastapi-users-auth.md)

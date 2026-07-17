# Documentation

Docs for the Codebase Intelligence Platform (see `PROJECT_PLAN.md` for the
plan and `../CHANGELOG.md` for release history).

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

## Screenshots

The main workspace pages (also embedded in the top-level README):

- [Dashboard](screenshots/dashboard.png) — stats, risks, hotspot heatmap
- [Ask the codebase](screenshots/query.png) — hybrid-retrieval Q&A with sources
- [Change impact](screenshots/impact.png) — blast-radius force graph
- [Security / SAST](screenshots/security.png) — builtin + Bandit + Ruff findings
- [Refactoring](screenshots/refactor.png) — ranked recommendations
- [Wiki](screenshots/wiki.png) — auto-generated per-module documentation

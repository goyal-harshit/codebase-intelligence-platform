# ADR 0001: Local-first, zero-budget stack

## Status

Accepted (v1.0, shipped).

## Context

The project must be reproducible by anyone with a laptop and no credit card
(`PROJECT_PLAN.md` §2): no paid APIs (OpenAI/Anthropic), no paid cloud, no paid tiers.
It is also a portfolio project — reviewers should get the full stack running with one
command, offline if necessary.

## Decision

Every dependency is free and open source, and the entire stack runs locally via
`docker compose up` (`docker-compose.yml`): PostgreSQL, Redis, ArcadeDB Community,
ChromaDB, MinIO, the FastAPI backend, a Celery worker, and the Next.js frontend.
The LLM is a local Ollama process on the host (reached via `host.docker.internal`).
Components degrade gracefully when a piece is missing:

- no `DATABASE_URL` → SQLite file (`backend/db/`)
- no `MINIO_ENDPOINT` → local filesystem storage (`backend/storage/`)
- no slowapi → no-op rate limiter (`backend/api/ratelimit.py`)
- no reachable LLM → retrieval still works; answer generation fails with a 503, not a crash

## Consequences

- Anyone can run and audit the full platform at ₹0; CI (`.github/workflows/ci.yml`) runs
  the 220+ tests offline.
- No managed-service lock-in; free-tier hosting (Vercel/Render/Neon) is an optional
  overlay, not a requirement (see `docs/deployment-free-tier.md`).
- Trade-off: answer quality is bounded by open-weight models that fit on the user's
  hardware, and there is no free GPU hosting — the LLM stays "bring your own machine".
- Trade-off: more moving parts to self-host (7 containers) than a managed SaaS stack.

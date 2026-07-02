# Project Plan — Codebase Intelligence Platform

**The single source of truth.** All previous plan documents
(`CODEBASE_INTELLIGENCE_MASTER_PLAN.md`, `ENTERPRISE_CODEBASE_INTELLIGENCE_ROADMAP.md`,
`FULL_STACK_GAP_PLAN.md`, `PROJECT_STATUS_AND_FIX_PLAN.md`) are deleted and superseded
by this file. Update this file when scope changes; do not create parallel plans.

## 1. What this is

> An autonomous software-engineering platform that understands, documents,
> analyzes, and improves large-scale repositories using open-source LLMs,
> static analysis, vector search, a code knowledge graph, and distributed
> backend services.

Not "an AI chatbot" — an open-source developer platform, built incrementally,
released in versions, reproducible with one command.

## 2. Hard constraints

- **₹0 budget.** No paid APIs (no OpenAI/Anthropic), no paid cloud (no AWS/Azure/GCP),
  no paid tiers of anything. Every dependency is free and open source.
- **One-command reproducibility:** `docker compose up` brings up the entire stack.
- **Local-first:** everything runs on a laptop; free-tier hosting is optional, later.

## 3. Technology stack (all free, all shipped)

| Layer | Choice | Notes |
|---|---|---|
| Frontend | Next.js + React + TypeScript + Tailwind | `frontend/` |
| API | FastAPI + Uvicorn, versioned under `/api/v1`, OpenAPI docs | `backend/main.py` |
| Relational DB | PostgreSQL (SQLite fallback for single-node dev), SQLAlchemy + Alembic | `backend/db/` |
| Auth | FastAPI-Users: JWT + bcrypt, **GitHub OAuth**, RBAC, per-user API keys | `backend/auth/` |
| Vector DB | ChromaDB (self-hosted, Docker) | free equivalent of Qdrant/Pinecone; `backend/vector_db/` |
| Embeddings | `BAAI/bge-small-en-v1.5` via sentence-transformers | `backend/vector_db/embedder.py` |
| Knowledge graph | ArcadeDB Community (graph DB) + NetworkX analysis | `backend/graph_db/` |
| Parsing | tree-sitter (Python, JS/TS, Go, Rust, Java, …) | `backend/ast_parser/` |
| Repo access | GitPython (clone/pull, no GitHub API needed) | ingestion pipeline |
| Search | Two-level hybrid: graph-structural (LLM→Cypher on ArcadeDB) with fallback; semantic = vector + BM25 lexical, RRF-fused | `backend/retrieval/` |
| LLM | Ollama (local, e.g. `qwen2.5-coder:7b`); provider-flexible via `LLM_BASE_URL` | `backend/llm/` |
| Jobs | Celery + Redis (durable ingestion), WebSockets for live updates | `backend/celery_app.py` |
| Object storage | MinIO (S3-compatible, self-hosted) for uploaded archives | `backend/storage/` |
| Static analysis | Builtin SAST scanner + **Bandit + Ruff (S rules)** integration, risk detection, refactoring recommender; ESLint on the frontend (CI-enforced) | `backend/security_scan/`, `backend/risk_detection/`, `backend/refactoring/` |
| Observability | Structured logging, request IDs, Prometheus metrics, health checks | `backend/observability.py` |
| Rate limiting | slowapi on ingest/query routes | `backend/api/ratelimit.py` |
| CI/CD | GitHub Actions | `.github/workflows/ci.yml` |
| Deployment | Docker + Docker Compose (Postgres, Redis, ArcadeDB, Chroma, MinIO, API, worker, frontend) | `docker-compose.yml` |

Deliberate substitutions from the "ideal" list (equally free, already integrated —
do not churn): **Chroma instead of Qdrant**, **ArcadeDB instead of Neo4j CE**.

## 4. Architecture

```text
                         Next.js Frontend (:3100)
                                  │
                         FastAPI Gateway (:8001)
              JWT / OAuth / API keys / RBAC / rate limits
                                  │
        ┌──────────────┬──────────┴─────────┬──────────────────┐
   Ingestion       Retrieval & Q&A     Analysis            Collaboration
 (upload/clone)   (hybrid search+LLM) (risks/SAST/impact/  (comments, activity,
        │                 │            hotspots/refactor)   notifications+WS)
   tree-sitter      Chroma + BGE            │                    │
   GitPython        BM25 + Ollama      static analyzers     Celery + Redis
        └──────────────┴──────────┬─────────┴──────────────────┘
                                  │
             PostgreSQL · Redis · ArcadeDB · ChromaDB · MinIO
                                  │
                          Docker Compose (one command)
```

AI pipeline: repo → clone → tree-sitter AST → dependency/knowledge graph →
metadata extraction → chunking → BGE embeddings → Chroma → hybrid search
(structural graph queries + vector similarity) → local LLM → grounded answer.

## 5. Feature matrix (v1.0)

| Feature | Status | Where |
|---|---|---|
| GitHub OAuth login | ✅ | `backend/auth/oauth_github.py`, login page |
| JWT auth + registration | ✅ | `backend/auth/users.py` |
| RBAC + per-user API keys | ✅ | `backend/auth/rbac.py`, `apikeys.py` |
| Audit log | ✅ | `backend/api/audit.py` |
| Repo ingestion (upload / git clone) | ✅ | `routes_ingest.py`, `routes_upload.py` |
| Background jobs (Celery) + job tracking | ✅ | `backend/celery_app.py`, `api/jobs.py` |
| WebSockets live updates / notifications | ✅ | `routes_notifications.py`, `main.py` |
| Knowledge graph + visualization | ✅ | `graph_db/`, `frontend/app/graph` |
| Hybrid search (structural + vector + BM25) | ✅ | `backend/retrieval/`, `lexical.py` |
| Repository chat / Q&A with history | ✅ | `routes_query.py`, `routes_conversations.py` |
| AI summarize + code review | ✅ | `routes_summarize.py`, `routes_review.py` |
| Risk detection + hotspot heatmap | ✅ | `risk_detection/`, `routes_hotspots.py` |
| Security / SAST dashboard (builtin + Bandit + Ruff) | ✅ | `security_scan/`, `frontend/app/security` |
| Refactoring recommendations | ✅ | `refactoring/`, `frontend/app/refactor` |
| Change impact / blast radius | ✅ | `impact/`, `frontend/app/impact` |
| Exports (CSV/XLSX) + HTML/PDF reports | ✅ | `routes_export.py`, `api/report.py` |
| Rate limiting, request IDs, metrics, health checks | ✅ | `ratelimit.py`, `observability.py`, `routes_health.py` |
| Auto-documentation wiki (API + viewer page) | ✅ | `backend/docgen/`, `frontend/app/wiki` |
| Docs: architecture, ADRs, API guide, deployment | ✅ | `docs/` |
| Automated tests (230+) + CI | ✅ | `backend/tests/`, `.github/workflows/ci.yml` |
| One-command Docker deployment | ✅ | `docker-compose.yml` |

## 6. Remaining roadmap

Ordered; each item ships as its own version bump.

1. ~~**v1.1 — Documentation layer.**~~ ✅ Shipped: `docs/architecture.md` (with
   diagram), five ADRs in `docs/adr/`, `docs/api-guide.md`, `docs/index.md`.
   Still open: screenshots + demo GIF.
2. ~~**v1.2 — Free-tier deployment guide.**~~ ✅ Shipped:
   `docs/deployment-free-tier.md` (Vercel/Render/Fly/Neon free tiers; honest
   "no free GPU hosting" caveat for Ollama).
3. ~~**v1.3 — Auto-documentation generator.**~~ ✅ Shipped: `backend/docgen/`
   renders deterministic per-module markdown from the knowledge graph with an
   optional bounded LLM "Purpose" pass; `/api/v1/docgen/{modules,generate,wiki}`,
   plus the `/wiki` frontend page (module sidebar, markdown viewer, LLM purpose
   button, wiki.md download).
4. **v1.4 — Polish.** Seed/demo repo on first boot, public project board,
   tagged releases with changelogs, screenshots/demo GIF in docs.

**Not building** (per the philosophy: integrate, don't reinvent): custom auth,
own vector DB / LLM / parser / ORM, landing-page animations, theme switching as
a milestone, Qdrant/Neo4j migrations for their own sake.

## 7. Working agreements

- Every design decision gets a line in `docs/` (ADR style) when v1.1 lands.
- `backend && python -m pytest tests -q` must pass before merge; CI enforces it.
- New services must join `docker-compose.yml` with a healthcheck.
- After code changes, run `graphify update .` to keep the knowledge graph current.

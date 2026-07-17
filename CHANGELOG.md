# Changelog

All notable changes to the Codebase Intelligence Platform.
Format follows [Keep a Changelog](https://keepachangelog.com/); versions map to
the roadmap in [PROJECT_PLAN.md](PROJECT_PLAN.md) §6 and exist as annotated git
tags.

## [v1.4.0] — 2026-07-17

The polish release: a fresh deployment now demos itself, and the release
process is formalized.

### Added
- **First-boot demo repo**: with `SEED_DEMO_REPO=true` (docker-compose default)
  a fresh deployment auto-ingests the bundled PyShelf demo project
  (`backend/demo_repo/`) so the dashboard, graph, risks, impact, security,
  refactor, and Ask pages have real data before the first user ingest. PyShelf
  carries deliberate smells (god class, long method, dead code, shotgun
  surgery) so the analysis pages have findings to show. Skipped quietly when
  jobs already exist or ArcadeDB is down; disable with `SEED_DEMO_REPO=false`.
- **This changelog** and annotated release tags `v1.0.0`–`v1.4.0`.
- Screenshots of the main workspace pages in `docs/screenshots/`, embedded in
  the README and `docs/index.md`.
- GitHub issue templates (`.github/ISSUE_TEMPLATE/`) and a contributing guide
  so the public repo is ready for a project board.
- Live ingest progress everywhere: `GET /api/v1/ingest` lists recent jobs so a
  global progress bar can find in-flight work from any page; embedding progress
  is reported in whole-percent steps.
- Incremental re-embedding: unchanged chunks (by content SHA-1) are skipped on
  re-ingest, cutting warm re-ingests to well under a minute.

### Fixed
- **Orphaned ingest jobs**: a crashed run could leave a job in "running"
  forever, and the global progress banner would show a weeks-old
  "embedding 6%" indefinitely. Jobs with no progress for 30+ minutes are now
  swept to `failed` on API startup and flagged `stale` in `GET /api/v1/ingest`;
  the banner ignores stale rows.
- Repo-relative path resolution in the summarize and impact-export routes.
- Wiki module titles now show repo-relative paths (e.g. `graphify/build.py`)
  instead of raw machine paths; module identifiers are unchanged.
- Two corrupt `main (1)` ref files (Windows copy artifacts) removed from
  `.git/refs`; `git fsck` is clean again.

### Changed
- One-click Docker deploy (`run_ui.bat`) and local-dev launcher
  (`run_local.bat`) hardened; env config consolidated in `.env.example`.

## [v1.3.0] — 2026-07-02

Auto-documentation, security scanning, and smarter retrieval.

### Added
- **Auto-documentation generator** (`backend/docgen/`): deterministic
  per-module markdown rendered from the knowledge graph with an optional
  bounded LLM "Purpose" pass; `/api/v1/docgen/{modules,generate,wiki}` plus the
  `/wiki` frontend page (module sidebar, markdown viewer, wiki.md download).
- **Security / SAST dashboard**: builtin scanner plus Bandit and Ruff (S rules)
  integration under `/api/v1/security`, with the `/security` page.
- **Refactoring recommender** under `/api/v1/refactor`, with the `/refactor` page.
- **GitHub OAuth sign-in** (free OAuth App; email/password keeps working
  without it).
- **BM25 lexical layer** fused with vector search via reciprocal-rank fusion
  (RRF) for hybrid semantic retrieval.

### Fixed
- Slow security/wiki/health pages; removed placeholder settings entries.

## [v1.2.0] — 2026-07-02

### Added
- **Free-tier deployment guide** (`docs/deployment-free-tier.md`):
  Vercel/Render/Fly/Neon options with an honest "no free GPU hosting" caveat
  for Ollama. *(Shipped in the same commit as v1.1.0.)*

## [v1.1.0] — 2026-07-02

The documentation layer.

### Added
- `docs/architecture.md` with system diagram, five ADRs in `docs/adr/`,
  `docs/api-guide.md`, and `docs/index.md`.

### Changed
- All earlier plan documents consolidated into `PROJECT_PLAN.md` (single
  source of truth).

## [v1.0.0] — 2026-06-29

The core platform: nine phases, one `docker compose up`.

### Added
- **AST parsing** (tree-sitter): Python, JS/TS, Go, Rust, Java, and more.
- **Knowledge graph** (ArcadeDB): File/Function/Class/Module vertices,
  CONTAINS/CALLS/IMPORTS/INHERITS_FROM edges, incremental re-indexing.
- **Vector search** (ChromaDB + BGE embeddings), AST-aware chunking.
- **Risk detection**: god objects, dead code, complexity, long methods,
  shotgun surgery, deep inheritance.
- **Change impact / blast radius** with force-graph visualization.
- **Hybrid retrieval + LLM Q&A** (structural LLM→Cypher with semantic
  fallback), repository chat with history, AI summarize and code review.
- **FastAPI backend** (`/api/v1`, OpenAPI docs) with JWT auth + registration,
  RBAC, per-user API keys, audit log, rate limiting, request IDs, Prometheus
  metrics, health checks.
- **Next.js frontend**: ingest, dashboard, query, risks, impact, hotspots,
  exports (CSV/XLSX), HTML/PDF reports, notifications over WebSockets.
- **Jobs**: Celery + Redis durable ingestion with DB-backed job tracking.
- **Object storage** (MinIO) for uploaded archives.
- **Docker Compose** one-command stack and GitHub Actions CI.

# API Guide

Practical walkthrough of the HTTP API. The backend serves on port 8001 in the compose
stack (`docker-compose.yml` maps 8001 → 8000). Interactive OpenAPI docs (Swagger UI)
are at **`/docs`** — every route below is try-able there.

All routes are wired in `backend/main.py`; handlers live in `backend/api/routes_*.py`
and `backend/auth/`.

## Authentication

Three ways to authenticate (resolved in this priority order by
`backend/api/security.py`):

1. **JWT bearer** — `Authorization: Bearer <token>` from `/auth/jwt/login` or the
   GitHub OAuth flow.
2. **Static service key** — `X-API-Key: <API_KEY>` (the `API_KEY` env var;
   service-to-service).
3. **Per-user API key** — `X-API-Key: <key>` created via `/api/v1/keys`.

If the `API_KEY` env var is unset, data routes are **unauthenticated** (dev mode; the
backend logs a startup warning).

### Auth routes

| Method | Path | Purpose |
|---|---|---|
| POST | `/auth/register` | Create an account (JSON `{"email", "password"}`). |
| POST | `/auth/jwt/login` | Log in (form-encoded `username` + `password`); returns `{"access_token"}`. |
| GET | `/auth/providers` | Which OAuth providers are configured (`{"github": true/false}`). |
| GET | `/auth/github/login` | Redirect to GitHub's authorize page (signed state token). |
| GET | `/auth/github/callback` | Code exchange → find-or-create user → redirect to `FRONTEND_URL/login#token=<JWT>` (token in the URL fragment, never in query strings/logs). |
| * | `/users/*` | FastAPI-Users user management (me, by id). |

GitHub OAuth is enabled only when `GITHUB_CLIENT_ID`/`GITHUB_CLIENT_SECRET` are set
(`backend/auth/oauth_github.py`); otherwise `/auth/github/*` returns 503.

## Data routes (`/api/v1`)

All routes below require a principal when `API_KEY` is set. Ingest and query are
rate-limited (defaults: 10/minute and 60/minute; `backend/api/ratelimit.py`).

### Ingestion & upload

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/v1/ingest` | Start ingestion of `{"repo_url"}` (git clone, SSRF-guarded) or `{"repo_path"}`; returns `{"job_id", "status": "queued"}`. Runs on Celery. |
| GET | `/api/v1/ingest/{job_id}` | Poll job status/progress. |
| POST | `/api/v1/ingest/upload` | Upload a repo archive (multipart); stored in MinIO, then ingested. |

### Query & conversations

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/v1/query` | Ask a question: `?q=...&top_k=10&session_id=...`. Returns answer, strategy (structural/semantic), sources, and any generated Cypher. |
| POST | `/api/v1/conversations` | Create a conversation session (multi-turn memory). |
| GET | `/api/v1/conversations` | List your conversations. |
| GET | `/api/v1/conversations/{session_id}/messages` | Message history of a session. |

### Analysis

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/v1/risks` | Risk-detection findings from the knowledge graph. |
| GET | `/api/v1/security` | SAST/security-scan findings (`backend/security_scan/`). |
| GET | `/api/v1/refactor` | Refactoring recommendations (`backend/refactoring/`). |
| GET | `/api/v1/impact/{file_path}` | Change impact / blast radius for a file. |
| GET | `/api/v1/hotspots` | Hotspot heatmap data (complexity × churn). |
| GET | `/api/v1/stats` | Repository/graph statistics. |

### AI assistance

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/v1/summarize` | LLM summary of a file/module. |
| POST | `/api/v1/review` | LLM code review of supplied code. |

### Auto-documentation (wiki)

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/v1/docgen/modules` | Documentable modules (source files the graph knows). |
| POST | `/api/v1/docgen/generate` | Markdown pages for selected/all modules; `{"narrative": true}` adds an LLM-written Purpose per module (best-effort). |
| GET | `/api/v1/docgen/wiki` | All pages concatenated behind an index (the `/wiki` frontend page's download source). |

### Exports & reports

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/v1/export/risks` | Download risks as `?format=csv` or `xlsx` (optional `severity` filter). |
| GET | `/api/v1/export/impact/{file_path}` | Download impact analysis as CSV/XLSX. |
| GET | `/api/v1/report/risks` | Rendered risk report, `?format=html` or `pdf`. |
| GET | `/api/v1/report/narrative` | AI-narrated report (LLM executive summary), HTML or PDF. |

### Repos, files & RBAC

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/v1/repos` | Register a repo; creator becomes `owner`. |
| GET | `/api/v1/repos` | List repos you belong to (with your role). |
| GET | `/api/v1/repos/{repo_id}/members` | List members and roles. |
| PUT | `/api/v1/repos/{repo_id}/members` | Grant/update a member's role (`viewer`/`member`/`owner`). |
| DELETE | `/api/v1/repos/{repo_id}/members/{member_id}` | Revoke membership. |
| GET | `/api/v1/repos/files` | File tree of the ingested repo. |
| GET | `/api/v1/repos/{job_id}/files` | File tree for a specific ingestion job. |

### Collaboration & notifications

| Method | Path | Purpose |
|---|---|---|
| GET / POST | `/api/v1/comments` | List / add comments (anchored to files/findings). |
| DELETE | `/api/v1/comments/{comment_id}` | Delete a comment. |
| GET | `/api/v1/activity` | Activity feed. |
| GET | `/api/v1/notifications` | List notifications. |
| POST | `/api/v1/notifications/{id}/read` | Mark one read. |
| POST | `/api/v1/notifications/read-all` | Mark all read. |
| WS | `/ws/notifications?token=<JWT>` | Live notification stream (JWT via query param). |

### Keys, LLM config, graphify, health

| Method | Path | Purpose |
|---|---|---|
| POST / GET | `/api/v1/keys` | Create / list per-user API keys (JWT required). |
| DELETE | `/api/v1/keys/{key_id}` | Revoke a key. |
| GET / PUT | `/api/v1/llm-config` | Inspect / switch LLM provider, base URL, model. |
| GET | `/api/v1/llm-config/models` | List models available on the LLM server. |
| POST | `/api/v1/llm-config/pull` | Pull a model on the Ollama server (202). |
| GET | `/api/v1/graphify/stats` \| `/graph` \| `/report` | Graphify knowledge-graph stats, graph JSON, and report. |
| GET | `/api/v1/health/services` | Per-service health (Postgres, Redis, ArcadeDB, Chroma, MinIO, LLM). Open, no auth. |
| GET | `/health` | Liveness probe. |
| GET | `/metrics` | Prometheus metrics. |

## curl examples

```bash
# 1. Register, then log in (form-encoded!) and capture the JWT
curl -s -X POST http://localhost:8001/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"email": "dev@example.com", "password": "s3cret-pass"}'

TOKEN=$(curl -s -X POST http://localhost:8001/auth/jwt/login \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'username=dev@example.com&password=s3cret-pass' | jq -r .access_token)

# 2. Start ingesting a repository (queued on the Celery worker), then poll it
JOB=$(curl -s -X POST http://localhost:8001/api/v1/ingest \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"repo_url": "https://github.com/pallets/flask"}' | jq -r .job_id)

curl -s http://localhost:8001/api/v1/ingest/$JOB -H "Authorization: Bearer $TOKEN"

# 3. Ask a question (hybrid graph + vector retrieval, answered by the local LLM)
curl -s -G http://localhost:8001/api/v1/query \
  -H "Authorization: Bearer $TOKEN" \
  --data-urlencode 'q=Which modules depend on the routing layer?' \
  --data-urlencode 'top_k=10'

# 4. Export the risk report as a PDF
curl -s -o risk_report.pdf \
  "http://localhost:8001/api/v1/report/risks?format=pdf" \
  -H "Authorization: Bearer $TOKEN"
```

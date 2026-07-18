# Deployment at ₹0

Honest guide to running the platform without spending anything. Local Docker Compose is
the default, recommended, and best-supported path; free-tier cloud hosting is an
optional overlay with real limitations, documented below.

## Option A (recommended): local, one command

```bash
git clone <this-repo> && cd codebase_intelligence_project
docker compose up
```

This starts Postgres, Redis, ArcadeDB, ChromaDB, MinIO, the FastAPI backend (:8001),
the Celery worker, and the Next.js frontend (:3100) — see `docker-compose.yml`. The
backend runs Alembic migrations on boot. `./run.sh --docker` (Windows:
`.\run.ps1 -Docker`) covers first-time setup: it creates `.env`, pulls the
Ollama model when available, and builds + starts the stack.

The LLM is **not** in the compose stack by default: install [Ollama](https://ollama.com)
on the host and pull a model:

```bash
ollama pull qwen2.5-coder:7b
```

Containers reach it at `http://host.docker.internal:11434/v1` (`LLM_BASE_URL`).
Alternatively, uncomment the `ollama` service in `docker-compose.yml` and point
`LLM_BASE_URL` at `http://ollama:11434/v1`. Any OpenAI-compatible local server
(LM Studio, llama.cpp, vLLM) also works — `backend/llm/` supports both client styles.

## Backend environment variables

Authoritative list from the `backend` service env block in `docker-compose.yml`:

| Variable | Purpose | Default / fallback |
|---|---|---|
| `DATABASE_URL` | Postgres DSN (`postgresql+psycopg2://...`) | unset → local SQLite file |
| `CELERY_BROKER_URL` | Redis broker for the worker | `redis://redis:6379/0` |
| `CELERY_TASK_ALWAYS_EAGER` | `true` = run jobs in-process (no worker needed) | `false` in compose |
| `AUTH_SECRET` | JWT signing secret — **set a strong random value** | insecure dev default (startup warning) |
| `API_KEY` | Static service key; when set, data routes require auth | unset → dev open mode |
| `GITHUB_CLIENT_ID` / `GITHUB_CLIENT_SECRET` | GitHub OAuth App (free) | blank → button hidden |
| `FRONTEND_URL` / `BACKEND_URL` | OAuth redirect targets | `http://localhost:3100` / `http://localhost:8001` |
| `MINIO_ENDPOINT` / `MINIO_ACCESS_KEY` / `MINIO_SECRET_KEY` | Object storage for uploads | endpoint unset → local filesystem |
| `ARCADEDB_URL` / `ARCADEDB_PASSWORD` | Knowledge graph | `http://arcadedb:2480` |
| `CHROMA_HOST` / `CHROMA_PORT` | Vector store | `chroma` / `8000` (host-mapped to 8003) |
| `LLM_BASE_URL` / `LLM_MODEL` | Local LLM endpoint and model | `http://host.docker.internal:11434/v1` / `qwen2.5-coder:7b` |

## Option B (optional): free-tier cloud hosting

You can host the web-facing pieces for free. Nothing here costs money, but every free
tier has strings attached — listed honestly.

### Frontend → Vercel (free Hobby tier)

Deploy `frontend/` as a Next.js app. `NEXT_PUBLIC_API_URL` is baked in at **build**
time (client code cannot read runtime env; see the comment in `docker-compose.yml`),
so set it in Vercel's project env to your public backend URL before building.

### Backend container → Render free or Fly.io

Build the `backend/` Dockerfile. Set the env vars above. Caveats:

- Render free instances **sleep after inactivity** (cold starts ~1 min); Fly's free
  allowance is small (shared-CPU VM).
- Set `AUTH_SECRET`, `API_KEY`, and `ARCADEDB_PASSWORD` to real secrets.
- The Celery worker is a second process; on a single free instance the pragmatic
  fallback is `CELERY_TASK_ALWAYS_EAGER=true` (ingestion runs in-request — fine for
  small repos, blocks the request for big ones).
- ArcadeDB, ChromaDB, and MinIO have no managed free tiers worth using; either run
  them as sidecar containers on the same host (Fly volumes) or accept that
  upload-to-MinIO falls back to the local filesystem (`MINIO_ENDPOINT` unset) and
  disk is **ephemeral** on free tiers — re-ingest after restarts.

### Postgres → Neon (free tier)

Create a free Neon project and set
`DATABASE_URL=postgresql+psycopg2://<user>:<pass>@<host>/<db>?sslmode=require`.
Free tier: ~0.5 GB storage, auto-suspends when idle (first query after idle is slow).
Alembic migrations run automatically on backend boot.

### Redis → Upstash (free tier) or self-hosted Valkey

Set `CELERY_BROKER_URL=rediss://...` from Upstash's free tier (10k commands/day cap),
or run Valkey/Redis yourself next to the backend container. If neither is practical,
`CELERY_TASK_ALWAYS_EAGER=true` removes the broker requirement entirely.

### LLM → no free option exists. Period.

There is **no free GPU hosting**. Do not look for one; you will find trials, not tiers.
The supported model is:

- Run Ollama on your own machine ("bring your own machine") and, if you want a cloud
  backend to use it, expose it to the backend via a tunnel you control — or simply run
  queries against a locally hosted stack.
- Without a reachable LLM, the platform degrades gracefully rather than breaking:
  ingestion, the knowledge graph, vector search, risks, security scan, refactoring,
  hotspots, impact, exports, and CSV/HTML reports all work. What fails (with a 503,
  per `backend/api/routes_query.py`) is answer generation, summarize, review, and the
  narrative report.

### Suggested ₹0 cloud topology

Vercel (frontend) → Render/Fly (backend, `CELERY_TASK_ALWAYS_EAGER=true`) →
Neon (Postgres) + Upstash (Redis, optional) → your laptop (Ollama, optional).
Everything else (ArcadeDB/Chroma/MinIO) rides along as containers or degrades to
filesystem fallbacks. For anything beyond a demo, run Option A locally.

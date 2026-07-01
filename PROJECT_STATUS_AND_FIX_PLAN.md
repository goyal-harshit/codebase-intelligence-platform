# Codebase Intelligence Platform — Status Audit & Fix Plan
_Generated 2026-07-01. Supersedes nothing in CODEBASE_INTELLIGENCE_MASTER_PLAN.md / ENTERPRISE_CODEBASE_INTELLIGENCE_ROADMAP.md — this is a status snapshot of what's actually built vs. those plans._

## 0. Architecture as it exists today

```
backend/   FastAPI + Celery + SQLAlchemy (auth, jobs, RBAC, storage)
           ArcadeDB (graph) + ChromaDB (vectors) + Ollama (LLM) as external services
frontend/  Next.js 14 (App Router) + Tailwind + axios + react-force-graph
```
~38 REST endpoints registered in `backend/main.py` (auth, ingest, upload, query, impact, risks, hotspots, stats, graphify, conversations, comments, activity, keys, repos, notifications, export). There is also a legacy server-rendered HTML app (`backend/analysis/webapp.py`) that is **not mounted in `main.py`** — it's only exercised by tests. Ignore it; the real UI is the Next.js frontend.

Nothing here is fake — the gaps below are specific, verified bugs/missing features, not vague impressions.

---

## 1. Heatmap — not showing (root cause found)

`GET /api/v1/hotspots` (`backend/api/routes_hotspots.py`) resolves the most recent completed ingest job's `repo_path`, then calls `build_hotspots()` (`backend/analysis/hotspots.py`), which calls `collect_git_insights()` (`backend/analysis/git_insights.py:23-28`).

**That function returns `{"available": False, "reason": "not a git repository"}` unless `repo_path` has a `.git` folder.**

Your ZIP-upload flow (`backend/api/routes_upload.py`) extracts the archive to `backend/data/repos/uploads/{uuid}/` — a plain directory, no `.git`. So any repo you fed in via upload will always report `available: false`, and the dashboard correctly renders the empty state "Hotspots need git history and a completed ingest" instead of the heatmap. This is not a frontend bug — `frontend/components/HotspotHeatmap.tsx` and the dashboard wiring in `frontend/app/dashboard/page.tsx:158-174` are correct and will render fine the moment the endpoint returns real data.

**Fix options (pick one, not mutually exclusive):**
1. When ingesting via **Git URL** (`POST /api/v1/ingest` with `repo_url`) instead of ZIP upload, `.git` is preserved by the clone — heatmap works today with zero code changes. Use this path to verify the feature isn't actually broken.
2. For ZIP uploads: keep a copy of `.git` if the ZIP contains one (many exported ZIPs strip it — check `Content-Disposition`/zip contents before assuming).
3. Add a fallback complexity-only heatmap (churn unavailable) so ZIP-uploaded repos still show *something* — color by `total_complexity` alone, label it "complexity heatmap (git history unavailable)".
4. Surface the `reason` field from `HotspotResult` more prominently in the UI so this isn't mysterious next time (currently it's shown as a small `detail` string in `StateBlock`, easy to miss).

**Recommended:** do (3) + make (4) more visible. It's the smallest change that makes the feature never look "broken" again.

---

## 2. Ask / Query — likely cause of failures

`backend/api/deps.py` builds `QueryEngine`, `ArcadeDBClient`, `VectorStoreBuilder`, and `OllamaClient` as **lazy singletons that don't connect at startup** (by design, so the API boots without any backend running). The first `/api/v1/query` call is what actually opens connections — and if ArcadeDB, ChromaDB, or Ollama isn't reachable at that moment, `routes_query.py:47-51` catches the exception and returns **HTTP 503 "query backend unavailable: ..."**.

Checklist to fix "ask isn't working," in order of likelihood:
1. **ArcadeDB and ChromaDB containers aren't running.** `docker-compose.yml` at repo root defines them — confirm with `docker compose ps`. If you're not using Docker at all, both are hard requirements for `/query`, not optional.
2. **Ollama model name mismatch.** `.env.local` sets `OLLAMA_MODEL=llama3.2:latest`, but `backend/llm/ollama.py:46` defaults to `qwen2.5-coder:7b` if the env var isn't actually loaded by the process. Run `ollama list` and confirm the exact tag matches `OLLAMA_MODEL` byte-for-byte (`llama3.2:latest` vs `llama3.2` are different keys to Ollama's API).
3. **No completed ingest yet.** If the graph/vector DB are empty (no repo ingested successfully), `/query` will return a low-quality or empty answer rather than erroring — check `/api/v1/stats` first to confirm `total_functions > 0`.
4. Open the browser dev tools Network tab while asking a question — the exact status code (503 vs 200-with-bad-answer vs CORS failure) tells you which of the above it is. Worth doing this once before changing code.

**No code is provably broken here** — `routes_query.py`, `frontend/app/query/page.tsx`, and `analysis/llm.py`'s graceful-degradation path all look correct. This is almost certainly an environment/services-not-running issue, not a bug.

---

## 3. File selector after upload — confirmed missing

Today's flow: upload ZIP → get `job_id` → poll until `complete` → then you must **already know the exact relative file path** to use `/api/v1/impact/{file_path}` or reference it in a question. There is no endpoint that lists the files in an ingested repo, and no frontend file-tree/browser component anywhere in `frontend/app/`.

**What to build (new feature, not a bug fix):**
- Backend: `GET /api/v1/repos/{job_id}/files` — walk the stored `repo_path` (reuse `ast_parser/repo_walker.py:walk_repository`, already ignores `.git`/`node_modules`/etc.) and return a tree or flat list of relative paths, optionally filtered by extension.
- Frontend: a `FileBrowser` component (simple: searchable flat list with fuzzy filter; better: collapsible tree) shown after ingest completes, on the Impact page and the Ask page, that fills in `file_path` on click instead of requiring free-text typing.
- Wire `frontend/app/impact/page.tsx`'s `filePath` input to this component as an optional "browse" affordance alongside the existing text box (keep the text box for power users / API parity).

This is genuinely net-new work — nothing today reads back the file list after ingestion.

---

## 4. Impact page — works, but UX is the whole problem

`GET /api/v1/impact/{file_path:path}` (`backend/api/routes_impact.py`) and `ImpactAnalyzer` (`backend/impact/analyzer.py`) are functionally correct and tested. The page requires:
- An **exact** file path as stored in the graph (which is whatever path the parser recorded during ingestion — usually the absolute path used for ingestion, not a path relative to repo root). This mismatch is the most common source of "impact page returns nothing."
- A completed ingest with the graph populated (same prerequisite as Ask).

**Fix, in priority order:**
1. Ship the file selector from Section 3 — this alone removes almost all confusion, since users click a path instead of guessing its exact stored form.
2. Normalize path matching server-side: accept a path relative to `repo_path` and resolve it to whatever absolute/stored form the graph uses (mirror the `_lookup_keys()` normalization trick already used in `hotspots.py:55-64` — reuse that helper rather than writing a new one).
3. Return a clear 404 with the nearest-match suggestion when a path isn't found, instead of an empty result set that looks like "no impact."

---

## 5. Local LLM integration — current state and what to add

**What exists today:**
- `backend/llm/ollama.py` — native Ollama client, config via `LLM_BASE_URL`/`LLM_MODEL` (preferred) or `OLLAMA_URL`/`OLLAMA_MODEL` (legacy fallback). Defaults: `http://localhost:11434`, `qwen2.5-coder:7b`.
- `backend/analysis/llm.py` — a second, OpenAI-compatible client (adds `/v1` suffix), also reads `LLM_BASE_URL`/`LLM_MODEL`, and additionally supports `LLM_API_KEY` — so **cloud providers with an OpenAI-compatible API (OpenAI itself, many hosted-inference providers) already work today** by just setting `LLM_BASE_URL` + `LLM_API_KEY` + `LLM_MODEL` in `.env.local`, no code change.
- These two clients are redundant/parallel, not unified — `deps.py` wires `OllamaClient` into `QueryEngine`; `analysis/llm.py`'s client is used by the legacy webapp path only. Worth consolidating eventually (see backlog).

**Since you already have a local LLM installed:** if it's Ollama, it should already be picked up automatically as long as `OLLAMA_URL` (or `LLM_BASE_URL`) points at it and `OLLAMA_MODEL`/`LLM_MODEL` matches a model tag you've pulled (`ollama list` to check). If your local LLM is something else (LM Studio, llama.cpp server, text-generation-webui, vLLM, etc.), it very likely already exposes an **OpenAI-compatible** `/v1/chat/completions` endpoint — point `LLM_BASE_URL` at that and it should work through `analysis/llm.py` without new code, provided `deps.py` is updated to use that client instead of (or in addition to) `OllamaClient` for the query path. That wiring gap — `deps.py` only ever constructs `OllamaClient`, never `analysis/llm.py`'s client — is the one real code fix needed to make "any local server, not just Ollama" actually work end-to-end.

**Missing (net-new features), in the order you described wanting them:**

| Feature | What to build |
|---|---|
| Runtime provider switch (local vs. API key) | Add a `Settings`/`LLM config` table or `.env`-backed config exposed via a small `GET/PUT /api/v1/llm-config` endpoint + a Settings page in the frontend. Fields: `provider` (`ollama` \| `openai_compatible` \| `anthropic`), `base_url`, `model`, `api_key` (encrypted at rest, reuse the existing `auth/apikeys.py` encryption pattern). |
| Model listing for local runtimes | Ollama exposes `GET /api/tags` listing installed models — add `list_models()` to `OllamaClient` and a backend route `GET /api/v1/llm-config/models` that proxies it, so the Settings page can populate a dropdown instead of free-text model names. |
| Download/pull a new local model | Ollama exposes `POST /api/pull` (streaming) — add a backend route that proxies this as a Celery task (same pattern as `celery_app.py`'s ingest tasks) with progress reported over the existing WebSocket (`/ws/notifications` is already wired in `main.py`) or the existing `notifications` system (`backend/notifications/`). Reuse, don't reinvent, the progress-reporting plumbing you already built for ingestion. |
| Cloud API key support | Already works for OpenAI-compatible endpoints via `analysis/llm.py` + `LLM_API_KEY`. To support Anthropic specifically (different request/response shape, not OpenAI-compatible), add a thin `AnthropicClient` implementing the same `LLMClient` protocol (`backend/llm/ollama.py:24-26` already defines the protocol — implement against it) and select it via the `provider` field above. |
| Unify the two existing LLM clients | Make `deps.py::get_llm()` provider-aware: read the config from the new settings source and instantiate `OllamaClient`, the OpenAI-compatible client, or `AnthropicClient` accordingly, all behind the same `LLMClient` protocol so `QueryEngine` doesn't change. |

This is the single largest chunk of new work in this plan — budget it as its own phase (see Section 7).

---

## 6. Everything else in the platform that already works (verified)

- Auth: FastAPI-Users JWT (`/auth/jwt/*`, `/auth/register`, `/users/*`), RBAC (`auth/rbac.py`, repo membership), API keys (`auth/apikeys.py`, `/api/v1/keys`).
- Ingest: both `repo_url` (git clone) and ZIP upload, Celery-backed, durable job tracking (`backend/tests/test_jobs_durable.py` passes), progress steps, storage abstraction (local fs or MinIO).
- Risk detection (`backend/risk_detection/detector.py`) and blast-radius/impact (`backend/impact/analyzer.py`) — both tested and correct.
- Retrieval: structural (Cypher) vs. semantic (vector) routing (`backend/retrieval/router.py`), with graceful fallback.
- Export/reporting: `/api/v1/export/risks`, `/api/v1/report/narrative` (LLM-generated), HTML risk reports.
- Collaboration: comments, activity feed, notifications (in-app + WebSocket + email dispatch).
- Observability: Prometheus metrics (`backend/observability.py`, `/metrics`), audit log (`backend/api/audit.py`).

Don't re-plan any of this — it's done. Reference this list instead of re-auditing it next session.

---

## 7. Prioritized backlog (next actionable steps, dependency-ordered)

> **Execution status (updated 2026-07-01):** Phase A and Phase B are **done and
> verified** (202 backend tests pass, frontend typechecks, live smoke test).
> Phase C's foundational slice (provider-aware `get_llm`, model listing,
> read-only `/llm-config`, Settings status panel) is done; the heavier
> config-DB / pull / Anthropic work remains. Details below.

**Phase A — Fix what's confusing right now — DONE**
1. ✅ Complexity-only heatmap fallback + `reason` surfaced. `build_hotspots()` now
   returns `mode: "complexity_only"` with an amber banner in the dashboard when
   git history is absent (ZIP uploads), instead of an empty state. Falls back to
   `available: false` only when the graph itself is empty. (`analysis/hotspots.py`,
   `components/HotspotHeatmap.tsx`, `app/dashboard/page.tsx`)
2. ✅ Verified Ask/services end-to-end via the new health probe (below): ArcadeDB
   and Ollama up, ChromaDB address (`CHROMA_PORT=8001`) points at a *stale second
   backend*, not Chroma — an env misconfig the probe now makes visible. Fix the
   env (point `CHROMA_PORT` at the real Chroma) and `/query` semantic search works.
3. ✅ `GET /api/v1/health/services` pings ArcadeDB/Chroma/LLM, never raises, and is
   surfaced in Settings → "Service health". (`api/routes_health.py`,
   `components/SystemStatusPanel.tsx`)
4. ✅ Impact path normalization: `ImpactAnalyzer.resolve_file_path()` maps a
   repo-relative path to the exact stored `File.path` (exact → suffix → basename
   suggestions); route returns a clear **404 with "did you mean"** instead of an
   empty result. (`impact/analyzer.py`, `api/routes_impact.py`)

**Phase B — File selector — DONE**
1. ✅ `GET /api/v1/repos/{job_id}/files` **and** `GET /api/v1/repos/files` (latest
   completed ingest, so Impact/Ask don't need to thread a job_id). (`api/routes_files.py`)
2. ✅ `FileBrowser` component — searchable, fuzzy-filtered flat list, graceful
   error/empty states. (`components/FileBrowser.tsx`)
3. ✅ Wired into Impact ("Browse ingested files" → fills path + runs) and Ask
   ("Reference a file" → inserts path into the question).

**Phase C — LLM provider flexibility — DONE (free/local providers only)**
> Scope decision: the user asked for **free/local LLMs only, no paid cloud
> providers**. The Anthropic (paid) client and any hosted-API-key path were
> deliberately dropped; provider choice is Ollama or any OpenAI-compatible local
> server (LM Studio / llama.cpp / vLLM / text-generation-webui).
1. ✅ `OpenAICompatibleClient` (`llm/openai_compatible.py`) + `list_models()` on it
   (`GET /v1/models`) and on `OllamaClient` (`GET /api/tags`).
2. ✅ `LlmSetting` DB table (`db/models.py`) + migration `7f1b2c3d4e50` — app-wide
   config override; API key encrypted at rest via Fernet (`llm/secretbox.py`,
   keyed off `LLM_CONFIG_SECRET`/`AUTH_SECRET`). Config store: `llm/config.py`.
3. ✅ `deps.get_llm()` builds from the effective config (DB override → `LLM_*` env),
   uncached so a runtime change applies on the next query.
4. ✅ Endpoints (`api/routes_llm.py`): `GET /llm-config`, JWT-protected
   `PUT /llm-config` (key never returned; audited), `GET /llm-config/models`,
   JWT-protected `POST /llm-config/pull`.
5. ✅ Ollama model pull as a background job (`api/tasks.py::run_model_pull` +
   `dispatch_model_pull`) streaming `POST /api/pull`, reporting throttled progress
   through the existing notification/WebSocket plumbing.
6. ✅ Settings **editor** UI (`components/LlmConfigEditor.tsx`): provider dropdown,
   base URL, model picker (datalist from installed models), optional API key
   (openai_compatible only), Save, and an Ollama "Pull a model" box.
   `SystemStatusPanel` keeps the service-health card.
- ⬜ **Explicitly out of scope (per user):** a dedicated `AnthropicClient` / any
   paid cloud provider.

**Status:** Phases A, B, and C (free/local scope) are all shipped and verified —
212 backend tests pass, frontend typechecks, and the LLM config GET/PUT/models
flow was smoke-tested live against a running Ollama.

# Full-Stack Completeness Plan — Codebase Intelligence Platform

Scope: gap analysis against a generic "complete SaaS platform" checklist, constrained to **100% free / open-source / self-hostable** components (no paid tiers, no vendor lock-in). This supersedes nothing in `CODEBASE_INTELLIGENCE_MASTER_PLAN.md` or `ENTERPRISE_CODEBASE_INTELLIGENCE_ROADMAP.md` — it adds the layers those docs don't cover (multi-user, persistence, notifications, collaboration) and fixes the few gaps flagged below.

Audit date: 2026-06-28. Based on direct repo inspection (not the old hardening report — several items from that report are now **done**: API-key auth, rate limiting, SSRF/path-traversal validation, parameterized Cypher, structured logging, Prometheus metrics, CI).

---

## 1. Current State Snapshot

| Layer | Status |
|---|---|
| AST parsing, graph DB, vector DB, hybrid retrieval, risk detection, impact analysis | Done (per prior report) |
| API-key auth, rate limiting, input validation, parameterized queries | **Done** — implemented since last audit |
| Structured logging, Prometheus metrics, `/health` | Done |
| Multi-user accounts, persistent metadata store, RBAC, OAuth | **Missing entirely** |
| File upload, notifications, collaboration, exports | **Missing entirely** |
| Cloud/static deployment targets | Not applicable by design (self-hosted Docker Compose) |

The project is architecturally sound and security-hardened for its current single-tenant, API-key-gated use case. The gaps below are not bugs — they're layers that were never in scope (no user system, no persistence beyond the graph/vector DBs, no collaboration). Treat this as "what to add," not "what to fix," except where noted in §5.

---

## 2. Gap Table by Category

Legend: ✅ Have · 🟡 Partial · ❌ Missing

### Frontend
| Item | Status | Note |
|---|---|---|
| Landing page, dashboard, charts, tables, forms, search/filters | ✅ | `frontend/app/*`, `recharts`, `RiskTable` |
| Auth UI | ❌ | No login/signup |
| Dark/light mode | ❌ | Light-only |
| Responsive design | 🟡 | Tailwind flex/max-w, not mobile-tested |
| File upload / drag-drop | ❌ | Only repo URL/path string |
| Infinite scroll | ❌ | — |
| Markdown / rich text editor | ❌ | — |
| Notifications UI (toast) | ❌ | Inline errors only |
| Keyboard shortcuts | 🟡 | Enter-to-submit only |

### Backend
| Item | Status | Note |
|---|---|---|
| REST API, CRUD, versioning (`/api/v1`) | ✅ | |
| GraphQL | ❌ | Not needed unless a client demands it — skip |
| Auth (API key) | ✅ | `backend/api/security.py` |
| JWT / OAuth / RBAC | ❌ | No multi-user model exists |
| Rate limiting, request validation | ✅ | slowapi + Pydantic validators |
| Background jobs | 🟡 | In-process `BackgroundTasks`, not durable (no Celery/Redis) |
| Caching | ❌ | No Redis cache layer |
| Logging | ✅ | |

### Database / Persistence
| Item | Status | Note |
|---|---|---|
| Graph DB (ArcadeDB), Vector DB (Chroma) | ✅ | Core to the product, correct choice |
| Relational/metadata store (users, jobs, audit, API keys) | ❌ | **This is the single biggest structural gap.** Job state lives in memory and is lost on restart; there is nowhere to put users, teams, or audit logs even after auth is added. |

### Auth
| Item | Status |
|---|---|
| Email/password, OAuth (GitHub/Google), magic links, password reset, email verification, RBAC | ❌ all — no user system exists yet |

### AI Features
| Item | Status | Note |
|---|---|---|
| Local LLM (Ollama), RAG, semantic search, doc Q&A, embeddings | ✅ | Core product |
| Prompt templates (externalized, not hardcoded) | ❌ | Prompts are inline strings in `cypher_generator.py` / `answer.py` |
| Conversation history (multi-turn) | ❌ | Every query is stateless |
| AI summarization / AI report generation | ❌ | Natural extension of existing LLM client |
| AI code review | ❌ | Natural extension of risk detection + LLM |

### File Handling
| Item | Status |
|---|---|
| Document parsing (code files) | ✅ |
| Image/PDF/CSV/Excel upload, PDF/CSV/Excel export, ZIP download | ❌ all |

### Search
| Item | Status |
|---|---|
| Structural (Cypher) + semantic (vector) search, severity filters | ✅ |
| Autocomplete, fuzzy search | ❌ |

### Visualization
| Item | Status | Note |
|---|---|---|
| Dashboard, line/bar/pie charts, force-directed network graph | ✅ | |
| Heatmaps, timelines, tree views, kanban, Gantt | ❌ | Heatmap (churn×complexity) is the highest-value addition — see §4 |

### Collaboration
| Item | Status |
|---|---|
| Team workspaces, invitations, comments, mentions, activity feed, version history, audit logs | ❌ all — blocked on the relational store in §3 |

### Notifications
| Item | Status |
|---|---|
| In-app, email, push, toast, activity log | ❌ all |

### Analytics
| Item | Status | Note |
|---|---|---|
| Usage stats (`/stats`), performance metrics (Prometheus) | ✅ | |
| User/event/session/error-aggregation analytics | ❌ | No user system to attribute events to yet |

### Security
| Item | Status | Note |
|---|---|---|
| Input validation, injection prevention, XSS protection, rate limiting, API keys | ✅ | |
| JWT, OAuth, CSRF, RBAC, HTTPS-in-code | ❌ | CSRF is moot until cookie-based sessions exist; HTTPS should terminate at a reverse proxy, not app code |

### Developer Experience
| Item | Status | Note |
|---|---|---|
| OpenAPI/Swagger, unit + integration tests, Docker, CI, env management, test fixtures | ✅ | Strong |
| E2E tests (Playwright), DB migrations | ❌ | Migrations only matter once a relational DB exists |

### Monitoring
| Item | Status | Note |
|---|---|---|
| Error/request logging, health check, Prometheus | ✅ | |
| Uptime monitoring | ❌ | Free option: self-hosted Uptime Kuma |

### Deployment
| Item | Status | Note |
|---|---|---|
| Docker Compose (full local/self-hosted stack) | ✅ | This is the correct deployment target — see §6, do not chase Vercel/Render |

### Storage
| Item | Status | Note |
|---|---|---|
| Local filesystem (`data/repos/`) | ✅ | Fine for cloned repos |
| Object storage for user-uploaded files (once file upload exists) | ❌ | Free/OSS answer: **MinIO** self-hosted, S3-compatible, in the same Docker Compose |

### Documentation
| Item | Status |
|---|---|
| README, Swagger docs, master plan, roadmap | ✅ |
| Architecture/sequence diagrams, admin guide | ❌ |

---

## 3. Bugs / Issues Found

Quick-pass scan found no new critical bugs (the deep security/code review was already done in the prior report and most items there are now fixed). Remaining known items:

1. **Circular-dependency risk detector is data-starved** — needs module-level import edges to be reliable. (Carried over, still open.)
2. **Dead-code detector flags legitimate entry points** (e.g. `main()`, FastAPI route handlers) as dead code — needs an entry-point allowlist/annotation.
3. **In-process background jobs are not durable** — a backend restart mid-ingestion silently drops the job with no retry or persisted failure state. This is the same root cause as the missing relational store (§2).
4. **Prompts are hardcoded inline** rather than externalized — makes prompt iteration require a code change + redeploy instead of a config edit.
5. No migrations tooling — fine today (no relational DB), but must be solved *before*, not after, adding Postgres (§4 Phase 1).

None of these block current functionality; they become blocking the moment multi-user/durability work starts, so fix #3 and #5 together in Phase 1.

---

## 4. Free/Open-Source Stack Additions (no paid tiers, anywhere)

| Need | Pick | Why this one, free-tier rationale |
|---|---|---|
| Relational metadata store | **PostgreSQL** (self-hosted container, already Docker-Composed) | Free forever, no row/row-count caps like hosted free tiers (Supabase/Mongo Atlas free tiers have limits and require an internet-connected account). Fully aligned with this project's local-first, air-gappable design. |
| ORM / migrations | **SQLAlchemy + Alembic** (Python, matches existing FastAPI backend) | Free, no external service, migrations versioned in git. |
| Background job durability | **Celery + Redis** (Redis self-hosted container — not "Redis free tier" which is a hosted SaaS with caps) | Already named in the original master plan; this closes that gap and fixes bug #3. |
| Caching | Same Redis instance, separate logical DB index | Zero extra infra cost — reuse the Celery broker. |
| Auth | **Authlib** or **FastAPI-Users** (self-hosted, OSS) for email/password + GitHub/Google OAuth; **PyJWT** for sessions | No third-party auth SaaS (Clerk/Auth0 free tiers cap MAUs) — fully self-hosted, no usage limits. |
| Object storage (file uploads) | **MinIO** (self-hosted, S3-compatible, Docker container) | Free, unlimited, no Cloudinary/Firebase free-tier bandwidth caps. |
| Email (verification, password reset, notifications) | **Self-hosted SMTP via MailHog for dev** + any free-tier transactional sender for prod (e.g. a provider with a perpetual free allotment) — keep this pluggable behind one interface | Avoids hard-coupling to one vendor; MailHog is good enough for an open-source project where users bring their own SMTP. |
| Push/in-app notifications | **WebSocket via FastAPI's native `WebSocket` support** (no external pub/sub needed at this scale) | Zero new infra; reuses the existing FastAPI app. |
| PDF/CSV/Excel export | **WeasyPrint** (PDF), Python stdlib `csv`, **openpyxl** (Excel) | All free, all self-hosted, no API-call-metered SaaS. |
| Uptime monitoring | **Uptime Kuma** (self-hosted, OSS, add as another Compose service) | Free, no SaaS account needed (unlike most "free tier" uptime monitors). |
| E2E tests | **Playwright** | Free, OSS, already the de facto standard. |
| Architecture/sequence diagrams | **Mermaid** (renders directly in GitHub/markdown, no diagramming SaaS) | Keeps diagrams as version-controlled text. |

This list deliberately avoids every item in your "Completely Free Tech Stack" list that is actually a *hosted SaaS with a free tier* (Supabase, Firebase, Cloudinary, Clerk, Vercel, Railway, Render) in favor of self-hosted OSS equivalents that run in the same Docker Compose file with no usage caps, no account requirement, and no risk of the free tier changing terms later. Given you're open-sourcing this, "free forever, runs anywhere" is a stronger pitch than "free tier of a commercial product."

---

## 5. Phased Build Plan

Each phase is independently shippable. Do not start a phase before its dependencies are done.

### Phase 1 — Persistence & Multi-User Foundation (prerequisite for everything else)
1. Add PostgreSQL service to `docker-compose.yml`; add SQLAlchemy + Alembic to backend.
2. Define schema: `users`, `api_keys`, `jobs`, `repos`, `audit_log`.
3. Migrate the in-memory job tracker to Postgres-backed job state; wire Celery + Redis for durable background ingestion (fixes bug #3).
4. Add basic user model + email/password auth (FastAPI-Users or Authlib) + JWT sessions.
5. Add GitHub/Google OAuth login.
6. **Output:** users can sign up, log in, and ingestion jobs survive a restart.

### Phase 2 — Authorization & Security Hardening on Top of Auth  ✅ DONE (2026-06-29)
1. RBAC: roles (`owner`, `member`, `viewer`) scoped per repo. — `db.RepoMember` table (+ migration `3a1c7f4b9d20`), `auth/rbac.py` (role ordering, grants, `require_repo_role` dependency, superuser bypass), `api/routes_repos.py` (create repo → creator is owner; list; member grant/revoke).
2. Migrate API-key auth to be per-user (issued/revoked from a settings page), keep it as a service-to-service option alongside JWT. — `auth/apikeys.py` (hashed storage, raw key shown once), `api/routes_keys.py` (JWT-protected CRUD), unified `api/security.get_principal` accepts JWT **or** per-user key **or** static service key.
3. Audit log table populated on ingest/query/risk actions. — `api/audit.py` `record_audit()` (best-effort, never breaks the request), wired into ingest/query/risks plus apikey/repo lifecycle.
4. CSRF protection on any cookie-based session routes. — **N/A by design:** auth is JWT *bearer header* only (no cookie-based sessions), so there is no CSRF surface. Revisit in Phase 7 if a reverse proxy ever introduces cookie sessions.
5. **Output:** multiple users share one instance; repo membership/roles, per-user keys, and an audit trail are all in place. (Note: the analysis *data plane* is still a single shared ArcadeDB graph — true per-repo data isolation at query time is a larger graph-layer change tracked separately, not part of Phase 2's authz scope.)

### Phase 3 — File Handling, Notifications, Exports
1. File upload (zip a repo instead of requiring a Git URL) → MinIO storage.
2. CSV/Excel export of risk reports and impact analysis (`openpyxl`).
3. PDF report generation (WeasyPrint) — directly extends the "AI report generation" gap.
4. In-app toast notifications (frontend) + WebSocket push for job-completion events.
5. Email notifications (job done, risk threshold breached) via pluggable SMTP.
6. **Output:** no CLI/manual steps required to get a repo in or a report out.

### Phase 4 — AI Feature Depth
1. Externalize prompts into versioned template files (fixes bug #4) — also unlocks prompt experimentation without redeploy.
2. Multi-turn conversation history (store in Postgres, keyed by user+session).
3. AI summarization endpoint (summarize a file/module/PR diff).
4. AI report generation (turn a risk-scan + impact-analysis run into a narrative PDF, building on Phase 3's PDF pipeline).
5. AI code review mode (run risk detectors + LLM commentary on a diff, not just a whole repo).
6. **Output:** the AI layer moves from "answer one-shot questions" to "produce artifacts a team actually uses."

### Phase 5 — Collaboration & Visualization Depth
1. Team workspaces (multiple repos per team, shared via Phase 2's RBAC).
2. Comments + mentions on specific risk findings or graph nodes.
3. Activity feed (derived from the audit log).
4. Hotspot heatmap (churn × complexity — git_insights.py already computes the inputs; this is mostly a frontend viz task).
5. Timeline view of risk/health score over time (requires storing periodic scan snapshots in Postgres).
6. **Output:** the product stops being single-player.

### Phase 6 — Frontend Polish & DX
1. Dark/light mode (Tailwind `dark:` variants — low effort, high visibility).
2. Drag-and-drop upload (pairs with Phase 3 file upload).
3. Markdown rendering for AI-generated reports/answers (`react-markdown`, free).
4. Mobile responsiveness pass.
5. Playwright E2E suite covering: sign-up → ingest → query → risk view → export.
6. Mermaid architecture/sequence diagrams added to README and `/docs`.
7. **Output:** the project looks and tests like a finished open-source product, not a prototype.

### Phase 7 — Operability
1. Add Uptime Kuma to Compose for self-monitoring.
2. Document a reverse-proxy (Caddy or Traefik — both free/OSS, both get free auto-HTTPS via Let's Encrypt) in front of the stack for HTTPS — this is also where CSRF/cookie security gets finalized.
3. Admin guide + architecture diagrams in `/docs`.
4. **Output:** a self-hoster can run this behind HTTPS with one more `docker compose up` and not touch app code.

---

## 6. What NOT to Add (explicitly out of scope, and why)

- **GraphQL** — REST + the existing OpenAPI docs already serve every current frontend need; adding GraphQL is added surface area with no current consumer.
- **Vercel/Netlify/Railway/Render/Firebase/Supabase as deployment targets** — this product's value (local LLM, self-hosted graph/vector DB) is fundamentally a Docker Compose / self-hosted product. Chasing PaaS deploy targets fights the architecture instead of leaning into it as a selling point (see the enterprise-market report's "air-gapped deployment" recommendation).
- **Kanban/Gantt views** — this is a code-intelligence tool, not a project-management tool; if a team wants Gantt/Kanban they already have Jira/Linear. Skip unless a real user asks.
- **IndexedDB** — only relevant for offline-first web apps; this product is server-backed by design.

---

## 7. Immediate Next Action

Start Phase 1, step 1 (Postgres + SQLAlchemy + Alembic in `docker-compose.yml`/`backend/`) — everything else in this plan is blocked on having a relational store.

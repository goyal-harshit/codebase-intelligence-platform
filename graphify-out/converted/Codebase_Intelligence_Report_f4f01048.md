<!-- converted from Codebase_Intelligence_Report.docx -->

Codebase Intelligence Platform
Project Assessment, Improvement Plan & Enterprise Market Analysis
Prepared for Harshit
June 27, 2026

# Table of Contents

# Executive Summary
This report covers the Codebase Intelligence platform in the working folder: an AST-parsing -> knowledge-graph -> vector-search -> LLM Q&A system with risk detection and change-impact analysis. It has two existing planning documents (CODEBASE_INTELLIGENCE_MASTER_PLAN.md and ENTERPRISE_CODEBASE_INTELLIGENCE_ROADMAP.md) that describe the intended build. This report does not repeat that plan. Instead it assesses what is actually implemented in the code today, identifies concrete weaknesses, lays out a prioritized improvement and future-functionality roadmap, and benchmarks the project against what the market - Sourcegraph Cody, CodeScene, GitHub Copilot Enterprise, Glean, and internal developer platforms generally - is asking enterprise buyers to deliver in 2026.
Bottom line: the core pipeline (parse -> graph -> embed -> retrieve -> answer, plus 7 risk detectors and blast-radius analysis) is genuinely built and exercised by tests, not just scaffolded. Git history shows real bug fixes (duplicate entity IDs, Docker image name, schema ordering) over the last two weeks, not a one-shot generation. The platform is feature-complete for a single-user / trusted-network demo, but is not production- or enterprise-ready: there is no authentication, no input validation on user-supplied paths/URLs, string-built Cypher in three places, no observability, and an in-memory (non-durable) job queue. Closing those gaps is Part 2 of this report. Part 3 lays out what to build next to move from "working demo" toward a product enterprises would actually buy, and Part 4 grounds that roadmap in what the market is currently paying for.

# Part 1 - Current Implementation Assessment
This section is grounded in a direct read of the code in backend/ and frontend/, not the planning documents. Where the implementation diverges from the plan, that is called out explicitly.
## 1.1 What Is Actually Built and Working
## 1.2 Divergences From the Two Planning Documents
- Graph database: the plan offers "ArcadeDB or Neo4j Community" as alternatives. The build committed to ArcadeDB only - no Neo4j code path exists.
- Job queue: the plan specifies Celery + Redis for ingestion jobs. The implementation uses an in-memory Python job tracker (backend/api/jobs.py) - fine for a single process, but jobs are lost on restart and won't scale past one worker.
- docker-compose.yml has an LLM endpoint mismatch: the compose file configures an OpenAI-compatible (/v1) endpoint while backend/llm/ollama.py calls Ollama's native /api/generate. One of the two needs to change.
- The offline backend/analysis/ engine is a parallel implementation path (no ArcadeDB/Chroma dependency) that isn't mentioned in either planning document and isn't wired into the FastAPI routes - it appears to be a standalone CLI/webapp.
## 1.3 Concrete Issues Found (by severity)
### Critical - block production/multi-tenant use
- No authentication or authorization on any endpoint. Every route in backend/api/routes_*.py is open. Anyone with network access can trigger ingestion (including of arbitrary repo URLs - an SSRF vector), run queries, and read all data.
- LLM-generated Cypher is executed without validation. backend/retrieval/cypher_generator.py builds a prompt and runs whatever Cypher the model returns directly against the graph. A jailbroken or malformed model response becomes an arbitrary graph-mutating query.
- No input validation on ingest/impact endpoints. routes_ingest.py accepts a repo URL with no allow-list or scheme check (SSRF / internal-network probing); routes_impact.py's file_path parameter has no path-traversal guard.
### High - reliability and correctness risk
- Three places build Cypher with f-string interpolation instead of parameters (impact/analyzer.py, risk_detection/detector.py, cypher_generator.py). The interpolated values are currently integers/config, so today's risk is low, but the pattern is unsafe if any of those become user-controlled later.
- Errors are silently swallowed in the retrieval fallback path (a bare except: pass in retriever.py) and partial-failure ingestion jobs are still marked "complete" even if embedding or risk detection failed.
- Most graph/vector/risk tests run against fakes, not the real ArcadeDB/Chroma services. There is no end-to-end test that clones a repo, ingests it, and asks a question - the riskiest integration points are the least tested.
- Call-target resolution only keeps the last segment of a dotted call (obj.method() and other.method() both resolve to "method"), which will cause silent mis-wiring of CALLS edges and bad blast-radius results on any codebase with common method names.
### Medium - data quality and operability
- Raw code is truncated to 2000 characters before embedding, so large functions are embedded incompletely.
- Risk thresholds (god-object method count, complexity cutoff, long-method LOC, etc.) are hardcoded in detector.py with no API or config-file override.
- No rate limiting anywhere - the ingest endpoint can be hit repeatedly to exhaust CPU/memory.
- No structured logging/tracing/metrics, despite Prometheus being named in the plan - there is currently nothing to look at when something goes wrong in production.
## 1.4 MVP Feature Checklist vs. Reality

# Part 2 - Improvement Plan (Hardening the Existing Build)
Ordered by priority. Each item is scoped to be independently shippable; none requires a rewrite of the existing architecture.
## 2.1 Critical - Do Before Any External Exposure
- Add API authentication (API key header is sufficient for v1; design for OAuth2/OIDC later) and apply it to every route in backend/api/.
- Validate and allow-list ingest repo URLs (scheme, host, no internal/loopback ranges) to close the SSRF hole; validate file_path inputs against the known file set rather than passing them straight into a query.
- Replace free-text LLM-generated Cypher execution with either (a) a constrained query template the LLM can only fill parameters into, or (b) a post-generation validator that rejects anything outside an allow-listed set of clause types (MATCH/RETURN/WHERE only, no CREATE/DELETE/SET).
- Convert the three remaining f-string-built Cypher queries to parameterized queries, matching the pattern already used correctly in graph_db/builder.py.
## 2.2 High - Before Calling This "Production"
- Add rate limiting (e.g., slowapi/FastAPI middleware) on ingest and query endpoints.
- Replace the in-memory job tracker with Celery + Redis as the original plan specifies, so jobs survive restarts and can scale to multiple workers.
- Fix the docker-compose Ollama endpoint mismatch (pick native /api/generate or OpenAI-compatible /v1 and make both sides agree); add the missing Ollama model-pull bootstrap step.
- Add structured logging (request IDs, job IDs) and basic Prometheus metrics (query latency, ingestion duration, LLM call count) - both already named in the plan but not implemented.
- Write true end-to-end tests: clone a small real repo -> ingest -> query -> impact -> risk scan, run in CI against live ArcadeDB/Chroma/Ollama containers (GitHub Actions already exists; extend it).
- Fix call-target resolution to use qualified names (module.Class.method) instead of the bare last segment, to stop cross-wiring same-named methods.
## 2.3 Medium - Quality of Life
- Expose risk-detector thresholds via a config endpoint or settings file instead of hardcoding them.
- Differentiate "complete" from "complete with warnings" in job status when embedding or risk detection partially fails.
- Add frontend error boundaries and basic caching (SWR/React Query) so a backend hiccup doesn't blank the UI.
- Replace ingestion-progress polling with WebSocket/SSE push updates.
- Remove the 2000-character raw-code truncation cap for embeddings, or chunk long functions instead of truncating them.
- Decide whether the standalone backend/analysis/ offline engine is a permanent CLI mode or should be merged into the main API - right now it's an unreferenced parallel implementation, which is maintenance debt.

# Part 3 - Future Functionality Roadmap
The two existing planning documents already list a v1.1 "should have" tier (ownership mapping, coverage overlay, multi-repo, refactor recommendations, GitHub Action PR comments) and a v2+ "stretch" tier (IDE plugin, multi-agent refactoring, security smells, data-flow/taint tracking, API contract drift, chatops bot). Rather than restate those, this section: (a) sequences them against the hardening work in Part 2, and (b) adds functionality not yet named in either plan, informed by where the market has moved (see Part 4).
## 3.1 Near-Term (next 1-2 build cycles, builds directly on what exists)
## 3.2 Mid-Term (new capability, not in either existing plan)
- AI-generated-code guardrail: a CI check that runs risk detection specifically on the diff of a PR and flags when an AI coding assistant (Copilot/Cursor/Claude Code) has just dropped code health below a threshold - directly mirrors CodeScene's "Code Health gate for AI-generated code" positioning and is a natural fit given this platform already computes complexity/health metrics.
- Temporal / behavioral analysis: blend git_insights.py (churn, authorship) with the complexity metrics already computed to produce a "hotspot" score (frequently-changed + complex = highest risk), not just a static snapshot. This is the core differentiator CodeScene built its product around - the parser and git layer needed for it already exist here.
- Developer-experience / flow metrics surface: expose DORA-style (lead time, deploy frequency, change-fail rate, MTTR - derivable from git + CI metadata already being parsed) and basic SPACE-style satisfaction/activity signals on the dashboard. Engineering leaders increasingly want this combined with code-health data rather than as a separate tool.
- Self-correcting AI loop / MCP server: expose the risk-detection and impact-analysis engines as MCP tools so any AI coding assistant (Claude Code, Cursor, Copilot) can call them mid-task - "check the blast radius before you finish this edit." This is the single most consequential 2026 trend (see Part 4) and the existing FastAPI routes are most of the way there already; it mainly needs an MCP-protocol wrapper.
- SBOM / dependency-vulnerability cross-reference: the graph already models ExternalDependency nodes; joining that against an OSV/NVD feed turns "dependency bloat" detection into actual vulnerability detection, which is now a baseline enterprise security requirement, not a nice-to-have.
## 3.3 Long-Term (platform-level bets)
- IDE plugin (VS Code first) querying the existing API - already named as v2 in the plan; sequence it after auth is in place, since an IDE plugin without API keys is a non-starter.
- Self-hosted / air-gapped deployment profile (Ollama + ArcadeDB + Chroma are all already local-first) packaged explicitly for regulated industries - this is close to free given the current stack choice and is a real enterprise-sales differentiator (see Part 4).
- Governance and audit layer: per-query audit log, role-based access to specific repos/risk data, and policy controls (who can trigger ingestion of what). This stops being optional once the auth work in Part 2 lands and the product is sold to more than one team.
- Refactoring-recommendation agent that proposes (not auto-applies) specific fixes for detected risks - god-object splits, dead-code removal PRs - gated behind human review. The plan's v2 "multi-agent refactoring assistant" is the right instinct; scope it to recommend-and-PR rather than autonomously commit, which is both safer and matches what buyers currently trust AI agents to do unsupervised.

# Part 4 - What Enterprises Actually Want From This Category of Software
This section synthesizes current (2026) market signal from Sourcegraph Cody, CodeScene, and enterprise engineering-platform research, to ground Part 3's prioritization in real buyer demand rather than feature speculation.
## 4.1 The Market Context
"Codebase intelligence" has split into two converging tracks. One track is AI coding assistants that need deep codebase context to be useful at enterprise scale (Sourcegraph Cody, GitHub Copilot Enterprise) - these are sold as developer tools but increasingly marketed on governance and multi-repo reasoning. The other track is engineering-intelligence/code-health platforms (CodeScene, and the broader DORA/SPACE/DevEx measurement space) sold to engineering leadership on risk reduction and productivity measurement, not to individual developers. This project currently has pieces of both (NL Q&A is track one, risk detection is track two) without fully committing to either buyer. That's a positioning decision worth making deliberately, not a gap - see 4.4.
## 4.2 What Track-One Buyers (AI coding assistants) Are Paying For
- Multi-repository, architecture-aware context - Cody Enterprise retrieves across up to 10 repos simultaneously specifically so it can answer "what else calls this API" across microservice boundaries, not just within one repo. This is exactly this platform's blast-radius feature, generalized across repos.
- Admin-controlled model choice and no-training guarantees - enterprises want to pick the underlying LLM (and increasingly run it themselves) rather than be locked to one vendor's model. This project's Ollama-first, fully local design is already aligned with this - it's a sales point, not just a technical choice.
- BYOC / self-hosted / air-gapped deployment for regulated environments - explicitly called out as a reason large enterprises pick Sourcegraph over hosted-only competitors.
- SOC 2 / formal AI governance - over 60% of enterprises are expected to require formal AI-governance frameworks (e.g., ISO 42001) by 2026; this is now a checkbox in procurement, not a future concern.
- Fast onboarding of new engineers onto large codebases - cited as a concrete ROI metric (one vendor's customer cut onboarding from weeks to 1-2 days) and is the most relatable, demo-able value of NL Q&A over a codebase.
## 4.3 What Track-Two Buyers (Engineering Leadership) Are Paying For
- Temporal/behavioral analysis, not just static snapshots - CodeScene's core differentiator is weighing code quality by how the team actually works with the code (churn x complexity), not a one-time scan. This is squarely in this project's reach given git_insights.py already exists.
- A single validated code-quality metric leadership can track over time and tie to defect rates and delivery speed - CodeScene's "Code Health" score is marketed specifically as research-backed and tied to business outcomes, not just a complexity number.
- Guardrails on AI-generated code specifically - a 2026-specific ask: as AI assistants now write a large share of committed code, leadership wants automated gates that block merges when AI-written code drops measured quality below a bar, and tooling that makes legacy code "AI-ready" (i.e., safe context for an assistant to edit).
- IDE- and PR-level enforcement, not just a dashboard - real-time in-IDE smell detection and PR-blocking quality gates are how these tools actually change behavior; a report nobody opens doesn't move metrics.
- Org/people-level insight (off-boarding risk, team autonomy, single points of failure) derived from the same ownership data, not just file-level metrics.
- Productivity measurement beyond DORA alone - DORA's delivery metrics are now seen as insufficient on their own (especially with AI writing 30-70% of code in some orgs); buyers want them combined with developer-experience signals (the DX "Core 4": speed, effectiveness, quality, business impact) rather than delivery velocity in isolation.
## 4.4 Positioning Recommendation for This Project
Given the existing stack, the more defensible near-term position is track two (engineering-intelligence / risk and architecture analysis for leadership and senior engineers) with NL Q&A as a feature inside it, rather than competing head-on with Cody/Copilot as a coding assistant. The reasoning:
- The hardest-to-replicate asset already built here is the knowledge graph + risk detectors + blast radius, which is exactly CodeScene/Sourcegraph's differentiated layer - not the LLM chat wrapper around it, which every competitor also has.
- A fully local/self-hosted stack (Ollama + ArcadeDB + Chroma) is a genuine, defensible advantage for the compliance-sensitive buyers named in 4.2 and 4.3, and costs nothing extra to maintain given it's already the architecture.
- The MCP-server idea in 3.2 lets this platform plug into whatever coding assistant the team already pays for (Copilot, Cursor, Claude Code) instead of trying to replace it - turning a competitive threat (AI assistants commoditizing chat-over-code) into a complementary integration.

# Part 5 - Consolidated Priority Table
A single view combining hardening (Part 2) and new functionality (Part 3), ordered by recommended sequence. Effort is relative, not in hours.

## Sources
Sourcegraph Cody enterprise features and 2026 pricing:
Sourcegraph Cody docs
Sourcegraph Cody Review 2026 (WeavAI)
Sourcegraph - Code Understanding, Oversight and Evolution
Cody for Visual Studio (GitHub)
CodeScene behavioral code analysis:
CodeScene - Behavioral Code Analysis
CodeScene - Scale AI Coding Safely
CodeScene - Technical Debt Management
Enterprise AI coding tools / 2026 landscape:
13 Best AI Coding Tools for Complex Codebases in 2026 (Augment Code)
5 AI Tools That Scale for 400k+ Enterprise Codebases (Augment Code)
5 Enterprise Tech Trends for 2026 (AngelHack DevLabs)
Engineering productivity metrics (DORA/SPACE/DevEx):
DORA - Platform Engineering capability
DORA vs SPACE vs DevEx 2026 (PanDev Metrics)
DORA Metrics Are Not Enough in 2026 (Oobeya)
How to measure developer productivity and platform ROI (platformengineering.org)
| Layer | Status |
| --- | --- |
| AST Parsing | Tree-sitter-based UniversalParser covering 9+ languages (Python, JS/TS, Go, Rust, Java, Ruby, PHP, C/C#), plus a pure-stdlib Python fallback. Extracts entities, calls, complexity, LOC, docstrings. Complete and tested. |
| Knowledge Graph | ArcadeDB (chosen over the Neo4j alternative named in the plan). Schema has 9 vertex types and 8 edge types. Builder uses parameterized UNWIND batches - no injection risk on the bulk-insert path. |
| Vector Search | ChromaDB + BAAI/bge-small-en-v1.5 embeddings, AST-aware chunking (one chunk = one whole entity). Complete. |
| Hybrid Retrieval | Keyword-based structural/semantic router, LLM-driven NL-to-Cypher generation via Ollama, semantic fallback on failure. Complete and functional, not just stubbed. |
| Risk Detection | 7 detectors live: god objects, dead code, high complexity, long methods, shotgun surgery, circular dependencies, deep inheritance. Circular-dependency and deep-inheritance detectors are implemented but starved of data because IMPORTS/INHERITS_FROM edges aren't yet rich enough to trigger them reliably. |
| Impact / Blast Radius | Working backward-CALLS graph walk up to configurable depth. Affected-test lookup is intentionally stubbed (returns empty until test-coverage ingestion is built). |
| Offline Analysis Engine | A separate, sizeable backend/analysis/ module (networkx-based) duplicates much of the graph-DB functionality without external services - health score, hotspots, ownership via git blame, lightweight pattern-matching Q&A. This looks like a fallback/CLI mode that doesn't yet share code with the main pipeline. |
| FastAPI Backend | All five route groups (ingest, query, risks, impact, stats) are implemented and wired to real services, not mocks. Jobs are tracked in-memory (not Celery/Redis as the plan specifies). |
| Frontend | Next.js 14 app with five functional pages (ingest/home, dashboard, query, risks, impact) and a force-graph visualization. All pages call the real backend, not placeholder data. |
| Tests | 8 test files with real assertions (parser, graph_db, risk_detection, retrieval, api, analysis). Most graph/risk tests run against a FakeClient rather than a live ArcadeDB instance; only one gated integration test touches the real database. |
| Planned MVP Feature | Status | Note |
| --- | --- | --- |
| Multi-language AST parsing | Done | 9+ languages via tree-sitter |
| Knowledge graph construction | Done | ArcadeDB, not Neo4j |
| Incremental re-indexing | Partial | Single-file re-parse can't resolve cross-file calls without full rebuild |
| Semantic code search | Done | ChromaDB + bge-small |
| Structural graph queries (NL to Cypher) | Done | No output validation |
| Hybrid retrieval | Done |  |
| NL Q&A with citations | Done |  |
| Change impact / blast radius | Done | Affected-tests lookup stubbed |
| 5+ risk detectors | Done | 7 implemented; 2 data-starved |
| REST API w/ OpenAPI docs | Done | No auth, no rate limit |
| Web dashboard | Done | No error boundaries, no caching |
| Docker Compose deploy | Partial | LLM endpoint mismatch needs fixing |
| Feature | Why it's next, concretely |
| --- | --- |
| PR-level impact comments (GitHub Action) | Already named in the plan's v1.1 tier and is the single highest-leverage feature for adoption - it puts blast-radius output in front of a reviewer at the moment a decision is made, with zero UI required. |
| Code ownership + bus-factor surfacing in the API/UI | backend/analysis/git_insights.py already computes this offline; it just isn't exposed through the FastAPI routes or the dashboard yet. This is mostly wiring, not new analysis. |
| Test-coverage ingestion | Unblocks the already-stubbed find_affected_tests() in impact/analyzer.py - turns an existing TODO into a working "what tests should I run" feature. |
| Configurable risk thresholds + custom rules API | Lets teams tune god-object/complexity cutoffs per codebase instead of hardcoded values, and is a prerequisite for any team adopting this as a merge gate (see CodeScene's quality-gate model in Part 4). |
| Multi-repo / monorepo-of-services support | Named as v1.1 in the existing roadmap. With ArcadeDB already multi-database capable, this is schema + UI work (cross-repo CALLS/IMPORTS edges) rather than new infrastructure. |
| Item | Category | Effort | Depends on |
| --- | --- | --- | --- |
| API authentication + input validation | Hardening | Medium | - |
| Constrain/validate LLM-generated Cypher | Hardening | Medium | - |
| Parameterize remaining f-string Cypher | Hardening | Small | - |
| Celery + Redis job queue | Hardening | Medium | Auth (shared infra work) |
| Fix docker-compose LLM endpoint mismatch | Hardening | Small | - |
| Logging + Prometheus metrics | Hardening | Medium | - |
| End-to-end tests on live services | Hardening | Medium | Docker fix |
| PR-comment GitHub Action (blast radius on diff) | Near-term feature | Medium | Auth, stable API |
| Expose ownership/bus-factor in API + UI | Near-term feature | Small | - |
| Test-coverage ingestion | Near-term feature | Medium | - |
| Configurable risk thresholds | Near-term feature | Small | - |
| Multi-repo support | Near-term feature | Large | Schema extension |
| Hotspot scoring (churn x complexity) | Mid-term feature | Medium | Ownership exposure |
| AI-generated-code quality gate | Mid-term feature | Medium | Configurable thresholds, PR action |
| MCP server wrapper for assistants | Mid-term feature | Medium | Auth |
| SBOM / vulnerability cross-reference | Mid-term feature | Medium | - |
| DORA/DevEx metrics dashboard | Mid-term feature | Large | Git/CI metadata pipeline |
| IDE plugin | Long-term | Large | Auth, stable API |
| Air-gapped deployment packaging | Long-term | Medium | Hardening complete |
| Governance/audit layer | Long-term | Large | Auth, RBAC |
| Refactoring-recommendation agent (recommend, not auto-apply) | Long-term | Large | Risk detection maturity |
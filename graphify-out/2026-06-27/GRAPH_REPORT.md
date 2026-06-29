# Graph Report - .  (2026-06-27)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 793 nodes · 1274 edges · 54 communities (45 shown, 9 thin omitted)
- Extraction: 91% EXTRACTED · 9% INFERRED · 0% AMBIGUOUS · INFERRED: 110 edges (avg confidence: 0.75)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `f210c145`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- [[_COMMUNITY_Repository Parsing|Repository Parsing]]
- [[_COMMUNITY_Database Client|Database Client]]
- [[_COMMUNITY_Code Analysis|Code Analysis]]
- [[_COMMUNITY_Answer Generator|Answer Generator]]
- [[_COMMUNITY_Code Graph|Code Graph]]
- [[_COMMUNITY_Dependency Graph|Dependency Graph]]
- [[_COMMUNITY_Codebase Intelligence Platform|Codebase Intelligence Platform]]
- [[_COMMUNITY_Risk Detection Engine|Risk Detection Engine]]
- [[_COMMUNITY_Change Impact Analysis|Change Impact Analysis]]
- [[_COMMUNITY_Application Settings|Application Settings]]
- [[_COMMUNITY_Project Dependencies|Project Dependencies]]
- [[_COMMUNITY_Risk Management|Risk Management]]
- [[_COMMUNITY_TypeScript Config|TypeScript Config]]
- [[_COMMUNITY_Fake Embedder|Fake Embedder]]
- [[_COMMUNITY_Request Handler|Request Handler]]
- [[_COMMUNITY_Codebase Intelligence|Codebase Intelligence]]
- [[_COMMUNITY_Dependency Service|Dependency Service]]
- [[_COMMUNITY_LLM Integration|LLM Integration]]
- [[_COMMUNITY_Knowledge Graph Architecture|Knowledge Graph Architecture]]
- [[_COMMUNITY_Account Login Module|Account Login Module]]
- [[_COMMUNITY_Semantic Retrieval Pipeline|Semantic Retrieval Pipeline]]
- [[_COMMUNITY_Backend Development Phases|Backend Development Phases]]
- [[_COMMUNITY_API Testing|API Testing]]
- [[_COMMUNITY_Code Q&A|Code Q&A]]
- [[_COMMUNITY_Parser Module|Parser Module]]
- [[_COMMUNITY_Enterprise Roadmap|Enterprise Roadmap]]
- [[_COMMUNITY_Full Project Structure|Full Project Structure]]
- [[_COMMUNITY_Docker Deployment|Docker Deployment]]
- [[_COMMUNITY_ArcadeDB Setup|ArcadeDB Setup]]
- [[_COMMUNITY_App Layout|App Layout]]
- [[_COMMUNITY_Account Module|Account Module]]
- [[_COMMUNITY_Community 64|Community 64]]
- [[_COMMUNITY_Community 65|Community 65]]
- [[_COMMUNITY_Community 66|Community 66]]
- [[_COMMUNITY_Agentic Framework|Agentic Framework]]
- [[_COMMUNITY_Web App Testing|Web App Testing]]
- [[_COMMUNITY_Project Charter|Project Charter]]
- [[_COMMUNITY_Feature Catalog|Feature Catalog]]
- [[_COMMUNITY_Testing Strategy|Testing Strategy]]
- [[_COMMUNITY_Risk Detection Engine|Risk Detection Engine]]
- [[_COMMUNITY_Monitoring Setup|Monitoring Setup]]
- [[_COMMUNITY_Observability|Observability]]
- [[_COMMUNITY_Testing Strategy|Testing Strategy]]
- [[_COMMUNITY_Hardware Budgeting|Hardware Budgeting]]
- [[_COMMUNITY_Analysis Engine|Analysis Engine]]
- [[_COMMUNITY_Community 91|Community 91]]
- [[_COMMUNITY_Community 92|Community 92]]
- [[_COMMUNITY_Community 93|Community 93]]
- [[_COMMUNITY_Next.js Config|Next.js Config]]
- [[_COMMUNITY_PostCSS Config|PostCSS Config]]
- [[_COMMUNITY_Tailwind Config|Tailwind Config]]

## God Nodes (most connected - your core abstractions)
1. `analyze_repository()` - 34 edges
2. `ArcadeDBClient` - 27 edges
3. `GraphBuilder` - 25 edges
4. `UniversalParser` - 21 edges
5. `RiskDetector` - 21 edges
6. `DiGraph` - 17 edges
7. `_e()` - 17 edges
8. `ImpactAnalyzer` - 17 edges
9. `CodeEntity` - 16 edges
10. `CodeRelationship` - 16 edges

## Surprising Connections (you probably didn't know these)
- `main()` --calls--> `analyze_repository()`  [INFERRED]
  scripts/analyze.py → backend/analysis/engine.py
- `main()` --calls--> `parse_repository()`  [INFERRED]
  scripts/build_graph.py → backend/ast_parser/__init__.py
- `main()` --calls--> `parse_repository()`  [INFERRED]
  scripts/embed_repo.py → backend/ast_parser/__init__.py
- `main()` --calls--> `parse_repository()`  [INFERRED]
  scripts/parse_repo.py → backend/ast_parser/__init__.py
- `main()` --calls--> `ArcadeDBClient`  [INFERRED]
  scripts/ask.py → backend/graph_db/client.py

## Import Cycles
- None detected.

## Communities (54 total, 9 thin omitted)

### Community 0 - "Repository Parsing"
Cohesion: 0.06
Nodes (35): parse_repository(), AST parsing engine (Phase 1)., Parse an entire repo: returns (entities, resolved_relationships)., CodeEntity, CodeRelationship, Language-agnostic AST parser built on tree-sitter.  Extracts CodeEntity (functio, Names of classes this class extends (last path component only)., Top-level module name(s) of an import statement. (+27 more)

### Community 1 - "Database Client"
Cohesion: 0.06
Nodes (37): Any, _file_id(), GraphBuilder, label_for(), Bulk ingestion of parsed entities/relationships into the graph.  Uses parameteri, ArcadeDBClient, ArcadeDBError, Thin HTTP client for ArcadeDB.  Wraps ArcadeDB's REST API (https://docs.arcadedb (+29 more)

### Community 2 - "Code Analysis"
Cohesion: 0.05
Nodes (47): _all_paths_to_roots(), analyze_repository(), _build_call_graph(), _build_index(), _call_graph_metrics(), CodebaseAnalysis, _complexity(), _dependencies() (+39 more)

### Community 3 - "Answer Generator"
Cohesion: 0.09
Nodes (28): AnswerGenerator, Turns retrieved context into a cited natural-language answer via the LLM., CypherGenerator, LLM-backed English->Cypher translation with few-shot prompting., extract_sources(), QueryEngine, End-to-end query engine: retrieve -> answer -> cite.  This is the single entry p, Best-effort list of file paths cited by the retrieved context. (+20 more)

### Community 4 - "Code Graph"
Cohesion: 0.09
Nodes (23): CodeGraph(), ForceGraph2D, GraphData, RiskTable(), SEVERITY_COLOR, CARDS, StatsGrid(), ImpactPage() (+15 more)

### Community 5 - "Dependency Graph"
Cohesion: 0.15
Nodes (29): graph_widget(), _layout(), Static, pre-laid-out dependency-graph widget (canvas, zero-dependency).  The lay, Deterministic force-directed layout. Mutates nodes with x,y in [-W,W]., _bars(), _e(), Render a CodebaseAnalysis to a self-contained HTML dashboard and JSON., render_html() (+21 more)

### Community 6 - "Codebase Intelligence Platform"
Cohesion: 0.06
Nodes (32): Build the graph from a repo, Continuous Integration, Embed a repo, Enterprise Codebase Intelligence Platform, Phase 1 — AST Parser, Phase 2 — Graph Database (ArcadeDB), Phase 3 — Vector DB & Embeddings (ChromaDB), Phase 4 — Risk Detection Engine (+24 more)

### Community 7 - "Risk Detection Engine"
Cohesion: 0.11
Nodes (17): persist_risks(), Architecture-risk detection over the code graph.  Each rule is a Cypher query ag, Write detected risks back to the graph as SecurityIssue vertices., RiskDetector, Risk detection engine (Phase 4): architecture-smell detection over the graph., main(), FakeClient, Phase 4 tests.  Offline against a fake graph client that returns canned query ro (+9 more)

### Community 8 - "Change Impact Analysis"
Cohesion: 0.12
Nodes (17): impact(), ImpactAnalyzer, Change-impact / blast-radius analysis.  Given a file (or a single entity), walk, Tests covering entities in the file. Needs COVERED_BY edges (Phase 4+         da, Change-impact / blast-radius analysis (Phase 5)., main(), FakeClient, Phase 5 tests.  Offline against a fake graph client returning canned hop rows; v (+9 more)

### Community 9 - "Application Settings"
Cohesion: 0.10
Nodes (14): App-level settings. Service clients read their own env vars in their own constru, Settings, JobManager, In-memory ingestion-job tracking.  A process-local job store with status transit, IngestRequest, start_ingest(), clone_repo(), The ingestion pipeline, run in a background thread.  Steps mirror the master pla (+6 more)

### Community 10 - "Project Dependencies"
Cohesion: 0.08
Nodes (25): dependencies, axios, lucide-react, next, react, react-dom, react-force-graph-2d, recharts (+17 more)

### Community 11 - "Risk Management"
Cohesion: 0.50
Nodes (4): 4.1 Architectural Risk Scoring, 4.2 Change Impact Analysis, 4.3 Ownership & Test Coverage Tracking, Phase 4: Risk Detection & Architecture Analysis (Weeks 5-7)

### Community 12 - "TypeScript Config"
Cohesion: 0.11
Nodes (18): compilerOptions, allowJs, esModuleInterop, incremental, isolatedModules, jsx, lib, module (+10 more)

### Community 17 - "Fake Embedder"
Cohesion: 0.08
Nodes (19): main(), FakeCollection, FakeEmbedder, Phase 3 tests.  Unit tests run offline with a deterministic fake embedder and a, Deterministic 4-dim vectors derived from text length — no ML deps., test_chunk_contains_signal_and_metadata(), test_embed_and_store_batches(), test_integration_semantic_search() (+11 more)

### Community 18 - "Request Handler"
Cohesion: 0.26
Nodes (7): BaseHTTPRequestHandler, _examples(), Handler, landing(), main(), _make_server(), _store()

### Community 19 - "Codebase Intelligence"
Cohesion: 0.12
Nodes (15): 16.1 Sample GitHub Actions CI (`.github/workflows/ci.yml`), 1.1 Installation Commands (Run These First, In Order), Enterprise Codebase Intelligence Platform — Master Implementation Plan, Full-Detail Build Guide: What to Build, How, From Where, and What to Expect, PART 16 — DOCUMENTATION & OPEN-SOURCE READINESS CHECKLIST, PART 17 — COST BREAKDOWN (Real Numbers), PART 18 — WEEK-BY-WEEK MASTER TIMELINE, PART 19 — TROUBLESHOOTING GUIDE (Common Issues) (+7 more)

### Community 21 - "Dependency Service"
Cohesion: 0.11
Nodes (12): get_graph_client(), get_llm(), get_query_engine(), get_vector_store(), Lazily-constructed singleton service clients for dependency injection.  Construc, risks(), LLM access layer (Phase 6)., LLMClient (+4 more)

### Community 22 - "LLM Integration"
Cohesion: 0.27
Nodes (9): available(), build_context(), chat(), explain(), _headers(), Optional local-LLM integration (Ollama by default; any OpenAI-compatible endpoin, True if an LLM endpoint answers. Cheap, never raises., OpenAI-compatible chat completion. Raises on failure. (+1 more)

### Community 23 - "Knowledge Graph Architecture"
Cohesion: 0.20
Nodes (10): 1.1 AST Parsing Engine, 2.1 Graph Database Selection, 2.2 Graph Schema Design, 2.3 Data Ingestion Pipeline, 3.1 Vector DB Selection, 3.2 Embedding Strategy, Part I: Foundation & Architecture, Phase 1: Core Technology Stack (Weeks 1-2) (+2 more)

### Community 37 - "Account Login Module"
Cohesion: 0.31
Nodes (5): Account, helper(), AdminAccount, Sample module for parser tests., validate_user()

### Community 38 - "Semantic Retrieval Pipeline"
Cohesion: 0.22
Nodes (9): 5.1 Semantic + Structural Retrieval (Hybrid RAG), 5.2 LLM-to-Cypher Translation, 5.3 Answer Generation Pipeline, 6.1 Local Ollama Setup, 6.2 Context Window Optimization, 6.3 LLM API Integration, Part II: Advanced Features, Phase 5: Natural Language Query Engine (Weeks 6-9) (+1 more)

### Community 39 - "Backend Development Phases"
Cohesion: 0.22
Nodes (9): 7.1 API Endpoints, 7.2 Background Job Processing, 8.1 React/Next.js Dashboard, 9.1 Docker Compose Stack, 9.2 Deployment Options, Part III: Platform & Operations, Phase 7: FastAPI Backend (Weeks 10-11), Phase 8: Web Frontend (Weeks 11-13) (+1 more)

### Community 42 - "Code Q&A"
Cohesion: 0.50
Nodes (7): answer(), _brief(), _by_name(), _explain(), _match_file(), Built-in, no-setup Q&A over the code index. Deterministic, offline.  Understands, _search()

### Community 43 - "Parser Module"
Cohesion: 0.25
Nodes (8): 4.1 What You're Building, 4.2 Exact Setup, 4.3 Core Parser Module — `backend/ast_parser/parser.py`, 4.4 Repository Walker — `backend/ast_parser/repo_walker.py`, 4.5 Symbol Resolution Pass (resolves `calls` edges to real entity IDs), 4.6 Where to Learn Tree-sitter (free resources), 4.7 Testing Checkpoint, PART 4 — PHASE 1: AST PARSING ENGINE (Weeks 1-2)

### Community 44 - "Enterprise Roadmap"
Cohesion: 0.25
Nodes (7): Conclusion, Enterprise Codebase Intelligence Platform - Complete Roadmap, Executive Summary, Future Enhancements (Post-MVP), GitHub Repository Structure, Success Metrics, Timeline & Milestones

### Community 51 - "Full Project Structure"
Cohesion: 0.29
Nodes (7): 10.1 Full Project Structure, 10.2 `requirements.txt`, 10.3 `main.py`, 10.4 Full Endpoint Reference, 10.5 Celery + Redis Setup, 10.6 Acceptance Criteria for Phase 7, PART 10 — PHASE 7: FASTAPI BACKEND (Weeks 10-11)

### Community 52 - "Docker Deployment"
Cohesion: 0.29
Nodes (7): 12.1 Full `docker-compose.yml`, 12.2 `backend/Dockerfile`, 12.3 `frontend/Dockerfile`, 12.4 First-Run Bootstrap Script (`scripts/setup.sh`), 12.5 Free/Cheap Hosting Options (where to deploy), 12.6 Acceptance Criteria for Phase 9, PART 12 — PHASE 9: DOCKER & DEPLOYMENT (Weeks 12-14)

### Community 53 - "ArcadeDB Setup"
Cohesion: 0.29
Nodes (7): 5.1 Install & Run ArcadeDB, 5.2 Python Client, 5.3 Full Graph Schema (write this exactly as Cypher setup), 5.4 Bulk Ingestion (Batch Inserts — Critical for Performance), 5.5 Incremental Update Strategy (SHA-256 based), 5.6 Acceptance Criteria for Phase 2, PART 5 — PHASE 2: GRAPH DATABASE (Weeks 2-4)

### Community 63 - "Account Module"
Cohesion: 0.47
Nodes (3): Account, helper(), validateUser()

### Community 64 - "Community 64"
Cohesion: 0.33
Nodes (6): 11.1 Project Setup, 11.2 Full Page Inventory, 11.3 Example: Query Page (`app/query/page.tsx`), 11.4 Graph Visualization Component (`components/CodeGraph.tsx`), 11.5 Acceptance Criteria for Phase 8, PART 11 — PHASE 8: NEXT.JS FRONTEND (Weeks 11-13)

### Community 65 - "Community 65"
Cohesion: 0.33
Nodes (6): 6.1 Install, 6.2 Embedding Model Setup, 6.3 AST-Aware Chunking Strategy, 6.4 Embedding Pipeline, 6.5 Acceptance Criteria for Phase 3, PART 6 — PHASE 3: VECTOR DATABASE & EMBEDDINGS (Weeks 3-4)

### Community 66 - "Community 66"
Cohesion: 0.33
Nodes (6): 9.1 Query Router, 9.2 LLM-to-Cypher Translator (with few-shot prompting), 9.3 Hybrid Retriever (Full Implementation), 9.4 Answer Generator, 9.5 Acceptance Criteria for Phase 6, PART 9 — PHASE 6: HYBRID RETRIEVAL + LLM QUERY ENGINE (Weeks 8-10)

### Community 67 - "Agentic Framework"
Cohesion: 0.33
Nodes (6): 10.1 Agentic Framework, 10.2 Refactoring Recommendation Engine, 11.1 SAST Integration, Part IV: Advanced Features & Optimization, Phase 10: Multi-Agent Orchestration (Weeks 15-17), Phase 11: Security & Compliance Scanning (Weeks 18-19)

### Community 74 - "Web App Testing"
Cohesion: 0.60
Nodes (5): _a(), test_index_built(), test_qa_explain_and_callers(), test_qa_file_and_search(), test_webapp_pages_render()

### Community 75 - "Project Charter"
Cohesion: 0.40
Nodes (5): 0.1 What You Are Building, 0.2 Definition of Done (v1.0), 0.3 Who This Is For, 0.4 Non-Goals (v1.0), PART 0 — PROJECT CHARTER

### Community 76 - "Feature Catalog"
Cohesion: 0.40
Nodes (5): 13.1 Core Features (MVP — Must Have), 13.2 Advanced Features (v1.1 — Should Have), 13.3 Stretch Features (v2+ — Nice to Have), 13.4 Feature → Phase Mapping, PART 13 — FULL FEATURE CATALOG (Complete List)

### Community 77 - "Testing Strategy"
Cohesion: 0.40
Nodes (5): 14.1 Unit Test Coverage Targets, 14.2 Sample Test Repos to Validate Against (use these specific public repos), 14.3 Integration Test Script, 14.4 Load Testing (use `locust`, free), PART 14 — TESTING STRATEGY (Full Detail)

### Community 78 - "Risk Detection Engine"
Cohesion: 0.40
Nodes (5): 7.1 Full List of Risk Rules to Implement, 7.2 Risk Scorer Implementation, 7.3 Persisting Risks Back to Graph (for queryability), 7.4 Acceptance Criteria for Phase 4, PART 7 — PHASE 4: RISK DETECTION ENGINE (Weeks 5-7)

### Community 85 - "Monitoring Setup"
Cohesion: 0.50
Nodes (4): 15.1 Prometheus + Grafana (Docker addition), 15.2 Metrics to Track, 15.3 Dashboards to Build in Grafana, PART 15 — MONITORING & OBSERVABILITY (Weeks 20-21)

### Community 86 - "Observability"
Cohesion: 0.50
Nodes (4): 12.1 Metrics & Logging, 12.2 Dashboard Queries, Part V: Monitoring & Iteration, Phase 12: Observability & Analytics (Weeks 20-21)

### Community 87 - "Testing Strategy"
Cohesion: 0.50
Nodes (4): 13.1 Unit Tests, 13.2 Integration Tests, Part VI: Testing & Quality, Phase 13: Testing Strategy (Weeks 22-23)

### Community 89 - "Hardware Budgeting"
Cohesion: 0.50
Nodes (4): Free/Open-Source Budget, Hardware (Minimum), Hardware (Recommended for Production), Resource Requirements

## Knowledge Gaps
- **182 isolated node(s):** `RISK_COLOR`, `metadata`, `SEVERITIES`, `ForceGraph2D`, `LINKS` (+177 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **9 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `parse_repository()` connect `Repository Parsing` to `Application Settings`, `Code Analysis`, `Database Client`, `Fake Embedder`?**
  _High betweenness centrality (0.154) - this node is a cross-community bridge._
- **Why does `analyze_repository()` connect `Code Analysis` to `Repository Parsing`, `Request Handler`, `Web App Testing`, `Dependency Graph`?**
  _High betweenness centrality (0.135) - this node is a cross-community bridge._
- **Why does `run_ingestion()` connect `Application Settings` to `Repository Parsing`, `Database Client`, `Fake Embedder`, `Risk Detection Engine`?**
  _High betweenness centrality (0.127) - this node is a cross-community bridge._
- **Are the 16 inferred relationships involving `analyze_repository()` (e.g. with `parse_repository()` and `main()`) actually correct?**
  _`analyze_repository()` has 16 INFERRED edges - model-reasoned connections that need verification._
- **Are the 11 inferred relationships involving `ArcadeDBClient` (e.g. with `run_ingestion()` and `GraphBuilder`) actually correct?**
  _`ArcadeDBClient` has 11 INFERRED edges - model-reasoned connections that need verification._
- **Are the 5 inferred relationships involving `GraphBuilder` (e.g. with `run_ingestion()` and `ArcadeDBClient`) actually correct?**
  _`GraphBuilder` has 5 INFERRED edges - model-reasoned connections that need verification._
- **Are the 2 inferred relationships involving `UniversalParser` (e.g. with `_parse()` and `test_unsupported_extension_returns_empty()`) actually correct?**
  _`UniversalParser` has 2 INFERRED edges - model-reasoned connections that need verification._
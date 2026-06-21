# Enterprise Codebase Intelligence Platform

Open-source platform that ingests any Git repo, builds a knowledge graph + vector index of its code, and answers plain-English questions, detects architecture risks, and computes change-impact / blast radius.

See `CODEBASE_INTELLIGENCE_MASTER_PLAN.md` for the full build spec.

## Status

| Phase | Component | State |
|---|---|---|
| 1 | AST parsing engine | **Done** |
| 2 | Graph database (ArcadeDB) | **Done** |
| 3 | Vector DB + embeddings | Not started |
| 4 | Risk detection | Not started |
| 5 | Impact / blast radius | Not started |
| 6 | Hybrid retrieval + LLM Q&A | Not started |
| 7 | FastAPI backend | Not started |
| 8 | Next.js frontend | Not started |
| 9 | Docker / deployment | Not started |

## Phase 1 — AST Parser

Language-agnostic parser (tree-sitter) extracting `CodeEntity` (functions, classes,
methods) and `CodeRelationship` (contains, calls) objects. Supports Python, JS/TS,
Go, Rust, Java, and more.

### Setup

```bash
cd backend
pip install -r requirements.txt
```

### Run on a repo

```bash
python scripts/parse_repo.py /path/to/repo --json out.json
```

### Test

```bash
cd backend && python -m pytest tests/ -q
```

### Validated

Parsed Flask (`src/`, 24 files) in 0.28s — 388 functions/methods, 53 classes,
extracted within ~7% of `grep` ground truth.

## Phase 2 — Graph Database (ArcadeDB)

Ingests parsed `CodeEntity`/`CodeRelationship` objects into an ArcadeDB graph
(`File`/`Function`/`Class`/`Interface`/`Module` vertices; `CONTAINS`/`CALLS`/…
edges). Ingestion uses parameterized `UNWIND $rows` batches — no string-built
Cypher — and typed, index-backed edge matches. Includes SHA-256–based
incremental re-indexing that re-parses only changed files and prunes deleted ones.

### Run ArcadeDB

```bash
docker run -d --name arcadedb -p 2480:2480 -p 2424:2424 \
  -e JAVA_OPTS="-Xmx2g" -e arcadedb.server.rootPassword=ChangeMe123! \
  -v arcadedb_data:/home/arcadedb/databases arcadedb/arcadedb:latest
```

Connection is configured via env vars: `ARCADEDB_URL` (default
`http://localhost:2480`), `ARCADEDB_DATABASE` (`codebase`), `ARCADEDB_USER`
(`root`), `ARCADEDB_PASSWORD`.

### Build the graph from a repo

```bash
python scripts/build_graph.py /path/to/repo            # full ingest
python scripts/build_graph.py /path/to/repo --reset    # drop + rebuild
python scripts/build_graph.py /path/to/repo --incremental  # only changed files
```

### Test

```bash
cd backend && python -m pytest tests/test_graph_db.py -q
```

Unit tests run offline against a recording fake client (no server needed). Set
`ARCADEDB_INTEGRATION=1` with a live ArcadeDB to also run the round-trip test.

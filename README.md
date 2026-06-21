# Enterprise Codebase Intelligence Platform

Open-source platform that ingests any Git repo, builds a knowledge graph + vector index of its code, and answers plain-English questions, detects architecture risks, and computes change-impact / blast radius.

See `CODEBASE_INTELLIGENCE_MASTER_PLAN.md` for the full build spec.

## Status

| Phase | Component | State |
|---|---|---|
| 1 | AST parsing engine | **Done** |
| 2 | Graph database (ArcadeDB) | Not started |
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

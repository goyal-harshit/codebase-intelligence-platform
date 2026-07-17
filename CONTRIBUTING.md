# Contributing

## Ground rules

- **₹0 budget**: no paid APIs, no paid cloud, no paid tiers. Every dependency
  must be free and open source (see PROJECT_PLAN.md §2).
- **One plan**: scope changes go into `PROJECT_PLAN.md` — do not create
  parallel plan documents.
- **Integrate, don't reinvent**: no custom auth, vector DB, LLM, parser, or
  ORM (see the "Not building" list in the plan).

## Dev setup

```
run_local.bat        # Windows: venv + npm install + native backend/frontend
# or
docker compose up -d --build
```

Backend tests must pass before merge (CI enforces both):

```
cd backend && python -m pytest tests -q
cd frontend && npm run build
```

## Conventions

- New services join `docker-compose.yml` with a healthcheck.
- New endpoints are versioned under `/api/v1` and covered by tests in
  `backend/tests/`.
- Design decisions get an ADR in `docs/adr/`.
- After code changes, run `graphify update .` to keep the knowledge graph
  current.
- Releases are annotated tags (`vX.Y.Z`) with a matching `CHANGELOG.md` entry.

## Project board

Work is tracked on the repository's GitHub Projects board (a free GitHub
feature). To set it up on a fork: repo → Projects → "New project" → Board,
with columns `Backlog / In progress / Done`, then add issues created from the
templates in `.github/ISSUE_TEMPLATE/`.

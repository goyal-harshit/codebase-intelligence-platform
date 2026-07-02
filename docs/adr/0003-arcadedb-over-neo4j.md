# ADR 0003: ArcadeDB over Neo4j

## Status

Accepted (v1.0, shipped). `PROJECT_PLAN.md` §3 marks this as a deliberate,
do-not-churn substitution.

## Context

The code knowledge graph (files, functions, classes, imports/calls edges) needs a graph
database with a Cypher-like query language, because the retrieval layer generates Cypher
from natural-language questions (`backend/retrieval/cypher_generator.py`). Neo4j
Community Edition is free but GPLv3, single-database, and its most useful operational
features (RBAC, hot backups) are Enterprise-only. ArcadeDB Community is Apache-2.0,
lightweight, multi-model, and speaks OpenCypher plus SQL over a plain REST API.

## Decision

Use ArcadeDB Community (`arcadedb` service in `docker-compose.yml`, ports 2480/2424).
`backend/graph_db/client.py` is a thin `requests`-based HTTP client: idempotent reads go
through `/api/v1/query`, writes through `/api/v1/command`, default language Cypher
(schema DDL like `CREATE VERTEX TYPE` is sent as SQL). Schema and graph construction
live in `backend/graph_db/schema.py` and `builder.py`; NetworkX handles in-process graph
analysis. Config via `ARCADEDB_URL` / `ARCADEDB_PASSWORD` (root password is set through
the container env).

## Consequences

- Free, permissively licensed, one small container; no driver dependency — plain HTTP.
- LLM-generated Cypher works largely as it would against Neo4j, keeping the structural
  retrieval path portable.
- Trade-off: smaller community and ecosystem than Neo4j; fewer tutorials, no APOC.
- Trade-off: ArcadeDB's Cypher dialect has gaps vs Neo4j; the retriever mitigates this
  by falling back to semantic (vector) search whenever a Cypher query fails or returns
  nothing (`backend/retrieval/retriever.py`).

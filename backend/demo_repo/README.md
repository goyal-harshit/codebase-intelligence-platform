# PyShelf — demo repository

A tiny, self-contained library-management app bundled with the Codebase
Intelligence Platform. On a fresh deployment (no repos ingested yet) it is
ingested automatically so every page — dashboard, graph, risks, impact,
security, refactor, Ask — has real data the moment you sign in.

It is deliberately imperfect: `catalog.py` hosts a god class, `loans.py` a
long method, `notifications.py` some dead code, and `utils.py` is called from
everywhere (shotgun surgery) — so the analysis pages have findings to show.

Disable the auto-ingest by setting `SEED_DEMO_REPO=false`.

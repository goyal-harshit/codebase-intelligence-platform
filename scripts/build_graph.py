#!/usr/bin/env python3
"""Phase 2 CLI: parse a repo and ingest it into ArcadeDB.

Usage:
    python scripts/build_graph.py <repo_path> [--incremental] [--reset]

Connection is read from env vars (ARCADEDB_URL, ARCADEDB_DATABASE,
ARCADEDB_USER, ARCADEDB_PASSWORD); see backend/graph_db/client.py for defaults.
"""
import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from ast_parser import parse_repository  # noqa: E402
from graph_db import (  # noqa: E402
    ArcadeDBClient,
    FileHashStore,
    GraphBuilder,
    IncrementalUpdater,
    apply_schema,
)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("repo_path")
    ap.add_argument("--incremental", action="store_true",
                    help="only re-index files whose content changed since last run")
    ap.add_argument("--reset", action="store_true",
                    help="drop and recreate the database before ingesting")
    ap.add_argument("--hash-store", default="data/file_hashes.db")
    args = ap.parse_args()

    client = ArcadeDBClient()
    if not client.is_alive():
        sys.exit(f"ArcadeDB not reachable at {client.base_url}. "
                 f"Start it (see master plan §5.1) and retry.")

    if args.reset and client.database_exists():
        client.drop_database()
    client.create_database()
    apply_schema(client)

    t = time.time()
    if args.incremental:
        store = FileHashStore(args.hash_store)
        result = IncrementalUpdater(client, store).update(args.repo_path)
        store.close()
        dt = time.time() - t
        print(f"Incremental update in {dt:.2f}s")
        print(f"  changed: {len(result['changed'])} file(s)")
        print(f"  deleted: {len(result['deleted'])} file(s)")
    else:
        entities, relationships = parse_repository(args.repo_path)
        stats = GraphBuilder(client).build(entities, relationships)
        dt = time.time() - t
        print(f"Ingested {args.repo_path} in {dt:.2f}s")
        print(f"  entities: {stats['entities']}  files: {stats['files']}  edges: {stats['edges']}")


if __name__ == "__main__":
    main()

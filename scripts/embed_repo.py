#!/usr/bin/env python3
"""Phase 3 CLI: parse a repo, embed every entity, store in ChromaDB.

Usage:
    python scripts/embed_repo.py <repo_path> [--collection NAME]

Requires a running Chroma (see master plan §6.1) and downloads the
BAAI/bge-small-en-v1.5 model on first run. Connection via CHROMA_HOST/CHROMA_PORT.
"""
import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from ast_parser import parse_repository  # noqa: E402
from vector_db import VectorStoreBuilder, COLLECTION_NAME  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("repo_path")
    ap.add_argument("--collection", default=COLLECTION_NAME)
    ap.add_argument("--query", help="run a semantic search after embedding")
    args = ap.parse_args()

    entities, _ = parse_repository(args.repo_path)
    builder = VectorStoreBuilder(collection_name=args.collection)

    t = time.time()
    stored = builder.embed_and_store(entities)
    print(f"Embedded + stored {stored} entities in {time.time() - t:.2f}s")

    if args.query:
        results = builder.search(args.query, top_k=5)
        names = results.get("metadatas", [[]])[0]
        print(f"\nTop matches for {args.query!r}:")
        for m in names:
            print(f"  {m.get('file_path')}::{m.get('name')} ({m.get('entity_type')})")


if __name__ == "__main__":
    main()

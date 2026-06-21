#!/usr/bin/env python3
"""CLI demo for the Phase 1 AST parser.

Usage: python scripts/parse_repo.py <repo_path> [--json out.json]
"""
import argparse
import json
import sys
import time
from collections import Counter
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from ast_parser import parse_repository  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("repo_path")
    ap.add_argument("--json", help="write entities+relationships to this file")
    args = ap.parse_args()

    t = time.time()
    entities, relationships = parse_repository(args.repo_path)
    dt = time.time() - t

    by_type = Counter(e.type for e in entities)
    by_lang = Counter(e.language for e in entities)
    rel_types = Counter(r.type for r in relationships)

    print(f"Parsed {args.repo_path} in {dt:.2f}s")
    print(f"Entities: {len(entities)}  -> {dict(by_type)}")
    print(f"Languages: {dict(by_lang)}")
    print(f"Relationships: {len(relationships)} -> {dict(rel_types)}")

    if args.json:
        payload = {
            "entities": [asdict(e) for e in entities],
            "relationships": [asdict(r) for r in relationships],
        }
        Path(args.json).write_text(json.dumps(payload, indent=2))
        print(f"Wrote {args.json}")


if __name__ == "__main__":
    main()

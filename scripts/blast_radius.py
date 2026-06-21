#!/usr/bin/env python3
"""Phase 5 CLI: compute the blast radius of changing a file.

Usage:
    python scripts/blast_radius.py <file_path> [--depth 5]

Reads the graph built by scripts/build_graph.py (ARCADEDB_* env vars).
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from graph_db import ArcadeDBClient  # noqa: E402
from impact import ImpactAnalyzer  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("file_path")
    ap.add_argument("--depth", type=int, default=5)
    args = ap.parse_args()

    client = ArcadeDBClient()
    if not client.is_alive():
        sys.exit(f"ArcadeDB not reachable at {client.base_url}.")

    result = ImpactAnalyzer(client).analyze_file_impact(args.file_path, args.depth)
    print(f"Blast radius for {result['target']}  (risk: {result['risk_level']})")
    print(f"  directly affected:     {result['directly_affected_count']}")
    print(f"  transitively affected: {result['transitively_affected_count']}")
    for r in result["directly_affected"][:20]:
        print(f"    [direct] {r['file']}::{r['name']}")
    for r in result["transitively_affected"][:20]:
        print(f"    [+{r['hops']}] {r['file']}::{r['name']}")


if __name__ == "__main__":
    main()

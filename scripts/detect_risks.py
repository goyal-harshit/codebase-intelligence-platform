#!/usr/bin/env python3
"""Phase 4 CLI: run risk detection against the graph and optionally persist it.

Usage:
    python scripts/detect_risks.py [--persist] [--severity high]

Reads the graph built by scripts/build_graph.py. Connection via the
ARCADEDB_* env vars (see backend/graph_db/client.py).
"""
import argparse
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from graph_db import ArcadeDBClient  # noqa: E402
from risk_detection import RiskDetector, SEVERITY_ORDER, persist_risks  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--persist", action="store_true",
                    help="write detected risks back to the graph as SecurityIssue nodes")
    ap.add_argument("--severity", choices=list(SEVERITY_ORDER),
                    help="only show risks at this severity")
    args = ap.parse_args()

    client = ArcadeDBClient()
    if not client.is_alive():
        sys.exit(f"ArcadeDB not reachable at {client.base_url}.")

    risks = RiskDetector(client).run_all_checks()
    if args.severity:
        risks = [r for r in risks if r["severity"] == args.severity]

    by_sev = Counter(r["severity"] for r in risks)
    by_type = Counter(r["type"] for r in risks)
    print(f"Detected {len(risks)} risk(s): {dict(by_sev)}")
    print(f"By type: {dict(by_type)}")
    for r in risks[:50]:
        loc = f" [{r['file']}]" if r.get("file") else ""
        print(f"  [{r['severity']:>8}] {r['type']}: {r['target']}{loc} — {r['details']}")

    if args.persist:
        n = persist_risks(client, risks)
        print(f"Persisted {n} SecurityIssue node(s).")


if __name__ == "__main__":
    main()

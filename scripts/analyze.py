#!/usr/bin/env python3
"""Generate a full codebase intelligence report — no external services needed.

Usage:
    python scripts/analyze.py <repo_path> [--out DIR] [--top N] [--no-git]
Produces <name>_report.html and <name>_report.json in the output dir.
"""
import argparse
import os
import sys
import re
import subprocess
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from analysis import analyze_repository  # noqa: E402
from analysis.report import write_html, write_json  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("repo_path")
    ap.add_argument("--out", default=".", help="output directory")
    ap.add_argument("--top", type=int, default=20, help="rows per ranked list")
    ap.add_argument("--no-git", action="store_true")
    ap.add_argument("--name", help="basename for output files")
    args = ap.parse_args()

    repo = args.repo_path
    _clone = None
    if re.match(r'^https?://', repo):
        _clone = tempfile.mkdtemp(prefix='cbi_')
        print('Cloning', repo, '...')
        r = subprocess.run(['git','clone','--depth','1',repo,_clone],capture_output=True,text=True)
        if r.returncode != 0:
            print('git clone failed:', r.stderr[-500:]); raise SystemExit(1)
        repo = _clone
        if not args.name:
            args.name = args.repo_path.rstrip('/').split('/')[-1].replace('.git','')
    t = time.time()
    analysis = analyze_repository(repo, top_n=args.top,
                                  with_git=not args.no_git)
    dt = time.time() - t

    os.makedirs(args.out, exist_ok=True)
    name = args.name or os.path.basename(os.path.abspath(args.repo_path).rstrip("/\\")) or "repo"
    html_path = os.path.join(args.out, f"{name}_report.html")
    json_path = os.path.join(args.out, f"{name}_report.json")
    write_html(analysis, html_path)
    write_json(analysis, json_path)

    hs = analysis.health_score
    print(f"Analyzed {args.repo_path} in {dt:.2f}s")
    print(f"Health: {hs.get('overall')}/100 (grade {hs.get('grade')})")
    print(f"  {analysis.overview}")
    print(f"  risks: {analysis.risks.get('summary')}")
    print(f"Wrote {html_path}")
    print(f"Wrote {json_path}")


if __name__ == "__main__":
    main()

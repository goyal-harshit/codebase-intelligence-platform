"""Git history insights: churn, ownership, bus factor, contributor activity.

Uses plain `git` subprocess calls (no GitPython dependency) so it works
anywhere git is installed. Returns {"available": False} when the path is not a
git repo.
"""
from __future__ import annotations

import os
import subprocess
from collections import Counter, defaultdict

from ast_parser.repo_walker import walk_repository


def _git(repo_path: str, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", repo_path, *args],
        capture_output=True, text=True, check=True,
    ).stdout


def _is_git_repo(repo_path: str) -> bool:
    try:
        out = _git(repo_path, "rev-parse", "--is-inside-work-tree").strip()
        return out == "true"
    except Exception:
        return False


def collect_git_insights(repo_path: str, top_n: int = 20) -> dict:
    if not _is_git_repo(repo_path):
        return {"available": False, "reason": "not a git repository"}

    source_files = {
        os.path.relpath(p, repo_path) for p in walk_repository(repo_path)
    }

    # One pass over history: commits, authors, per-file churn & authorship.
    log = _git(repo_path, "log", "--no-merges", "--pretty=format:%H|%an|%ad",
               "--date=short", "--name-only")

    commits = 0
    authors = Counter()
    dates = []
    file_commits = Counter()
    file_authors = defaultdict(Counter)
    cur_author = None

    for line in log.splitlines():
        if "|" in line and line.count("|") >= 2:
            parts = line.split("|")
            cur_author = parts[1]
            commits += 1
            authors[cur_author] += 1
            dates.append(parts[2])
        elif line.strip():
            rel = line.strip()
            if rel in source_files:
                file_commits[rel] += 1
                if cur_author:
                    file_authors[rel][cur_author] += 1

    # Bus factor per file: min #authors covering >50% of that file's commits.
    knowledge_risk = []
    for f, auth_counter in file_authors.items():
        total = sum(auth_counter.values())
        if total == 0:
            continue
        ordered = auth_counter.most_common()
        cum = 0
        bus = 0
        for _, c in ordered:
            cum += c
            bus += 1
            if cum > total / 2:
                break
        top_author, top_c = ordered[0]
        if bus == 1:
            knowledge_risk.append({
                "file": f, "bus_factor": bus, "sole_owner": top_author,
                "ownership_pct": round(100 * top_c / total, 1), "commits": total,
            })
    knowledge_risk.sort(key=lambda x: x["commits"], reverse=True)

    file_churn = [{"file": f, "commits": c} for f, c in file_commits.most_common(top_n)]

    # Overall bus factor (project-level).
    total_commits = sum(authors.values()) or 1
    cum = 0
    project_bus = 0
    for _, c in authors.most_common():
        cum += c
        project_bus += 1
        if cum > total_commits / 2:
            break

    return {
        "available": True,
        "total_commits": commits,
        "contributors": len(authors),
        "first_commit": min(dates) if dates else None,
        "last_commit": max(dates) if dates else None,
        "project_bus_factor": project_bus,
        "top_contributors": [{"author": a, "commits": c}
                             for a, c in authors.most_common(top_n)],
        "file_churn": file_churn,
        "knowledge_risk_files": knowledge_risk[:top_n],
    }

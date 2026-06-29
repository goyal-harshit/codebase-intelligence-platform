"""Hotspot analysis: combine git churn with graph-derived complexity."""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .git_insights import collect_git_insights

if TYPE_CHECKING:
    from graph_db import ArcadeDBClient


@dataclass(frozen=True)
class FileComplexity:
    file: str
    total_complexity: int
    max_complexity: int
    functions: int
    lines_of_code: int


def collect_file_complexity(graph: "ArcadeDBClient") -> dict[str, FileComplexity]:
    """Aggregate complexity per file from Function vertices.

    Aggregation is done in Python to stay compatible with the project's test
    fakes and ArcadeDB's Cypher dialect quirks.
    """
    rows = graph.query(
        "MATCH (f:Function) RETURN f.file_path AS file, "
        "f.cyclomatic_complexity AS complexity, f.lines_of_code AS loc"
    )
    buckets: dict[str, dict[str, int]] = {}
    for row in rows:
        file_path = row.get("file")
        if not file_path:
            continue
        complexity = int(row.get("complexity") or 1)
        loc = int(row.get("loc") or 0)
        bucket = buckets.setdefault(
            file_path,
            {"total_complexity": 0, "max_complexity": 0, "functions": 0, "lines_of_code": 0},
        )
        bucket["total_complexity"] += complexity
        bucket["max_complexity"] = max(bucket["max_complexity"], complexity)
        bucket["functions"] += 1
        bucket["lines_of_code"] += loc

    return {
        path: FileComplexity(file=path, **values)
        for path, values in buckets.items()
    }


def _lookup_keys(file_path: str, repo_path: str) -> set[str]:
    norm = os.path.normpath(file_path)
    keys = {norm, norm.replace("\\", "/")}
    try:
        rel = os.path.relpath(norm, repo_path)
        keys.add(os.path.normpath(rel))
        keys.add(rel.replace("\\", "/"))
    except ValueError:
        pass
    return keys


def build_hotspots(graph: "ArcadeDBClient", repo_path: str, limit: int = 25) -> dict:
    insights = collect_git_insights(repo_path, top_n=max(limit * 4, 100))
    if not insights.get("available"):
        return {
            "available": False,
            "reason": insights.get("reason", "git history unavailable"),
            "repo_path": repo_path,
            "hotspots": [],
        }

    churn_by_file = {
        os.path.normpath(item["file"]): int(item["commits"])
        for item in insights.get("file_churn", [])
    }
    churn_by_file.update({
        item["file"].replace("\\", "/"): int(item["commits"])
        for item in insights.get("file_churn", [])
    })

    hotspots = []
    for file_path, complexity in collect_file_complexity(graph).items():
        churn = 0
        display_file = file_path
        for key in _lookup_keys(file_path, repo_path):
            if key in churn_by_file:
                churn = churn_by_file[key]
                display_file = key.replace("\\", "/")
                break
        if churn == 0:
            continue
        score = churn * complexity.total_complexity
        hotspots.append({
            "file": display_file,
            "churn": churn,
            "total_complexity": complexity.total_complexity,
            "max_complexity": complexity.max_complexity,
            "functions": complexity.functions,
            "lines_of_code": complexity.lines_of_code,
            "score": score,
        })

    hotspots.sort(key=lambda item: item["score"], reverse=True)
    return {
        "available": True,
        "repo_path": repo_path,
        "hotspots": hotspots[:limit],
        "total": len(hotspots),
    }

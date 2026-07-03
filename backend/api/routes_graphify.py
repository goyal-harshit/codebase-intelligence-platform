"""Routes for serving graphify-out graph data and reports."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Response, Query

router = APIRouter()

# graphify-out lives at the project root (parent of backend/)
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_GRAPHIFY_DIR = _PROJECT_ROOT / "graphify-out"

# ---------------------------------------------------------------------------
# Mtime-aware cache: re-reads only when the file on disk has changed.
# ---------------------------------------------------------------------------
_cache: dict[str, tuple[float, Any]] = {}


def _read_json_cached(path: Path) -> Any:
    """Return parsed JSON from *path*, using a cache keyed on file mtime."""
    try:
        mtime = os.path.getmtime(path)
    except OSError:
        raise HTTPException(404, f"{path.name} not found")

    key = str(path)
    cached = _cache.get(key)
    if cached and cached[0] == mtime:
        return cached[1]

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        raise HTTPException(500, f"Failed to read {path.name}: {exc}")

    _cache[key] = (mtime, data)
    return data


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/graphify/stats")
def graphify_stats():
    """Summary counts (nodes, edges, communities) without the full graph."""
    graph_path = _GRAPHIFY_DIR / "graph.json"
    if not graph_path.exists():
        return {"nodes": 0, "edges": 0, "communities": 0, "available": False}
    data = _read_json_cached(graph_path)
    
    # Filter for code nodes only
    nodes = [n for n in data.get("nodes", []) if n.get("file_type") == "code"]
    node_ids = {n.get("id") for n in nodes if "id" in n}
    links = [lnk for lnk in data.get("links", []) if lnk.get("source") in node_ids and lnk.get("target") in node_ids]
    
    communities = {n.get("community") for n in nodes if n.get("community") is not None}
    return {
        "nodes": len(nodes),
        "edges": len(links),
        "communities": len(communities),
        "available": True,
    }


@router.get("/graphify/graph")
def graphify_graph(download: bool = Query(default=False)):
    """Full graph data transformed for the frontend visualisation layer."""
    data = _read_json_cached(_GRAPHIFY_DIR / "graph.json")
    
    # Filter for code nodes only
    nodes = [
        {
            "id": n["id"],
            "name": n.get("label", n["id"]),
            "type": n.get("file_type", "unknown"),
            "community": n.get("community"),
            "file": n.get("source_file"),
        }
        for n in data.get("nodes", [])
        if n.get("file_type") == "code"
    ]
    
    node_ids = {n["id"] for n in nodes}
    links = [
        {"source": lnk["source"], "target": lnk["target"]}
        for lnk in data.get("links", [])
        if lnk.get("source") in node_ids and lnk.get("target") in node_ids
    ]
    
    result = {"nodes": nodes, "links": links}
    if download:
        return Response(
            content=json.dumps(result),
            media_type="application/json",
            headers={"Content-Disposition": 'attachment; filename="graph.json"'}
        )
    return result


@router.get("/graphify/report")
def graphify_report(download: bool = Query(default=False)):
    """Return GRAPH_REPORT.md as plain text."""
    report_path = _GRAPHIFY_DIR / "GRAPH_REPORT.md"
    if not report_path.exists():
        raise HTTPException(404, "GRAPH_REPORT.md not found")
    try:
        content = report_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise HTTPException(500, f"Failed to read report: {exc}")
    
    headers = {}
    if download:
        headers["Content-Disposition"] = 'attachment; filename="codebase_architecture_report.md"'
        
    return Response(content=content, media_type="text/plain; charset=utf-8", headers=headers)

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from .deps import get_graph_client
from .result_cache import cached

router = APIRouter()


def cached_stats(graph) -> dict:
    """Graph counts, cached until the next ingest. Shared by the route and the
    post-ingest cache warmer so both use the same key."""
    def compute() -> dict:
        def scalar(cypher: str) -> int:
            rows = graph.query(cypher)
            return rows[0]["n"] if rows else 0

        return {
            "total_files": scalar("MATCH (f:File) RETURN count(f) AS n"),
            "total_functions": scalar("MATCH (f:Function) RETURN count(f) AS n"),
            "total_classes": scalar("MATCH (c:Class) RETURN count(c) AS n"),
            "total_calls": scalar("MATCH ()-[r:CALLS]->() RETURN count(r) AS n"),
        }

    # Counts change only on ingest; cache to avoid 4 graph round-trips per load.
    return cached("stats", compute)


@router.get("/stats")
def stats(graph=Depends(get_graph_client)):
    try:
        return cached_stats(graph)
    except Exception as e:
        raise HTTPException(503, f"graph backend unavailable: {e}")

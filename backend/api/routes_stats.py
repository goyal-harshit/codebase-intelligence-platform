from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from .deps import get_graph_client

router = APIRouter()


@router.get("/stats")
def stats(graph=Depends(get_graph_client)):
    try:
        def scalar(cypher: str) -> int:
            rows = graph.query(cypher)
            return rows[0]["n"] if rows else 0

        return {
            "total_files": scalar("MATCH (f:File) RETURN count(f) AS n"),
            "total_functions": scalar("MATCH (f:Function) RETURN count(f) AS n"),
            "total_classes": scalar("MATCH (c:Class) RETURN count(c) AS n"),
            "total_calls": scalar("MATCH ()-[r:CALLS]->() RETURN count(r) AS n"),
        }
    except Exception as e:
        raise HTTPException(503, f"graph backend unavailable: {e}")

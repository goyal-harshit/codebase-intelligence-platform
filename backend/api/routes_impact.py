from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from impact import ImpactAnalyzer

from .deps import get_graph_client

router = APIRouter()


@router.get("/impact/{file_path:path}")
def impact(file_path: str, depth: int = 5, graph=Depends(get_graph_client)):
    try:
        return ImpactAnalyzer(graph).analyze_file_impact(file_path, max_depth=depth)
    except Exception as e:
        raise HTTPException(503, f"graph backend unavailable: {e}")

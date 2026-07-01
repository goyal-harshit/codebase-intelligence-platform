from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from impact import ImpactAnalyzer

from .deps import get_graph_client
from .validators import ValidationError, validate_relative_path

router = APIRouter()


@router.get("/impact/{file_path:path}")
def impact(file_path: str, depth: int = 5, graph=Depends(get_graph_client)):
    try:
        file_path = validate_relative_path(file_path)
    except ValidationError as e:
        raise HTTPException(400, str(e))
    analyzer = ImpactAnalyzer(graph)
    try:
        resolved, suggestions = analyzer.resolve_file_path(file_path)
    except Exception as e:
        raise HTTPException(503, f"graph backend unavailable: {e}")
    if resolved is None:
        detail = f"file not found in graph: {file_path}"
        if suggestions:
            detail += "; did you mean: " + ", ".join(suggestions)
        raise HTTPException(404, detail)
    try:
        return analyzer.analyze_file_impact(resolved, max_depth=depth)
    except Exception as e:
        raise HTTPException(503, f"graph backend unavailable: {e}")

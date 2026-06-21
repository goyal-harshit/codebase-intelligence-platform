from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from .deps import get_query_engine

router = APIRouter()


@router.get("/query")
def query(
    q: str = Query(..., min_length=1, description="natural-language question"),
    top_k: int = 10,
    engine=Depends(get_query_engine),
):
    try:
        return engine.answer(q, top_k=top_k)
    except Exception as e:
        raise HTTPException(503, f"query backend unavailable: {e}")

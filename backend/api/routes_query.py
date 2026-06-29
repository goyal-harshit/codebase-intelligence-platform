from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from observability import QUERY_LATENCY

from .audit import record_audit
from .deps import get_query_engine
from .ratelimit import QUERY_LIMIT, limiter
from .security import Principal, get_principal

router = APIRouter()


@router.get("/query")
@limiter.limit(QUERY_LIMIT)
def query(
    request: Request,
    q: str = Query(..., min_length=1, description="natural-language question"),
    top_k: int = 10,
    engine=Depends(get_query_engine),
    principal: Principal = Depends(get_principal),
):
    record_audit("query", user_id=principal.user_id, target=q[:512], request=request)
    try:
        with QUERY_LATENCY.time():
            return engine.answer(q, top_k=top_k)
    except Exception as e:
        raise HTTPException(503, f"query backend unavailable: {e}")

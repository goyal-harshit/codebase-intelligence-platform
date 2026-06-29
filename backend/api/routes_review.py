"""AI code review endpoint (Phase 4): review a unified diff with the LLM."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from . import review as _review
from .audit import record_audit
from .deps import get_llm
from .security import Principal, get_principal

router = APIRouter()


class ReviewRequest(BaseModel):
    diff: str = Field(..., min_length=1, description="unified diff to review")


@router.post("/review")
def review_route(
    req: ReviewRequest,
    request: Request,
    llm=Depends(get_llm),
    principal: Principal = Depends(get_principal),
):
    try:
        review = _review.review_diff(llm, req.diff)
    except Exception as e:
        raise HTTPException(503, f"LLM backend unavailable: {e}")
    record_audit("review", user_id=principal.user_id, request=request)
    return {"review": review}

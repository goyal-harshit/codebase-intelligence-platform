from __future__ import annotations

import os
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import desc, select

from analysis.hotspots import build_hotspots
from db import Job, get_sessionmaker

from .audit import record_audit
from .deps import get_graph_client
from .result_cache import cached
from .security import Principal, get_principal

router = APIRouter()


def _latest_repo_path(user_id: str | None = None) -> str | None:
    terminal = ("complete", "complete_with_warnings")
    with get_sessionmaker()() as session:
        stmt = (
            select(Job.repo_path)
            .where(Job.repo_path.is_not(None), Job.status.in_(terminal))
            .order_by(desc(Job.updated_at))
            .limit(1)
        )
        if user_id:
            stmt = stmt.where(Job.user_id == user_id)
        return session.execute(stmt).scalar_one_or_none()


def cached_hotspots(graph, path: str, limit: int) -> dict:
    """Hotspots for a repo, cached per (repo, limit) until the next ingest.
    build_hotspots walks full git history + a graph query, so it's shared by the
    route and the post-ingest warmer."""
    return cached(f"hotspots:{path}:{limit}", lambda: build_hotspots(graph, path, limit=limit))


@router.get("/hotspots")
def hotspots(
    request: Request,
    repo_path: Optional[str] = Query(default=None),
    limit: int = Query(default=25, ge=1, le=100),
    graph=Depends(get_graph_client),
    principal: Principal = Depends(get_principal),
):
    path = repo_path or _latest_repo_path(principal.user_id)
    if not path:
        # Service-key/anonymous mode can still use the latest successful ingest.
        path = _latest_repo_path()
    if not path:
        return {
            "available": False,
            "reason": "no completed local ingest job with a repo_path; pass repo_path explicitly",
            "hotspots": [],
        }
    if not os.path.isdir(path):
        raise HTTPException(400, f"repo_path is not a directory: {path}")

    record_audit(
        "hotspots",
        user_id=principal.user_id,
        target=path,
        detail={"limit": limit},
        request=request,
    )
    try:
        return cached_hotspots(graph, path, limit)
    except Exception as e:
        raise HTTPException(503, f"hotspot analysis unavailable: {e}")

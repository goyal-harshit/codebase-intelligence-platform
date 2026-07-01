"""Collaboration (Phase 5): activity feed based on the audit log.
"""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

import db as _db
from auth import current_active_user
from db import AuditLog

router = APIRouter()


class ActivityOut(BaseModel):
    id: int
    user_id: Optional[str] = None
    action: str
    target: Optional[str] = None
    detail: Optional[dict] = None
    created_at: datetime


@router.get("/activity", response_model=list[ActivityOut])
def get_activity_feed(
    limit: int = Query(50, ge=1, le=200),
    user=Depends(current_active_user)
):
    """Get the most recent activity feed events from the audit log."""
    with _db.get_sessionmaker()() as s:
        # We fetch the latest audit logs. This could be filtered by repo access,
        # but for Phase 5 we start with a global stream for the team instance.
        activities = (
            s.query(AuditLog)
            .order_by(AuditLog.created_at.desc())
            .limit(limit)
            .all()
        )
        return activities

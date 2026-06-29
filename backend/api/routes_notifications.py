"""In-app notification REST API (Phase 3). JWT-protected; users see only their
own notifications. Real-time delivery is over the WebSocket in main.py; this is
the durable list + read-state management behind it."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth import current_active_user
from notifications import list_for_user, mark_all_read, mark_read

router = APIRouter()


class NotificationInfo(BaseModel):
    id: str
    type: str
    level: str
    title: str
    body: Optional[str] = None
    detail: Optional[dict] = None
    read: bool
    created_at: datetime


@router.get("/notifications", response_model=list[NotificationInfo])
def list_notifications(unread_only: bool = False, user=Depends(current_active_user)):
    return list_for_user(user.id, unread_only=unread_only)


@router.post("/notifications/read-all")
def read_all(user=Depends(current_active_user)):
    return {"marked_read": mark_all_read(user.id)}


@router.post("/notifications/{notification_id}/read")
def read_one(notification_id: str, user=Depends(current_active_user)):
    if not mark_read(user.id, notification_id):
        raise HTTPException(404, "unknown or already-read notification")
    return {"status": "ok"}

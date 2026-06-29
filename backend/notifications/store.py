"""Durable notification storage (Phase 3).

Notifications live in the ``notifications`` table so they survive restarts and are
visible across processes (the Celery worker writes them; the API reads/streams
them) without any external pub/sub — matching the plan's "no extra infra" stance.
"""
from __future__ import annotations

from typing import Optional

import db as _db
from db import Notification


def create_notification(
    user_id: Optional[str],
    title: str,
    *,
    body: Optional[str] = None,
    level: str = "info",
    type: str = "job",
    detail: Optional[dict] = None,
) -> dict:
    with _db.get_sessionmaker()() as s:
        n = Notification(
            user_id=user_id, title=title, body=body, level=level, type=type, detail=detail
        )
        s.add(n)
        s.commit()
        return _to_dict(n)


def list_for_user(user_id: str, unread_only: bool = False, limit: int = 50) -> list[dict]:
    with _db.get_sessionmaker()() as s:
        q = s.query(Notification).filter(Notification.user_id == user_id)
        if unread_only:
            q = q.filter(Notification.read.is_(False))
        rows = q.order_by(Notification.created_at.desc()).limit(limit).all()
        return [_to_dict(n) for n in rows]


def mark_read(user_id: str, notification_id: str) -> bool:
    with _db.get_sessionmaker()() as s:
        n = s.get(Notification, notification_id)
        if n is None or n.user_id != user_id:
            return False
        if n.read:
            return False
        n.read = True
        s.commit()
        return True


def mark_all_read(user_id: str) -> int:
    with _db.get_sessionmaker()() as s:
        count = (
            s.query(Notification)
            .filter(Notification.user_id == user_id, Notification.read.is_(False))
            .update({Notification.read: True})
        )
        s.commit()
        return count


def _to_dict(n: Notification) -> dict:
    return {
        "id": n.id,
        "type": n.type,
        "level": n.level,
        "title": n.title,
        "body": n.body,
        "detail": n.detail,
        "read": n.read,
        "created_at": n.created_at,
    }

"""Notification dispatch (Phase 3): fan one event out to the durable store and
to email. Called from the ingestion task on terminal job states.

Best-effort throughout — a failure to notify must never fail the job.
"""
from __future__ import annotations

import logging
from typing import Optional

import db as _db
from db import User

from .email import get_email_sender
from .store import create_notification

logger = logging.getLogger("codebase_intelligence.notify")

# Map job status -> (notification level, human title).
_STATUS = {
    "complete": ("success", "Ingestion complete"),
    "complete_with_warnings": ("warning", "Ingestion completed with warnings"),
    "failed": ("error", "Ingestion failed"),
}


def _user_email(user_id: str) -> Optional[str]:
    with _db.get_sessionmaker()() as s:
        user = s.get(User, user_id)
        return user.email if user else None


def notify_job_completion(
    job_id: str,
    user_id: Optional[str],
    status: str,
    *,
    result: Optional[dict] = None,
    error: Optional[str] = None,
) -> None:
    level, title = _STATUS.get(status, ("info", f"Ingestion {status}"))
    if status == "failed":
        body = error or "The ingestion job failed."
    elif result:
        body = (f"{result.get('files', '?')} files, {result.get('entities', '?')} entities, "
                f"{result.get('risks', '?')} risks indexed.")
    else:
        body = "Ingestion finished."

    detail = {"job_id": job_id, "status": status}

    try:
        create_notification(user_id, title, body=body, level=level, type="job", detail=detail)
    except Exception:  # pragma: no cover - defensive
        logger.warning("failed to persist job notification for %s", job_id, exc_info=True)

    # Email only makes sense for an attributed user account.
    if user_id:
        email = _user_email(user_id)
        if email:
            get_email_sender().send(email, f"[Codebase Intelligence] {title}",
                                    f"{body}\n\nJob: {job_id}")

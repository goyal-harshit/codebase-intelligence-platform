"""Audit logging: persist security-relevant actions to the ``audit_log`` table.

Phase 2 (FULL_STACK_GAP_PLAN.md §5) requires the audit log to be populated on
ingest/query/risk actions. Auditing is best-effort: a failure to record an event
must never break the request that triggered it, so every write is guarded.
"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import Request

import db as _db
from db import AuditLog

logger = logging.getLogger("codebase_intelligence.audit")


def client_ip(request: Optional[Request]) -> Optional[str]:
    """Best-effort client IP, honouring a single X-Forwarded-For hop (the value
    a reverse proxy in front of the stack sets — see Phase 7)."""
    if request is None:
        return None
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else None


def record_audit(
    action: str,
    *,
    user_id: Optional[str] = None,
    target: Optional[str] = None,
    detail: Optional[dict] = None,
    request: Optional[Request] = None,
) -> None:
    """Append one audit event. Swallows all errors (logs a warning) so auditing
    can never take down the data path."""
    try:
        with _db.get_sessionmaker()() as s:
            s.add(
                AuditLog(
                    action=action,
                    user_id=user_id,
                    target=target,
                    detail=detail,
                    ip=client_ip(request),
                )
            )
            s.commit()
    except Exception:  # pragma: no cover - defensive
        logger.warning("failed to record audit event '%s'", action, exc_info=True)

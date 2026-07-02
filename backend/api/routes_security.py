"""Security / SAST findings endpoint (roadmap Phase 11).

Scans the most recent completed ingest's ``repo_path`` on demand (mirrors the
``/hotspots`` pattern — the scan needs raw source on disk, which the graph does
not hold). Fast enough to run per-request for typical repos.
"""
from __future__ import annotations

import os
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request
from sqlalchemy import desc, select

from db import Job, get_sessionmaker
from security_scan import scan_repository

from .audit import record_audit

router = APIRouter()

_TERMINAL = ("complete", "complete_with_warnings")


def _latest_repo_path() -> Optional[str]:
    with get_sessionmaker()() as session:
        return session.execute(
            select(Job.repo_path)
            .where(Job.repo_path.is_not(None), Job.status.in_(_TERMINAL))
            .order_by(desc(Job.updated_at))
            .limit(1)
        ).scalar_one_or_none()


@router.get("/security")
def security(
    request: Request,
    repo_path: Optional[str] = Query(default=None),
    severity: Optional[str] = Query(default=None),
):
    path = repo_path or _latest_repo_path()
    if not path:
        return {"available": False,
                "reason": "no completed ingest with a repo_path; pass repo_path explicitly",
                "findings": [], "total": 0, "by_severity": {}}
    if not os.path.isdir(path):
        raise HTTPException(400, f"repo_path is not a directory: {path}")

    record_audit("security_scan", target=path, detail={"severity": severity}, request=request)
    try:
        # external=True layers Bandit + Ruff (S rules) over the builtin scanner.
        result = scan_repository(path, external=True)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(503, f"security scan failed: {e}")

    if severity:
        findings = [f for f in result["findings"] if f["severity"] == severity]
        result = {**result, "findings": findings, "total": len(findings)}
    result["available"] = True
    return result

"""Security / SAST findings endpoint (roadmap Phase 11).

Scans the most recent completed ingest's ``repo_path`` on demand (mirrors the
``/hotspots`` pattern — the scan needs raw source on disk, which the graph does
not hold). Fast enough to run per-request for typical repos.
"""
from __future__ import annotations

import os
import time
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request
from sqlalchemy import desc, select

from db import Job, get_sessionmaker
from security_scan import scan_repository

from .audit import record_audit

router = APIRouter()

_TERMINAL = ("complete", "complete_with_warnings")

# Bandit/Ruff over a real repo can take seconds-to-minutes; the dashboard and
# security page both hit this endpoint on every visit, so results are cached
# per repo path. ``?refresh=true`` forces a rescan.
_CACHE_TTL_SECONDS = 600
_scan_cache: dict[str, tuple[float, dict]] = {}


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
    refresh: bool = Query(default=False),
):
    path = repo_path or _latest_repo_path()
    if not path:
        return {"available": False,
                "reason": "no completed ingest with a repo_path; pass repo_path explicitly",
                "findings": [], "total": 0, "by_severity": {}}
    if not os.path.isdir(path):
        raise HTTPException(400, f"repo_path is not a directory: {path}")

    record_audit("security_scan", target=path, detail={"severity": severity}, request=request)
    cached = _scan_cache.get(path)
    if cached and not refresh and time.monotonic() - cached[0] < _CACHE_TTL_SECONDS:
        result = cached[1]
    else:
        try:
            # external=True layers Bandit + Ruff (S rules) over the builtin scanner.
            result = scan_repository(path, external=True)
        except Exception as e:  # noqa: BLE001
            raise HTTPException(503, f"security scan failed: {e}")
        _scan_cache[path] = (time.monotonic(), result)

    if severity:
        findings = [f for f in result["findings"] if f["severity"] == severity]
        result = {**result, "findings": findings, "total": len(findings)}
    result["available"] = True
    return result

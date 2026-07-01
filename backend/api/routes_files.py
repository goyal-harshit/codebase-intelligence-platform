"""Ingested-repo file listing (plan Phase B).

``GET /api/v1/repos/{job_id}/files`` walks the repo stored for a completed
ingest job and returns the parseable source files as repo-relative paths. This
is what backs the frontend file selector so users click an exact path (matching
what the graph stored) for Impact/Ask instead of guessing free-text.
"""
from __future__ import annotations

import os

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import desc, select

from ast_parser.repo_walker import walk_repository
from db import Job, get_sessionmaker

router = APIRouter()

_TERMINAL = ("complete", "complete_with_warnings")


def _job_repo_path(job_id: str) -> str | None:
    with get_sessionmaker()() as session:
        return session.execute(
            select(Job.repo_path).where(Job.id == job_id)
        ).scalar_one_or_none()


def _latest_repo_path() -> str | None:
    with get_sessionmaker()() as session:
        return session.execute(
            select(Job.repo_path)
            .where(Job.repo_path.is_not(None), Job.status.in_(_TERMINAL))
            .order_by(desc(Job.updated_at))
            .limit(1)
        ).scalar_one_or_none()


def _walk_files(repo_path: str, ext: str | None, limit: int) -> list[str]:
    files: list[str] = []
    for abs_path in walk_repository(repo_path):
        rel = os.path.relpath(abs_path, repo_path).replace("\\", "/")
        if ext and not rel.endswith(ext):
            continue
        files.append(rel)
        if len(files) >= limit:
            break
    files.sort()
    return files


@router.get("/repos/files")
def list_latest_repo_files(
    ext: str | None = Query(default=None, description="filter to paths ending with this extension, e.g. .py"),
    limit: int = Query(default=5000, ge=1, le=20000),
):
    """Files from the most recent completed ingest — lets the Impact/Ask file
    selector work without the caller knowing a specific job_id."""
    repo_path = _latest_repo_path()
    if not repo_path:
        raise HTTPException(404, "no completed ingest with a repo_path yet")
    if not os.path.isdir(repo_path):
        raise HTTPException(410, f"repo path no longer available on disk: {repo_path}")
    files = _walk_files(repo_path, ext, limit)
    return {"repo_path": repo_path, "count": len(files), "files": files}


@router.get("/repos/{job_id}/files")
def list_repo_files(
    job_id: str,
    ext: str | None = Query(default=None, description="filter to paths ending with this extension, e.g. .py"),
    limit: int = Query(default=5000, ge=1, le=20000),
):
    repo_path = _job_repo_path(job_id)
    if not repo_path:
        raise HTTPException(404, "unknown job_id, or job has no repo_path")
    if not os.path.isdir(repo_path):
        raise HTTPException(410, f"repo path no longer available on disk: {repo_path}")
    files = _walk_files(repo_path, ext, limit)
    return {
        "job_id": job_id,
        "repo_path": repo_path,
        "count": len(files),
        "files": files,
    }

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from .audit import record_audit
from .jobs import jobs
from .ratelimit import INGEST_LIMIT, limiter
from .security import Principal, get_principal
from .tasks import ingest_repo_task
from .validators import ValidationError, validate_repo_url

router = APIRouter()


class IngestRequest(BaseModel):
    repo_url: Optional[str] = None
    repo_path: Optional[str] = None


@router.post("/ingest")
@limiter.limit(INGEST_LIMIT)
def start_ingest(
    request: Request,
    req: IngestRequest,
    principal: Principal = Depends(get_principal),
):
    if not (req.repo_url or req.repo_path):
        raise HTTPException(400, "provide repo_url or repo_path")
    if req.repo_url:
        # Allow-list scheme + block internal/loopback targets (SSRF guard).
        try:
            req.repo_url = validate_repo_url(req.repo_url)
        except ValidationError as e:
            raise HTTPException(400, str(e))
    job_id = jobs.create(
        repo_url=req.repo_url, repo_path=req.repo_path, user_id=principal.user_id
    )
    # Durable dispatch: runs on the Celery worker (or in-process in eager mode).
    ingest_repo_task.delay(job_id, req.repo_url, req.repo_path)
    record_audit(
        "ingest",
        user_id=principal.user_id,
        target=req.repo_url or req.repo_path,
        detail={"job_id": job_id},
        request=request,
    )
    return {"job_id": job_id, "status": "queued"}


@router.get("/ingest/{job_id}")
def ingest_status(job_id: str):
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(404, "unknown job_id")
    return job

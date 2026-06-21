from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

from .jobs import jobs
from .tasks import run_ingestion

router = APIRouter()


class IngestRequest(BaseModel):
    repo_url: Optional[str] = None
    repo_path: Optional[str] = None


@router.post("/ingest")
def start_ingest(req: IngestRequest, background: BackgroundTasks):
    if not (req.repo_url or req.repo_path):
        raise HTTPException(400, "provide repo_url or repo_path")
    job_id = jobs.create()
    background.add_task(run_ingestion, jobs, job_id, req.repo_url, req.repo_path)
    return {"job_id": job_id, "status": "queued"}


@router.get("/ingest/{job_id}")
def ingest_status(job_id: str):
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(404, "unknown job_id")
    return job

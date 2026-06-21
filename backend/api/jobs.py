"""In-memory ingestion-job tracking.

A process-local job store with status transitions. Sufficient for a single-node
dev server; swap for Celery + Redis (master plan §10.5) for multi-worker
production without changing the route contract.
"""
from __future__ import annotations

import threading
import uuid
from typing import Optional


class JobManager:
    def __init__(self) -> None:
        self._jobs: dict[str, dict] = {}
        self._lock = threading.Lock()

    def create(self) -> str:
        job_id = uuid.uuid4().hex
        with self._lock:
            self._jobs[job_id] = {
                "job_id": job_id, "status": "queued", "step": None,
                "error": None, "result": None,
            }
        return job_id

    def update(self, job_id: str, **fields) -> None:
        with self._lock:
            if job_id in self._jobs:
                self._jobs[job_id].update(fields)

    def get(self, job_id: str) -> Optional[dict]:
        with self._lock:
            job = self._jobs.get(job_id)
            return dict(job) if job else None


# module-level singleton used by the ingest routes + tasks
jobs = JobManager()

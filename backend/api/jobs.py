"""Durable ingestion-job tracking, backed by the relational store.

Job state lives in the ``jobs`` table (SQLite in dev, Postgres in prod) instead
of process memory, so jobs survive a restart and are visible to both the API
process and the Celery worker (FULL_STACK_GAP_PLAN.md bug #3).
"""
from __future__ import annotations

from typing import Optional

import db as _db
from db import Job

# Columns a caller is allowed to update on a job row.
_UPDATABLE = {"status", "step", "error", "warnings", "result", "repo_url", "repo_path", "user_id"}


class JobManager:
    def _session(self):
        return _db.get_sessionmaker()()

    def create(self, repo_url: Optional[str] = None, repo_path: Optional[str] = None,
               user_id: Optional[str] = None) -> str:
        with self._session() as s:
            job = Job(status="queued", repo_url=repo_url, repo_path=repo_path,
                      user_id=user_id, warnings=[])
            s.add(job)
            s.commit()
            return job.id

    def update(self, job_id: str, **fields) -> None:
        data = {k: v for k, v in fields.items() if k in _UPDATABLE}
        if not data:
            return
        with self._session() as s:
            job = s.get(Job, job_id)
            if job is None:
                return
            for key, value in data.items():
                setattr(job, key, value)
            s.commit()

    def get(self, job_id: str) -> Optional[dict]:
        with self._session() as s:
            job = s.get(Job, job_id)
            if job is None:
                return None
            return {
                "job_id": job.id,
                "user_id": job.user_id,
                "status": job.status,
                "step": job.step,
                "error": job.error,
                "result": job.result,
                "warnings": job.warnings or [],
            }


# module-level singleton used by the ingest routes + Celery task
jobs = JobManager()

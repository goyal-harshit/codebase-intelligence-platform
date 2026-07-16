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
_UPDATABLE = {"status", "step", "error", "warnings", "result", "repo_url", "repo_path", "user_id", "progress"}


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

    def find_active(self, repo_url: Optional[str] = None,
                    repo_path: Optional[str] = None) -> Optional[str]:
        """Id of a queued/running job for the same target, if one exists.

        Lets the ingest route return the in-flight job instead of piling a
        duplicate CPU-heavy pipeline on top of it (e.g. double-clicked
        "Start analysis").
        """
        from datetime import datetime, timedelta, timezone

        from sqlalchemy import or_, select

        target = repo_url or repo_path
        if not target:
            return None
        # Ignore jobs with no recent progress: a crash can orphan a row in
        # "running" and it must not block re-ingesting that repo forever.
        stale_cutoff = datetime.now(timezone.utc) - timedelta(minutes=30)
        with self._session() as s:
            return s.execute(
                select(Job.id)
                .where(
                    Job.status.in_(("queued", "running")),
                    or_(Job.repo_url == target, Job.repo_path == target),
                    Job.updated_at >= stale_cutoff,
                )
                .order_by(Job.created_at.desc())
                .limit(1)
            ).scalar_one_or_none()

    @staticmethod
    def _to_dict(job: Job) -> dict:
        return {
            "job_id": job.id,
            "user_id": job.user_id,
            "status": job.status,
            "step": job.step,
            "progress": job.progress,
            "error": job.error,
            "result": job.result,
            "warnings": job.warnings or [],
            "repo_url": job.repo_url,
            "repo_path": job.repo_path,
            "created_at": job.created_at,
            "updated_at": job.updated_at,
        }

    def get(self, job_id: str) -> Optional[dict]:
        with self._session() as s:
            job = s.get(Job, job_id)
            if job is None:
                return None
            return self._to_dict(job)

    def list_recent(self, limit: int = 20) -> list[dict]:
        """Most recent jobs, newest first.

        Backs ``GET /api/v1/ingest`` so any page can discover an in-flight
        ingestion (global progress bar) without holding a job id.
        """
        from sqlalchemy import select

        with self._session() as s:
            rows = (
                s.execute(select(Job).order_by(Job.created_at.desc()).limit(limit))
                .scalars()
                .all()
            )
            return [self._to_dict(j) for j in rows]


# module-level singleton used by the ingest routes + Celery task
jobs = JobManager()

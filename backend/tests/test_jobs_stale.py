"""Orphaned-job reconciliation (v1.4).

A crash can leave rows in "running" forever; they must be flagged stale in
listings and swept to "failed" on startup, without touching live jobs.
"""
from datetime import datetime, timedelta, timezone

from sqlalchemy import update

import db as _db
from api.jobs import STALE_ACTIVE_MINUTES, JobManager
from db import Job

jobs = JobManager()


def _backdate(job_id: str, minutes: int) -> None:
    old = datetime.now(timezone.utc) - timedelta(minutes=minutes)
    with _db.get_sessionmaker()() as s:
        s.execute(update(Job).where(Job.id == job_id).values(updated_at=old))
        s.commit()


def test_silent_active_job_is_flagged_stale_and_swept():
    job_id = jobs.create(repo_path="/tmp/crashed-repo")
    jobs.update(job_id, status="running", step="embedding", progress=6)
    _backdate(job_id, STALE_ACTIVE_MINUTES + 5)

    listed = {j["job_id"]: j for j in jobs.list_recent(limit=50)}
    assert listed[job_id]["stale"] is True

    assert jobs.fail_stale_active() >= 1
    swept = jobs.get(job_id)
    assert swept["status"] == "failed"
    assert "interrupted" in swept["error"]


def test_fresh_active_job_is_untouched():
    job_id = jobs.create(repo_path="/tmp/live-repo")
    jobs.update(job_id, status="running", step="embedding", progress=42)

    listed = {j["job_id"]: j for j in jobs.list_recent(limit=50)}
    assert listed[job_id]["stale"] is False

    jobs.fail_stale_active()
    assert jobs.get(job_id)["status"] == "running"


def test_terminal_jobs_never_stale():
    job_id = jobs.create(repo_path="/tmp/done-repo")
    jobs.update(job_id, status="complete", step="complete", progress=100)
    _backdate(job_id, STALE_ACTIVE_MINUTES * 10)

    listed = {j["job_id"]: j for j in jobs.list_recent(limit=50)}
    assert listed[job_id]["stale"] is False

    jobs.fail_stale_active()
    assert jobs.get(job_id)["status"] == "complete"

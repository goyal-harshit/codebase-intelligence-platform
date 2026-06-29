"""Durable job state: persisted to the DB and run via Celery (eager in tests)."""
from api.jobs import JobManager
from api.tasks import ingest_repo_task


def test_job_state_persists_across_manager_instances():
    # A fresh JobManager (as the worker process would have) sees the same row —
    # this is the durability that the old in-memory store lacked.
    writer = JobManager()
    job_id = writer.create(repo_url="https://github.com/x/y.git")
    writer.update(job_id, status="running", step="parsing")

    reader = JobManager()
    job = reader.get(job_id)
    assert job["status"] == "running"
    assert job["step"] == "parsing"


def test_eager_task_runs_and_records_terminal_state():
    # In eager mode .delay() runs synchronously. With no ArcadeDB up, the task
    # should reach a terminal "failed" state (not crash, not stay queued).
    jm = JobManager()
    job_id = jm.create(repo_path="/no/such/repo")
    ingest_repo_task.delay(job_id, None, "/no/such/repo")
    job = jm.get(job_id)
    assert job["status"] in {"failed", "complete", "complete_with_warnings"}


def test_unknown_job_get_returns_none():
    assert JobManager().get("does-not-exist") is None

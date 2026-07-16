"""Phase 7 tests.

Drive the FastAPI app with Starlette's TestClient. The app must boot and behave
with NO backends running: /health works, data endpoints degrade to 503, and the
ingest job lifecycle (create -> queryable status, 404 for unknown) works.
"""
import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from main import app  # noqa: E402

client = TestClient(app)


def test_health_ok():
    r = client.get("/health")
    assert r.status_code == 200 and r.json() == {"status": "ok"}


def test_openapi_lists_all_routes():
    paths = client.get("/openapi.json").json()["paths"]
    for p in ["/api/v1/ingest", "/api/v1/query", "/api/v1/risks", "/api/v1/stats"]:
        assert p in paths
    assert any(p.startswith("/api/v1/impact/") for p in paths)


def test_query_requires_q():
    assert client.get("/api/v1/query").status_code == 422


def test_stats_degrades_to_503_without_graph():
    # No ArcadeDB running in tests -> clean 503, not a crash.
    r = client.get("/api/v1/stats")
    assert r.status_code in (200, 503)
    if r.status_code == 503:
        assert "unavailable" in r.json()["detail"]


def test_ingest_validates_empty_body():
    assert client.post("/api/v1/ingest", json={}).status_code == 400


def test_ingest_creates_job_and_status_is_queryable():
    # repo_path that doesn't exist -> background task marks it failed fast,
    # but the POST itself must return a queued job id.
    r = client.post("/api/v1/ingest", json={"repo_path": "/no/such/repo"})
    assert r.status_code == 200
    job_id = r.json()["job_id"]
    assert r.json()["status"] == "queued"

    status = client.get(f"/api/v1/ingest/{job_id}")
    assert status.status_code == 200
    assert status.json()["job_id"] == job_id
    assert status.json()["status"] in {"queued", "running", "failed", "complete"}


def test_unknown_job_404():
    assert client.get("/api/v1/ingest/deadbeef").status_code == 404


def test_ingest_list_returns_recent_jobs_newest_first():
    # Two jobs created back-to-back; the list endpoint (which backs the global
    # progress bar) must return both, newest first, in the single-job shape.
    a = client.post("/api/v1/ingest", json={"repo_path": "/no/such/repo-a"}).json()["job_id"]
    b = client.post("/api/v1/ingest", json={"repo_path": "/no/such/repo-b"}).json()["job_id"]

    r = client.get("/api/v1/ingest")
    assert r.status_code == 200
    jobs = r.json()["jobs"]
    ids = [j["job_id"] for j in jobs]
    assert ids.index(b) < ids.index(a)
    for j in jobs:
        for key in ("job_id", "status", "step", "progress", "repo_path", "created_at"):
            assert key in j

    limited = client.get("/api/v1/ingest", params={"limit": 1}).json()["jobs"]
    assert len(limited) == 1
    assert client.get("/api/v1/ingest", params={"limit": 0}).status_code == 422

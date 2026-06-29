"""ZIP upload ingestion: happy path enqueues a job, and the archive is rejected
when it is not a zip / empty / contains a traversal path (Phase 3)."""
import io
import zipfile

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from api.jobs import jobs  # noqa: E402
from main import app  # noqa: E402

client = TestClient(app)


def _zip(members: dict[str, str]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, content in members.items():
            zf.writestr(name, content)
    return buf.getvalue()


def _post(data: bytes, filename: str = "repo.zip"):
    return client.post(
        "/api/v1/ingest/upload",
        files={"file": (filename, data, "application/zip")},
    )


def test_upload_zip_enqueues_job(monkeypatch):
    monkeypatch.delenv("API_KEY", raising=False)  # dev-open
    data = _zip({"src/app.py": "def main():\n    return 1\n"})
    r = _post(data)
    assert r.status_code == 200, r.text
    job_id = r.json()["job_id"]
    # The job row exists (durable); eager ingestion reaches a terminal state with
    # no graph backend up, never staying "queued"/raising.
    job = jobs.get(job_id)
    assert job is not None


def test_rejects_non_zip(monkeypatch):
    monkeypatch.delenv("API_KEY", raising=False)
    assert _post(b"not a zip", filename="repo.txt").status_code == 400  # bad extension
    assert _post(b"not a zip", filename="repo.zip").status_code == 400  # not a real zip


def test_rejects_empty(monkeypatch):
    monkeypatch.delenv("API_KEY", raising=False)
    assert _post(b"", filename="repo.zip").status_code == 400


def test_rejects_zip_slip(monkeypatch):
    monkeypatch.delenv("API_KEY", raising=False)
    evil = _zip({"../../escape.txt": "pwned"})
    assert _post(evil).status_code == 400

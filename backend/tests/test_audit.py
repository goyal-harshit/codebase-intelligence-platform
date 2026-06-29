"""Audit logging: security-relevant actions land in the audit_log table, and a
failure in the audit path never breaks the request (Phase 2)."""
import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

import db as _db  # noqa: E402
from api.audit import record_audit  # noqa: E402
from db import AuditLog  # noqa: E402
from main import app  # noqa: E402

client = TestClient(app)


def _count(action: str) -> int:
    with _db.get_sessionmaker()() as s:
        return s.query(AuditLog).filter(AuditLog.action == action).count()


def test_record_audit_persists_row():
    before = _count("unit.test")
    record_audit("unit.test", target="t", detail={"k": "v"})
    assert _count("unit.test") == before + 1


def test_record_audit_swallows_errors(monkeypatch):
    # A broken DB session must not raise out of record_audit.
    def boom():
        raise RuntimeError("db down")

    monkeypatch.setattr(_db, "get_sessionmaker", boom)
    record_audit("unit.test")  # should not raise


def test_query_route_writes_audit_event(monkeypatch):
    monkeypatch.delenv("API_KEY", raising=False)  # dev-open so the route is reachable
    before = _count("query")
    # The route audits before touching the (absent) graph backend, so 503 is fine.
    client.get("/api/v1/query", params={"q": "what calls foo?"})
    assert _count("query") == before + 1

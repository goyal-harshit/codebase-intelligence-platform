"""Tests for API-key auth on data routes (offline)."""
import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from main import app  # noqa: E402

client = TestClient(app)


def test_health_open_without_key(monkeypatch):
    monkeypatch.setenv("API_KEY", "secret")
    assert client.get("/health").status_code == 200


def test_protected_route_401_without_key(monkeypatch):
    monkeypatch.setenv("API_KEY", "secret")
    r = client.get("/api/v1/stats")
    assert r.status_code == 401


def test_protected_route_401_with_wrong_key(monkeypatch):
    monkeypatch.setenv("API_KEY", "secret")
    r = client.get("/api/v1/stats", headers={"X-API-Key": "nope"})
    assert r.status_code == 401


def test_protected_route_passes_auth_with_correct_key(monkeypatch):
    monkeypatch.setenv("API_KEY", "secret")
    # Correct key clears auth; with no graph backend it then degrades to 503/200,
    # never 401.
    r = client.get("/api/v1/stats", headers={"X-API-Key": "secret"})
    assert r.status_code in (200, 503)


def test_open_when_no_key_configured(monkeypatch):
    monkeypatch.delenv("API_KEY", raising=False)
    r = client.get("/api/v1/stats")
    assert r.status_code in (200, 503)  # auth disabled -> not 401

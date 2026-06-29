"""Tests for metrics endpoint, request-id propagation, and rate-limit wiring."""
import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from main import app  # noqa: E402

client = TestClient(app)


def test_metrics_endpoint_exposes_custom_metrics():
    r = client.get("/metrics")
    # prometheus_client is a dependency, so /metrics should serve, not 503.
    assert r.status_code == 200
    body = r.text
    assert "ci_query_latency_seconds" in body
    assert "ci_ingestion_duration_seconds" in body
    assert "ci_llm_calls_total" in body


def test_request_id_is_generated_and_returned():
    r = client.get("/health")
    assert r.headers.get("X-Request-ID")


def test_request_id_is_echoed_when_supplied():
    r = client.get("/health", headers={"X-Request-ID": "abc123"})
    assert r.headers.get("X-Request-ID") == "abc123"


def test_rate_limiter_is_wired():
    from api.ratelimit import SLOWAPI_AVAILABLE

    assert SLOWAPI_AVAILABLE is True
    assert app.state.limiter is not None

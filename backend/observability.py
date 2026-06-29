"""Structured logging, request-ID propagation, and Prometheus metrics.

Shared infrastructure used across the api/ and llm/ packages. Everything here
degrades to a no-op if ``prometheus_client`` is not installed, so the app and
its offline test suite never hard-depend on it.
"""
from __future__ import annotations

import contextvars
import logging

REQUEST_ID_HEADER = "X-Request-ID"

# Per-request correlation id, attached to log records via the filter below.
_request_id: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="-")


def set_request_id(value: str) -> None:
    _request_id.set(value)


def get_request_id() -> str:
    return _request_id.get()


class _RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = get_request_id()
        return True


def configure_logging(level: int = logging.INFO) -> None:
    """Install a request-id-aware log format once (idempotent)."""
    root = logging.getLogger()
    if getattr(root, "_ci_configured", False):
        return
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(
        "%(asctime)s %(levelname)s [%(request_id)s] %(name)s: %(message)s"
    ))
    handler.addFilter(_RequestIdFilter())
    root.addHandler(handler)
    root.setLevel(level)
    root._ci_configured = True  # type: ignore[attr-defined]


# -- metrics ---------------------------------------------------------------

try:
    from prometheus_client import (  # type: ignore
        CONTENT_TYPE_LATEST,
        Counter,
        Histogram,
        generate_latest,
    )

    _PROM = True
    QUERY_LATENCY = Histogram("ci_query_latency_seconds", "NL query latency")
    INGESTION_DURATION = Histogram("ci_ingestion_duration_seconds", "Repo ingestion duration")
    LLM_CALLS = Counter("ci_llm_calls_total", "Number of LLM generate() calls")
except Exception:  # prometheus_client missing -> no-op stubs
    _PROM = False

    class _Noop:
        def labels(self, *a, **k):
            return self

        def observe(self, *a, **k):
            pass

        def inc(self, *a, **k):
            pass

        def time(self):
            from contextlib import nullcontext

            return nullcontext()

    QUERY_LATENCY = INGESTION_DURATION = LLM_CALLS = _Noop()  # type: ignore[assignment]


def metrics_payload() -> tuple[bytes, str] | None:
    """Return (body, content_type) for /metrics, or None if Prometheus is absent."""
    if not _PROM:
        return None
    return generate_latest(), CONTENT_TYPE_LATEST

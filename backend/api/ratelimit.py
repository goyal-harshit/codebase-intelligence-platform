"""Per-client rate limiting via slowapi, with a no-op fallback.

If slowapi is not installed the limiter becomes a pass-through decorator so the
routes still import and run (just unthrottled). Limits are env-configurable.
"""
from __future__ import annotations

import os

try:
    from slowapi import Limiter
    from slowapi.util import get_remote_address

    SLOWAPI_AVAILABLE = True
    limiter = Limiter(key_func=get_remote_address)
except Exception:  # slowapi missing -> identity decorator
    SLOWAPI_AVAILABLE = False

    class _NoopLimiter:
        def limit(self, *_a, **_k):
            def deco(fn):
                return fn

            return deco

    limiter = _NoopLimiter()  # type: ignore[assignment]

INGEST_LIMIT = os.getenv("RATE_LIMIT_INGEST", "10/minute")
QUERY_LIMIT = os.getenv("RATE_LIMIT_QUERY", "60/minute")

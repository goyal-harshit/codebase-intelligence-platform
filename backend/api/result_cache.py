"""Process-local TTL cache for expensive, ingest-derived read endpoints.

Analysis results (stats, risks, hotspots, refactor recommendations) only change
when a new ingest completes, yet the dashboard and detail pages recompute them
from the graph on every visit — the dashboard alone re-runs ~7 graph queries for
risks and a full ``git log`` for hotspots on each load. Cache the results keyed
by ``(name, params)`` behind a TTL guard, and bump a generation counter when an
ingest completes so fresh data shows up immediately instead of after the TTL.

Only successful results are cached: the compute callable runs *outside* the lock
so a slow first computation never blocks other requests, and exceptions
propagate uncached (so a transient backend outage doesn't get pinned).
"""
from __future__ import annotations

import threading
import time
from typing import Any, Callable

# Analysis outputs are stable between ingests; a generous TTL is just a backstop
# in case an invalidation is ever missed. Correctness comes from ``invalidate``.
DEFAULT_TTL_SECONDS = 600.0

_lock = threading.Lock()
_generation = 0
_store: dict[str, tuple[int, float, Any]] = {}


def invalidate() -> None:
    """Drop every cached result — call when new data has been ingested."""
    global _generation
    with _lock:
        _generation += 1
        _store.clear()


def cached(
    key: str,
    compute: Callable[[], Any],
    *,
    ttl: float = DEFAULT_TTL_SECONDS,
    refresh: bool = False,
) -> Any:
    """Return ``compute()``'s result, memoized under *key* until TTL/invalidate.

    ``refresh=True`` forces a recompute (and refreshes the cache).
    """
    with _lock:
        gen = _generation
        entry = _store.get(key)
        if (
            entry is not None
            and not refresh
            and entry[0] == gen
            and time.monotonic() - entry[1] < ttl
        ):
            return entry[2]

    # Compute outside the lock: this can take seconds (git log, graph traversal).
    value = compute()

    with _lock:
        # Only store if no ingest invalidated us mid-compute; otherwise the value
        # may reflect stale data and the next request should recompute.
        if _generation == gen:
            _store[key] = (gen, time.monotonic(), value)
    return value

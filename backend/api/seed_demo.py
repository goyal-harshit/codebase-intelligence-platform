"""First-boot demo seeding (v1.4).

When ``SEED_DEMO_REPO`` is enabled and no ingestion job has ever been recorded,
ingest the bundled ``demo_repo/`` (PyShelf) so a fresh deployment greets the
user with a populated dashboard instead of an empty state. Off by default so
tests and bare dev runs are unaffected; docker-compose turns it on.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path

logger = logging.getLogger("codebase_intelligence.seed")

DEMO_REPO_DIR = Path(__file__).resolve().parents[1] / "demo_repo"

_TRUTHY = {"1", "true", "yes", "on"}


def seed_enabled() -> bool:
    return os.getenv("SEED_DEMO_REPO", "").strip().lower() in _TRUTHY


def maybe_seed_demo_repo() -> str | None:
    """Dispatch a demo-repo ingestion on first boot; return its job id.

    Returns None (and never raises) whenever seeding doesn't apply: flag off,
    a job already exists (not a first boot), the bundled repo is missing, or
    ArcadeDB isn't reachable yet — a failed seed job would be a confusing
    first impression, so we skip quietly rather than record a failure.
    """
    if not seed_enabled():
        return None
    try:
        from .jobs import jobs
        from .tasks import dispatch_ingest

        if jobs.list_recent(limit=1):
            return None
        if not DEMO_REPO_DIR.is_dir():
            logger.warning("SEED_DEMO_REPO set but %s is missing; skipping", DEMO_REPO_DIR)
            return None

        from graph_db import ArcadeDBClient

        if not ArcadeDBClient().is_alive():
            logger.info("SEED_DEMO_REPO set but ArcadeDB is unreachable; skipping demo seed")
            return None

        job_id = jobs.create(repo_path=str(DEMO_REPO_DIR))
        dispatch_ingest(job_id, None, str(DEMO_REPO_DIR))
        logger.info("first boot: ingesting bundled demo repo (job %s)", job_id)
        return job_id
    except Exception:  # noqa: BLE001 — seeding must never break startup
        logger.warning("demo repo seeding failed", exc_info=True)
        return None

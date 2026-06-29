"""Celery application for durable background ingestion.

Defaults to **eager mode** (tasks run synchronously, in-process) when
``CELERY_TASK_ALWAYS_EAGER`` is unset, so the API and the offline test suite run
with no Redis broker. The docker-compose deployment sets a real broker and
``CELERY_TASK_ALWAYS_EAGER=false`` to dispatch work to a separate worker.
"""
from __future__ import annotations

import os

from celery import Celery

BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", BROKER_URL)

_eager_env = os.getenv("CELERY_TASK_ALWAYS_EAGER")
ALWAYS_EAGER = True if _eager_env is None else _eager_env.lower() in ("1", "true", "yes")

celery_app = Celery(
    "codebase_intelligence",
    broker=BROKER_URL,
    backend=RESULT_BACKEND,
    include=["api.tasks"],  # imported lazily by the worker (avoids import cycle)
)
celery_app.conf.update(
    task_always_eager=ALWAYS_EAGER,
    task_eager_propagates=False,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
)

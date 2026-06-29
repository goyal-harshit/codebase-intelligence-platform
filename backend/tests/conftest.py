"""Shared test setup.

Points the relational store at a throwaway SQLite file for the whole test
session (hermetic — no pollution of the real ``data/app.db``) and forces Celery
into eager mode so ingestion runs in-process without a Redis broker.
"""
import os
import tempfile

import pytest


@pytest.fixture(scope="session", autouse=True)
def _hermetic_db():
    fd, path = tempfile.mkstemp(prefix="ci_test_", suffix=".db")
    os.close(fd)
    os.environ["DATABASE_URL"] = "sqlite:///" + path.replace(os.sep, "/")
    os.environ.setdefault("CELERY_TASK_ALWAYS_EAGER", "true")

    import db

    db.reset_engine_cache()
    db.init_db()
    yield
    db.reset_engine_cache()
    try:
        os.remove(path)
    except OSError:
        pass

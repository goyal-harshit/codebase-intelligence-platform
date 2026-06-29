"""Engine + session factory for the relational metadata store.

Design goals (consistent with the rest of this backend):
* **Boots with no external services.** ``DATABASE_URL`` defaults to a local
  SQLite file, so the app and its tests run with zero Postgres dependency.
  Production points ``DATABASE_URL`` at the Postgres container in compose.
* **Lazy.** ``create_engine`` opens no connection at import time; failures only
  surface when a session is actually used.
"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import Session, sessionmaker

# Repo-root data dir, so the default works regardless of launch CWD.
_DATA_DIR = Path(__file__).resolve().parents[2] / "data"
DEFAULT_DATABASE_URL = f"sqlite:///{(_DATA_DIR / 'app.db').as_posix()}"


def get_database_url() -> str:
    return os.getenv("DATABASE_URL") or DEFAULT_DATABASE_URL


@lru_cache
def get_engine() -> Engine:
    url = get_database_url()
    # SQLite needs check_same_thread=False so background-task threads can share
    # the connection pool; Postgres ignores connect_args.
    if url.startswith("sqlite") and "/:memory:" not in url and ":memory:" not in url:
        # Ensure the parent directory exists so SQLite can create the file.
        db_path = url.split("sqlite:///", 1)[-1]
        parent = os.path.dirname(db_path)
        if parent:
            os.makedirs(parent, exist_ok=True)
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    return create_engine(url, future=True, pool_pre_ping=True, connect_args=connect_args)


@lru_cache
def _sessionmaker() -> sessionmaker:
    return sessionmaker(bind=get_engine(), class_=Session, expire_on_commit=False, future=True)


def get_sessionmaker() -> sessionmaker:
    return _sessionmaker()


# -- async layer (for FastAPI-Users, which is async-only) ------------------

def _async_url(url: str) -> str:
    """Map the sync DATABASE_URL to its async driver equivalent."""
    if url.startswith("sqlite:///"):
        return url.replace("sqlite:///", "sqlite+aiosqlite:///", 1)
    if url.startswith("postgresql+psycopg2://"):
        return url.replace("postgresql+psycopg2://", "postgresql+asyncpg://", 1)
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


@lru_cache
def get_async_engine():
    return create_async_engine(_async_url(get_database_url()), future=True, pool_pre_ping=True)


@lru_cache
def _async_sessionmaker():
    return async_sessionmaker(bind=get_async_engine(), class_=AsyncSession, expire_on_commit=False)


async def get_async_session():
    """FastAPI dependency yielding an AsyncSession (used by the auth layer)."""
    async with _async_sessionmaker()() as session:
        yield session


def init_db() -> None:
    """Create tables for local/SQLite dev so the app works without running
    Alembic. For Postgres, Alembic migrations are the source of truth (and this
    call is a harmless no-op-ish create_all of any missing tables)."""
    from . import models  # noqa: F401 - register mapped classes
    from .base import Base

    Base.metadata.create_all(get_engine())


def reset_engine_cache() -> None:
    """Drop cached engine/sessionmaker (used by tests that swap DATABASE_URL)."""
    get_engine.cache_clear()
    _sessionmaker.cache_clear()
    get_async_engine.cache_clear()
    _async_sessionmaker.cache_clear()

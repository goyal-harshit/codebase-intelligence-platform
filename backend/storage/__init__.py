"""Pluggable object storage. Defaults to the local filesystem so the app boots
with no external services; set ``MINIO_ENDPOINT`` to use MinIO/S3 instead."""
from __future__ import annotations

import os
from functools import lru_cache

from .base import Storage
from .local import LocalStorage

__all__ = ["Storage", "LocalStorage", "get_storage", "reset_storage_cache"]


@lru_cache
def get_storage() -> Storage:
    endpoint = os.getenv("MINIO_ENDPOINT")
    if endpoint:
        from .minio_store import MinioStorage

        return MinioStorage(
            endpoint=endpoint,
            access_key=os.getenv("MINIO_ACCESS_KEY", "minioadmin"),
            secret_key=os.getenv("MINIO_SECRET_KEY", "minioadmin"),
            bucket=os.getenv("MINIO_BUCKET", "codebase-uploads"),
            secure=os.getenv("MINIO_SECURE", "false").lower() == "true",
        )
    root = os.getenv("STORAGE_LOCAL_ROOT") or os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "data", "uploads",
    )
    return LocalStorage(root)


def reset_storage_cache() -> None:
    """Drop the cached backend (used by tests that swap storage env vars)."""
    get_storage.cache_clear()

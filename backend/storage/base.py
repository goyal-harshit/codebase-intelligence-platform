"""Object-storage abstraction (Phase 3).

One small interface so uploaded artifacts can live on the local filesystem in
dev (zero infra, the project's default) or in MinIO/S3 in production, selected
by env var. Keys are forward-slash paths (e.g. ``uploads/<uuid>.zip``).
"""
from __future__ import annotations

from abc import ABC, abstractmethod


class Storage(ABC):
    @abstractmethod
    def put(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        """Store ``data`` under ``key``; return a backend-specific locator."""

    @abstractmethod
    def get(self, key: str) -> bytes:
        """Read back the bytes stored under ``key``."""

    @abstractmethod
    def exists(self, key: str) -> bool:
        ...

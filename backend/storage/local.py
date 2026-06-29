"""Filesystem-backed Storage — the zero-infra default (dev + self-hosted)."""
from __future__ import annotations

import os
from pathlib import Path

from .base import Storage


class LocalStorage(Storage):
    def __init__(self, root: str) -> None:
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _resolve(self, key: str) -> Path:
        # Confine every key under root; reject traversal out of the store.
        target = (self.root / key).resolve()
        if os.path.commonpath([self.root, target]) != str(self.root):
            raise ValueError(f"key escapes storage root: {key}")
        return target

    def put(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        path = self._resolve(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return str(path)

    def get(self, key: str) -> bytes:
        return self._resolve(key).read_bytes()

    def exists(self, key: str) -> bool:
        return self._resolve(key).exists()

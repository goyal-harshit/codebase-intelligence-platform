"""Repository traversal and incremental-change detection helpers."""
from __future__ import annotations

import hashlib
import os
from typing import Iterator

from .parser import LANGUAGE_MAP

IGNORE_DIRS = {".git", "node_modules", "venv", ".venv", "__pycache__",
               "dist", "build", ".next", ".mypy_cache", ".pytest_cache"}


def walk_repository(repo_path: str, only_supported: bool = True) -> Iterator[str]:
    """Yield file paths for all (optionally only parseable) source files."""
    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
        for name in files:
            if only_supported and os.path.splitext(name)[1] not in LANGUAGE_MAP:
                continue
            yield os.path.join(root, name)


def file_hash(file_path: str) -> str:
    """SHA-256 of file content; used for incremental update detection."""
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()

"""Repository traversal and incremental-change detection helpers."""
from __future__ import annotations

import fnmatch
import hashlib
import os
from typing import Iterator

from .parser import LANGUAGE_MAP

IGNORE_DIRS = {".git", "node_modules", "venv", ".venv", "__pycache__",
               "dist", "build", ".next", ".mypy_cache", ".pytest_cache",
               ".idea", ".obsidian", "graphify-out"}
DEFAULT_IGNORE_PATHS = {
    "data/repos",
    "reports",
}


def _load_ignore_paths(repo_path: str) -> set[str]:
    """Load simple path ignores from .graphifyignore plus built-in generated
    directories. Patterns are repo-relative and intentionally conservative."""
    patterns = set(DEFAULT_IGNORE_PATHS)
    ignore_file = os.path.join(repo_path, ".graphifyignore")
    try:
        with open(ignore_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    patterns.add(line.rstrip("/\\"))
    except OSError:
        pass
    return {p.replace("\\", "/").strip("/") for p in patterns if p.strip("/\\")}


def _ignored(rel_path: str, patterns: set[str]) -> bool:
    rel = rel_path.replace("\\", "/").strip("/")
    for pattern in patterns:
        if rel == pattern or rel.startswith(pattern + "/"):
            return True
        if fnmatch.fnmatch(rel, pattern):
            return True
    return False


def walk_repository(repo_path: str, only_supported: bool = True) -> Iterator[str]:
    """Yield file paths for all (optionally only parseable) source files."""
    repo_path = os.path.abspath(repo_path)
    ignore_paths = _load_ignore_paths(repo_path)
    for root, dirs, files in os.walk(repo_path):
        kept = []
        for d in dirs:
            full = os.path.join(root, d)
            rel = os.path.relpath(full, repo_path)
            if d in IGNORE_DIRS or _ignored(rel, ignore_paths):
                continue
            kept.append(d)
        dirs[:] = kept
        for name in files:
            if only_supported and os.path.splitext(name)[1] not in LANGUAGE_MAP:
                continue
            path = os.path.join(root, name)
            rel = os.path.relpath(path, repo_path)
            if _ignored(rel, ignore_paths):
                continue
            yield path


def file_hash(file_path: str) -> str:
    """SHA-256 of file content; used for incremental update detection."""
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()

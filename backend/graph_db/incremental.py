"""Incremental re-indexing driven by per-file SHA-256 hashes.

A small SQLite key-value store persists ``file_path -> content_hash`` so that
on a subsequent run only changed/added files are re-parsed, and their stale
vertices are removed (``DETACH DELETE``) before re-insertion. Deleted files are
also pruned from the graph.
"""
from __future__ import annotations

import sqlite3
from typing import TYPE_CHECKING

from ast_parser import SymbolResolver, UniversalParser, file_hash, walk_repository

from .builder import GraphBuilder, _file_id

if TYPE_CHECKING:
    from .client import ArcadeDBClient


class FileHashStore:
    """Persistent ``file_path -> hash`` map backed by SQLite."""

    def __init__(self, db_path: str = "data/file_hashes.db") -> None:
        import os
        os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
        self._conn = sqlite3.connect(db_path)
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS file_hashes (path TEXT PRIMARY KEY, hash TEXT NOT NULL)"
        )
        self._conn.commit()

    def get(self, path: str) -> str | None:
        row = self._conn.execute(
            "SELECT hash FROM file_hashes WHERE path = ?", (path,)
        ).fetchone()
        return row[0] if row else None

    def set(self, path: str, value: str) -> None:
        self._conn.execute(
            "INSERT INTO file_hashes (path, hash) VALUES (?, ?) "
            "ON CONFLICT(path) DO UPDATE SET hash = excluded.hash",
            (path, value),
        )
        self._conn.commit()

    def delete(self, path: str) -> None:
        self._conn.execute("DELETE FROM file_hashes WHERE path = ?", (path,))
        self._conn.commit()

    def all_paths(self) -> set[str]:
        return {r[0] for r in self._conn.execute("SELECT path FROM file_hashes")}

    def close(self) -> None:
        self._conn.close()


class IncrementalUpdater:
    def __init__(self, client: "ArcadeDBClient", hash_store: FileHashStore,
                 parser: UniversalParser | None = None) -> None:
        self.client = client
        self.hash_store = hash_store
        self.parser = parser or UniversalParser()

    def update(self, repo_path: str) -> dict:
        """Re-index only changed/added files and prune deleted ones."""
        seen: set[str] = set()
        changed: list[str] = []
        for path in walk_repository(repo_path):
            seen.add(path)
            current = file_hash(path)
            if current != self.hash_store.get(path):
                changed.append(path)
                self._reindex_file(path)
                self.hash_store.set(path, current)

        deleted = self.hash_store.all_paths() - seen
        for path in deleted:
            self._purge_file(path)
            self.hash_store.delete(path)

        return {"changed": changed, "deleted": sorted(deleted)}

    # -- internals ---------------------------------------------------------

    def _reindex_file(self, path: str) -> None:
        self._purge_file(path)
        entities, relationships = self.parser.parse_file(path)
        if not entities:
            return
        # Resolve call targets against this file's own symbols so intra-file
        # CALLS edges survive ingestion. Cross-file calls cannot be resolved
        # from a single file in isolation; a periodic full rebuild
        # (build_graph.py --reset) re-links them with global symbol context.
        relationships = SymbolResolver().resolve(entities, relationships)
        GraphBuilder(self.client).build(entities, relationships)

    def _purge_file(self, path: str) -> None:
        """Remove the File node and every entity defined in it."""
        self.client.command(
            "MATCH (n {file_path: $path}) DETACH DELETE n", params={"path": path}
        )
        self.client.command(
            "MATCH (f:File {id: $fid}) DETACH DELETE f", params={"fid": _file_id(path)}
        )

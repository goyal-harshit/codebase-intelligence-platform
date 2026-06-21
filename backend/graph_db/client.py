"""Thin HTTP client for ArcadeDB.

Wraps ArcadeDB's REST API (https://docs.arcadedb.com/#HTTP-API). Reads
(idempotent) go through ``/api/v1/query``; writes through
``/api/v1/command``. The default query language is Cypher, but schema DDL
(``CREATE VERTEX TYPE ...``) must be sent as ``sql`` — pass ``language="sql"``.
"""
from __future__ import annotations

import os
from typing import Any, Optional

import requests


class ArcadeDBError(RuntimeError):
    """Raised when ArcadeDB returns a non-2xx response."""


class ArcadeDBClient:
    def __init__(
        self,
        base_url: Optional[str] = None,
        database: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        timeout: float = 120.0,
    ) -> None:
        self.base_url = (base_url or os.getenv("ARCADEDB_URL", "http://localhost:2480")).rstrip("/")
        self.database = database or os.getenv("ARCADEDB_DATABASE", "codebase")
        self.user = user or os.getenv("ARCADEDB_USER", "root")
        self.password = password or os.getenv("ARCADEDB_PASSWORD", "")
        self.timeout = timeout
        self._session = requests.Session()
        self._session.auth = (self.user, self.password)

    # -- low-level ---------------------------------------------------------

    def _post(self, path: str, payload: dict) -> Any:
        resp = self._session.post(f"{self.base_url}{path}", json=payload, timeout=self.timeout)
        if resp.status_code >= 300:
            raise ArcadeDBError(f"{resp.status_code} {resp.request.method} {path}: {resp.text}")
        if not resp.content:
            return None
        return resp.json().get("result")

    # -- server / database lifecycle --------------------------------------

    def is_alive(self) -> bool:
        try:
            resp = self._session.get(f"{self.base_url}/api/v1/ready", timeout=5)
            return resp.status_code < 300
        except requests.RequestException:
            return False

    def database_exists(self) -> bool:
        try:
            dbs = self._post("/api/v1/server", {"command": "list databases"}) or {}
        except ArcadeDBError:
            return False
        names = dbs.get("databases", dbs) if isinstance(dbs, dict) else dbs
        return self.database in (names or [])

    def create_database(self, if_not_exists: bool = True) -> None:
        if if_not_exists and self.database_exists():
            return
        self._post("/api/v1/server", {"command": f"create database {self.database}"})

    def drop_database(self) -> None:
        self._post("/api/v1/server", {"command": f"drop database {self.database}"})

    # -- queries / commands ------------------------------------------------

    def query(self, command: str, params: Optional[dict] = None, language: str = "cypher") -> Any:
        """Run an idempotent read."""
        return self._post(
            f"/api/v1/query/{self.database}",
            {"language": language, "command": command, "params": params or {}},
        )

    def command(self, command: str, params: Optional[dict] = None, language: str = "cypher") -> Any:
        """Run a write/DDL statement."""
        return self._post(
            f"/api/v1/command/{self.database}",
            {"language": language, "command": command, "params": params or {}},
        )

    # convenience aliases matching the master-plan naming
    def execute_cypher(self, command: str, params: Optional[dict] = None) -> Any:
        return self.query(command, params, language="cypher")

    def execute_command(self, command: str, params: Optional[dict] = None) -> Any:
        return self.command(command, params, language="cypher")

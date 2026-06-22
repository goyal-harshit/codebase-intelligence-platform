"""Graph schema: vertex/edge types and indexes.

ArcadeDB DDL is SQL, not Cypher, so these statements are executed with
``language="sql"``. Each statement is idempotent (``IF NOT EXISTS``).
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .client import ArcadeDBClient

# Every distinct entity vertex label we may create, plus the synthesized
# File node and the auxiliary types used by later phases.
VERTEX_TYPES = [
    "File",
    "Function",
    "Class",
    "Interface",
    "Module",
    "ExternalDependency",
    "SecurityIssue",
    "Author",
    "TestFile",
]

EDGE_TYPES = [
    "CONTAINS",
    "CALLS",
    "IMPORTS",
    "INHERITS_FROM",
    "DEPENDS_ON",
    "AFFECTED_BY",
    "AUTHORED_BY",
    "COVERED_BY",
]

# (type, property, unique?) — id is unique per vertex type so MATCH-by-id is fast.
INDEXES = [
    ("File", "id", True),
    ("File", "path", True),
    ("Function", "id", True),
    ("Function", "name", False),
    ("Class", "id", True),
    ("Class", "name", False),
    ("Interface", "id", True),
    ("Module", "id", True),
]


def schema_statements() -> list[str]:
    """Return the ordered list of DDL statements that define the schema."""
    stmts = [f"CREATE VERTEX TYPE {v} IF NOT EXISTS" for v in VERTEX_TYPES]
    stmts += [f"CREATE EDGE TYPE {e} IF NOT EXISTS" for e in EDGE_TYPES]
    # ArcadeDB requires a property to exist before it can be indexed.
    for vtype, prop, _ in INDEXES:
        stmts.append(f"CREATE PROPERTY {vtype}.{prop} IF NOT EXISTS STRING")
    for vtype, prop, unique in INDEXES:
        kind = "UNIQUE" if unique else "NOTUNIQUE"
        stmts.append(f"CREATE INDEX IF NOT EXISTS ON {vtype} ({prop}) {kind}")
    return stmts


def apply_schema(client: "ArcadeDBClient") -> None:
    """Create all vertex/edge types and indexes on the database."""
    for stmt in schema_statements():
        client.command(stmt, language="sql")

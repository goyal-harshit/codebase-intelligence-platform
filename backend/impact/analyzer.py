"""Change-impact / blast-radius analysis.

Given a file (or a single entity), walk the CALLS graph backwards to find every
function transitively affected by a change, bucket them by hop distance, and
score the overall blast radius.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from graph_db import ArcadeDBClient

TRANSITIVE_CAP = 50  # cap returned transitive rows to keep responses bounded
MAX_DEPTH = 50  # hard cap on the variable-length path bound (see _bounded_depth)


def _bounded_depth(value: int) -> int:
    """Coerce a traversal depth to a safe, bounded int.

    The depth is interpolated into a Cypher variable-length quantifier
    (``[:CALLS*1..N]``), which cannot be a bind parameter, so it must be proven
    to be an integer in range here. Out-of-range/garbage values are clamped
    rather than passed through.
    """
    return max(1, min(int(value), MAX_DEPTH))


class ImpactAnalyzer:
    def __init__(self, client: "ArcadeDBClient") -> None:
        self.client = client

    def analyze_file_impact(self, file_path: str, max_depth: int = 5) -> dict:
        depth = _bounded_depth(max_depth)
        rows = self.client.query(
            "MATCH (f:File {path: $path})-[:CONTAINS]->(entity) "
            f"MATCH p = (entity)<-[:CALLS*1..{depth}]-(affected) "
            "RETURN DISTINCT affected.name AS name, "
            "affected.file_path AS file, length(p) AS hops ORDER BY hops ASC",
            params={"path": file_path},
        )
        return self._summarize(file_path, rows)

    def analyze_entity_impact(self, entity_id: str, max_depth: int = 5) -> dict:
        depth = _bounded_depth(max_depth)
        rows = self.client.query(
            f"MATCH p = ({{id: $id}})<-[:CALLS*1..{depth}]-(affected) "
            "RETURN DISTINCT affected.name AS name, "
            "affected.file_path AS file, length(p) AS hops ORDER BY hops ASC",
            params={"id": entity_id},
        )
        return self._summarize(entity_id, rows)

    def find_affected_tests(self, file_path: str) -> list[dict]:
        """Tests covering entities in the file. Needs COVERED_BY edges (Phase 4+
        data gap) — returns [] until coverage ingestion lands."""
        return self.client.query(
            "MATCH (f:File {path: $path})-[:CONTAINS]->(entity) "
            "MATCH (entity)-[:COVERED_BY]->(t:TestFile) "
            "RETURN DISTINCT t.path AS path",
            params={"path": file_path},
        )

    # -- internals ---------------------------------------------------------

    def _summarize(self, target: str, rows: list[dict]) -> dict:
        direct = [r for r in rows if r["hops"] == 1]
        transitive = [r for r in rows if r["hops"] > 1]
        return {
            "target": target,
            "directly_affected_count": len(direct),
            "transitively_affected_count": len(transitive),
            "directly_affected": direct,
            "transitively_affected": transitive[:TRANSITIVE_CAP],
            "risk_level": self._risk_level(len(direct) + len(transitive)),
        }

    @staticmethod
    def _risk_level(total: int) -> str:
        if total > 50:
            return "critical"
        if total > 20:
            return "high"
        if total > 5:
            return "medium"
        return "low"

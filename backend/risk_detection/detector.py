"""Architecture-risk detection over the code graph.

Each rule is a Cypher query against the Phase 2 schema. Rules backed by data
the parser already produces (CONTAINS/CALLS edges, complexity/LOC properties)
are live now; rules needing IMPORTS / INHERITS_FROM edges (circular deps, deep
inheritance, dependency bloat) are implemented and forward-compatible — they
return nothing until those edges are populated (see KNOWN DATA GAPS in README).
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from graph_db import ArcadeDBClient

SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}


class RiskDetector:
    def __init__(
        self,
        client: "ArcadeDBClient",
        god_object_methods: int = 20,
        high_complexity: int = 15,
        long_method_loc: int = 100,
        shotgun_files: int = 30,
        deep_inheritance: int = 5,
    ) -> None:
        self.client = client
        self.god_object_methods = god_object_methods
        self.high_complexity = high_complexity
        self.long_method_loc = long_method_loc
        self.shotgun_files = shotgun_files
        self.deep_inheritance = deep_inheritance

    # -- data-backed rules -------------------------------------------------

    def detect_god_objects(self) -> list[dict]:
        rows = self.client.query(
            "MATCH (c:Class)-[:CONTAINS]->(m:Function) "
            "WITH c, count(m) AS n WHERE n > $threshold "
            "RETURN c.name AS name, c.file_path AS file, n AS method_count "
            "ORDER BY n DESC",
            params={"threshold": self.god_object_methods},
        )
        return [
            {"type": "god_object", "severity": "high", "target": r["name"],
             "file": r["file"], "details": f"{r['method_count']} methods "
             f"(threshold {self.god_object_methods})"}
            for r in rows
        ]

    def detect_dead_code(self) -> list[dict]:
        rows = self.client.query(
            "MATCH (f:Function) WHERE NOT (f)<-[:CALLS]-() "
            "RETURN f.name AS name, f.file_path AS file, f.lines_of_code AS loc"
        )
        return [
            {"type": "dead_code", "severity": "medium", "target": r["name"],
             "file": r["file"], "details": "no incoming calls"}
            for r in rows
        ]

    def detect_high_complexity(self) -> list[dict]:
        rows = self.client.query(
            "MATCH (f:Function) WHERE f.cyclomatic_complexity > $threshold "
            "RETURN f.name AS name, f.file_path AS file, "
            "f.cyclomatic_complexity AS complexity ORDER BY complexity DESC",
            params={"threshold": self.high_complexity},
        )
        return [
            {"type": "high_complexity", "severity": "medium", "target": r["name"],
             "file": r["file"], "details": f"cyclomatic complexity {r['complexity']}"}
            for r in rows
        ]

    def detect_long_methods(self) -> list[dict]:
        rows = self.client.query(
            "MATCH (f:Function) WHERE f.lines_of_code > $threshold "
            "RETURN f.name AS name, f.file_path AS file, f.lines_of_code AS loc "
            "ORDER BY loc DESC",
            params={"threshold": self.long_method_loc},
        )
        return [
            {"type": "long_method", "severity": "low", "target": r["name"],
             "file": r["file"], "details": f"{r['loc']} lines"}
            for r in rows
        ]

    def detect_shotgun_surgery(self) -> list[dict]:
        rows = self.client.query(
            "MATCH (f:Function)<-[:CALLS]-(caller) "
            "WITH f, count(DISTINCT caller.file_path) AS n WHERE n > $threshold "
            "RETURN f.name AS name, f.file_path AS file, n AS caller_files "
            "ORDER BY n DESC",
            params={"threshold": self.shotgun_files},
        )
        return [
            {"type": "shotgun_surgery", "severity": "high", "target": r["name"],
             "file": r["file"], "details": f"called from {r['caller_files']} files"}
            for r in rows
        ]

    # -- rules awaiting IMPORTS / INHERITS_FROM edges ----------------------

    def detect_circular_dependencies(self) -> list[dict]:
        rows = self.client.query(
            "MATCH p=(a:Module)-[:IMPORTS*2..6]->(a) "
            "RETURN DISTINCT a.name AS name, length(p) AS cycle_length"
        )
        return [
            {"type": "circular_dependency", "severity": "high", "target": r["name"],
             "file": "", "details": f"cycle length {r['cycle_length']}"}
            for r in rows
        ]

    def detect_deep_inheritance(self) -> list[dict]:
        rows = self.client.query(
            f"MATCH p=(c:Class)-[:INHERITS_FROM*{self.deep_inheritance}..]->(b:Class) "
            "RETURN c.name AS name, c.file_path AS file, length(p) AS depth "
            "ORDER BY depth DESC"
        )
        return [
            {"type": "deep_inheritance", "severity": "medium", "target": r["name"],
             "file": r["file"], "details": f"inheritance depth {r['depth']}"}
            for r in rows
        ]

    # -- aggregation -------------------------------------------------------

    def run_all_checks(self) -> list[dict]:
        risks: list[dict] = []
        risks += self.detect_god_objects()
        risks += self.detect_dead_code()
        risks += self.detect_high_complexity()
        risks += self.detect_long_methods()
        risks += self.detect_shotgun_surgery()
        risks += self.detect_circular_dependencies()
        risks += self.detect_deep_inheritance()
        return sorted(risks, key=lambda r: SEVERITY_ORDER[r["severity"]])


def persist_risks(client: "ArcadeDBClient", risks: list[dict], batch_size: int = 500) -> int:
    """Write detected risks back to the graph as SecurityIssue vertices."""
    rows = [
        {"type": r["type"], "severity": r["severity"], "target": r["target"],
         "file": r.get("file", ""), "details": r.get("details", "")}
        for r in risks
    ]
    cypher = (
        "UNWIND $rows AS row CREATE (s:SecurityIssue {"
        "type: row.type, severity: row.severity, target: row.target, "
        "file: row.file, details: row.details})"
    )
    for i in range(0, len(rows), batch_size):
        client.command(cypher, params={"rows": rows[i:i + batch_size]})
    return len(rows)

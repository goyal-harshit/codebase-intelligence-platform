"""Phase 4 tests.

Offline against a fake graph client that returns canned query rows per call,
so detector logic, severity ordering, and persistence are validated without a
live database. A gated ARCADEDB_INTEGRATION test runs against real data.
"""
import os

import pytest

from risk_detection import RiskDetector, SEVERITY_ORDER, persist_risks


class FakeClient:
    """Returns successive preset row-lists from `results`; records writes."""

    def __init__(self, results=None):
        self.results = list(results or [])
        self.queries = []
        self.commands = []

    def query(self, command, params=None, language="cypher"):
        self.queries.append((command, params or {}))
        return self.results.pop(0) if self.results else []

    def command(self, command, params=None, language="cypher"):
        self.commands.append((command, params or {}))
        return []


def test_god_object_mapping_and_threshold_param():
    client = FakeClient([[{"name": "God", "file": "g.py", "method_count": 42}]])
    risks = RiskDetector(client, god_object_methods=20).detect_god_objects()
    assert risks == [{
        "type": "god_object", "severity": "high", "target": "God",
        "file": "g.py", "details": "42 methods (threshold 20)",
    }]
    assert client.queries[0][1] == {"threshold": 20}


def test_dead_code_uses_negated_call_pattern():
    client = FakeClient([[{"name": "orphan", "file": "a.py", "loc": 3}]])
    risks = RiskDetector(client).detect_dead_code()
    assert risks[0]["type"] == "dead_code" and risks[0]["severity"] == "medium"
    assert "NOT (f)<-[:CALLS]-()" in client.queries[0][0]


def test_high_complexity_threshold():
    client = FakeClient([[{"name": "f", "file": "a.py", "complexity": 22}]])
    risks = RiskDetector(client, high_complexity=15).detect_high_complexity()
    assert "22" in risks[0]["details"]
    assert client.queries[0][1] == {"threshold": 15}


def test_shotgun_surgery_counts_distinct_files():
    client = FakeClient([[{"name": "util", "file": "u.py", "caller_files": 50}]])
    risks = RiskDetector(client, shotgun_files=30).detect_shotgun_surgery()
    assert risks[0]["severity"] == "high"
    assert "DISTINCT caller.file_path" in client.queries[0][0]


def test_deep_inheritance_uses_configured_depth():
    client = FakeClient([[]])
    RiskDetector(client, deep_inheritance=5).detect_deep_inheritance()
    assert "INHERITS_FROM*5.." in client.queries[0][0]


def test_run_all_checks_sorted_by_severity():
    # one result list per detector call, in run_all_checks order:
    # god(high), dead(medium), high_complexity(medium), long(low),
    # shotgun(high), circular(high), deep_inheritance(medium)
    client = FakeClient([
        [{"name": "G", "file": "g.py", "method_count": 30}],   # god -> high
        [{"name": "d", "file": "d.py", "loc": 2}],             # dead -> medium
        [],                                                     # high_complexity
        [{"name": "lng", "file": "l.py", "loc": 200}],         # long -> low
        [],                                                     # shotgun
        [],                                                     # circular
        [],                                                     # deep inheritance
    ])
    risks = RiskDetector(client).run_all_checks()
    severities = [SEVERITY_ORDER[r["severity"]] for r in risks]
    assert severities == sorted(severities)
    assert risks[0]["severity"] == "high"      # god object first
    assert risks[-1]["severity"] == "low"      # long method last


def test_persist_risks_is_parameterized_and_batched():
    client = FakeClient()
    risks = [
        {"type": "god_object", "severity": "high", "target": "G",
         "file": "g.py", "details": "30 methods"},
        {"type": "dead_code", "severity": "medium", "target": "d"},  # no file/details
    ]
    n = persist_risks(client, risks, batch_size=500)
    assert n == 2
    cypher, params = client.commands[0]
    assert "UNWIND $rows" in cypher and "CREATE (s:SecurityIssue" in cypher
    assert params["rows"][1]["file"] == "" and params["rows"][1]["details"] == ""


@pytest.mark.skipif(
    not os.getenv("ARCADEDB_INTEGRATION"),
    reason="set ARCADEDB_INTEGRATION=1 with a live, populated graph to run",
)
def test_integration_runs_against_live_graph():
    from graph_db import ArcadeDBClient

    risks = RiskDetector(ArcadeDBClient()).run_all_checks()
    assert isinstance(risks, list)

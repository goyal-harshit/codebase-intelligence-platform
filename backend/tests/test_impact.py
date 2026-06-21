"""Phase 5 tests.

Offline against a fake graph client returning canned hop rows; validates
bucketing (direct vs transitive), the transitive cap, risk-level thresholds,
and query construction. A gated ARCADEDB_INTEGRATION test hits live data.
"""
import os

import pytest

from impact import ImpactAnalyzer, TRANSITIVE_CAP


class FakeClient:
    def __init__(self, rows=None):
        self.rows = list(rows or [])
        self.queries = []

    def query(self, command, params=None, language="cypher"):
        self.queries.append((command, params or {}))
        return self.rows


def _rows(*hops):
    return [{"name": f"fn{i}", "file": f"f{i}.py", "hops": h} for i, h in enumerate(hops)]


def test_buckets_direct_and_transitive():
    client = FakeClient(_rows(1, 1, 2, 3))
    result = ImpactAnalyzer(client).analyze_file_impact("a.py")
    assert result["directly_affected_count"] == 2
    assert result["transitively_affected_count"] == 2
    assert result["target"] == "a.py"


def test_passes_path_param_and_depth_in_query():
    client = FakeClient([])
    ImpactAnalyzer(client).analyze_file_impact("auth.py", max_depth=3)
    cypher, params = client.queries[0]
    assert params == {"path": "auth.py"}
    assert "[:CALLS*1..3]" in cypher


def test_depth_floored_to_one():
    client = FakeClient([])
    ImpactAnalyzer(client).analyze_file_impact("a.py", max_depth=0)
    assert "[:CALLS*1..1]" in client.queries[0][0]


def test_transitive_results_capped():
    client = FakeClient(_rows(*([2] * (TRANSITIVE_CAP + 25))))
    result = ImpactAnalyzer(client).analyze_file_impact("big.py")
    assert len(result["transitively_affected"]) == TRANSITIVE_CAP
    assert result["transitively_affected_count"] == TRANSITIVE_CAP + 25  # count is uncapped


@pytest.mark.parametrize("total,level", [
    (3, "low"), (10, "medium"), (25, "high"), (60, "critical"),
])
def test_risk_level_thresholds(total, level):
    assert ImpactAnalyzer._risk_level(total) == level


def test_entity_impact_matches_by_id():
    client = FakeClient([])
    ImpactAnalyzer(client).analyze_entity_impact("abc123", max_depth=2)
    cypher, params = client.queries[0]
    assert params == {"id": "abc123"}
    assert "{id: $id}" in cypher and "[:CALLS*1..2]" in cypher


def test_find_affected_tests_query_shape():
    client = FakeClient([])
    ImpactAnalyzer(client).find_affected_tests("a.py")
    assert "COVERED_BY" in client.queries[0][0]


@pytest.mark.skipif(
    not os.getenv("ARCADEDB_INTEGRATION"),
    reason="set ARCADEDB_INTEGRATION=1 with a populated graph to run",
)
def test_integration_smoke():
    from graph_db import ArcadeDBClient

    result = ImpactAnalyzer(ArcadeDBClient()).analyze_file_impact("nonexistent.py")
    assert result["risk_level"] == "low"

"""The variable-length depth interpolated into Cypher must be a bounded int."""
import pytest

from impact.analyzer import MAX_DEPTH, ImpactAnalyzer
from risk_detection.detector import RiskDetector


class _CaptureClient:
    def __init__(self):
        self.queries = []

    def query(self, command, params=None, language="cypher"):
        self.queries.append(command)
        return []


def test_impact_depth_clamped_to_max():
    c = _CaptureClient()
    ImpactAnalyzer(c).analyze_file_impact("a.py", max_depth=9999)
    assert f"*1..{MAX_DEPTH}]" in c.queries[0]


def test_impact_depth_floored_at_one():
    c = _CaptureClient()
    ImpactAnalyzer(c).analyze_file_impact("a.py", max_depth=0)
    assert "*1..1]" in c.queries[0]


def test_impact_depth_normal_value_passes_through():
    c = _CaptureClient()
    ImpactAnalyzer(c).analyze_file_impact("a.py", max_depth=3)
    assert "*1..3]" in c.queries[0]


def test_deep_inheritance_normal_value_interpolates_bounded():
    c = _CaptureClient()
    RiskDetector(c, deep_inheritance=4).detect_deep_inheritance()
    assert "INHERITS_FROM*4.." in c.queries[0]


def test_deep_inheritance_rejects_non_numeric_threshold():
    c = _CaptureClient()
    # A hostile non-int threshold fails closed (never reaches the query as text).
    with pytest.raises(ValueError):
        RiskDetector(c, deep_inheritance="5 OR 1=1").detect_deep_inheritance()  # type: ignore[arg-type]
    assert c.queries == []

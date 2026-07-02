"""Phase 10 tests — risk→recommendation mapping, ordering, and narrative."""
from __future__ import annotations

import refactoring.recommender as rec_mod
from refactoring import RefactoringRecommender, recommend_narrative

CANNED = [
    {"type": "dead_code", "severity": "medium", "target": "unused_fn", "file": "a.py", "details": "no callers"},
    {"type": "god_object", "severity": "high", "target": "BigClass", "file": "b.py", "details": "40 methods"},
    {"type": "unknown_type", "severity": "low", "target": "x", "file": "c.py", "details": ""},
]


class _FakeDetector:
    def __init__(self, *a, **k):
        pass

    def run_all_checks(self):
        return list(CANNED)


def test_maps_risks_and_orders_by_severity_then_effort(monkeypatch):
    monkeypatch.setattr(rec_mod, "RiskDetector", _FakeDetector)
    recs = RefactoringRecommender(client=None).recommend()

    # unknown_type has no template → dropped
    types = [r["type"] for r in recs]
    assert types == ["god_object", "dead_code"]  # high before medium
    top = recs[0]
    assert top["title"] == "Split god object"
    assert top["effort"] == "high"
    assert "BigClass" in top["suggestion"]
    assert top["id"]  # stable id present


def test_narrative_uses_llm_and_degrades(monkeypatch):
    monkeypatch.setattr(rec_mod, "RiskDetector", _FakeDetector)
    recs = RefactoringRecommender(client=None).recommend()

    class OkLLM:
        def generate(self, prompt, temperature=0.2):
            assert "BigClass" in prompt
            return "1. Do the god object first."

    class BadLLM:
        def generate(self, prompt, temperature=0.2):
            raise RuntimeError("llm down")

    assert recommend_narrative(recs, OkLLM()).startswith("1.")
    assert recommend_narrative(recs, BadLLM()) is None  # graceful degrade
    assert recommend_narrative([], OkLLM()) is None

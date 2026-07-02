"""Refactoring recommendation engine (roadmap Phase 10).

Turns the architecture risks the graph already surfaces (god objects, dead code,
high complexity, circular deps, …) into concrete, prioritized refactoring
recommendations. Deterministic and fast; an optional narrative plan can be
generated with the local LLM."""
from .recommender import RefactoringRecommender, recommend_narrative

__all__ = ["RefactoringRecommender", "recommend_narrative"]

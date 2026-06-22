"""Self-contained codebase analysis engine (no external services required).

Computes a complete intelligence report from the AST parser output plus
(optionally) git history, using an in-memory graph. This is the offline,
zero-dependency-on-Docker path that powers the analysis report.
"""
from .engine import analyze_repository, CodebaseAnalysis
from .git_insights import collect_git_insights

__all__ = ["analyze_repository", "CodebaseAnalysis", "collect_git_insights"]

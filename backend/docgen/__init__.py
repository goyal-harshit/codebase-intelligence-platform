"""Auto-documentation ("wiki") generator (roadmap v1.3).

Turns the parsed entities the graph already stores into per-module markdown
documentation: a deterministic skeleton (entity inventory, signatures,
imports, cross-file dependents) plus an optional LLM-written "Purpose" prose
section that degrades away cleanly when no model is reachable."""
from .generator import (
    MAX_NARRATIVE_MODULES,
    DocGenerator,
    build_skeleton,
    build_wiki,
    purpose_narrative,
)

__all__ = [
    "MAX_NARRATIVE_MODULES",
    "DocGenerator",
    "build_skeleton",
    "build_wiki",
    "purpose_narrative",
]

"""Risk detection engine (Phase 4): architecture-smell detection over the graph."""
from .detector import RiskDetector, persist_risks, SEVERITY_ORDER

__all__ = ["RiskDetector", "persist_risks", "SEVERITY_ORDER"]

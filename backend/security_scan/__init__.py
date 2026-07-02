"""Static application security testing (SAST) — roadmap Phase 11.

Regex-based, dependency-free, LLM-free source scanner. Finds hardcoded secrets,
injection-prone patterns, weak crypto, and insecure defaults, and reports them
in the same shape the risk pipeline uses so the frontend can render them
alongside architecture risks."""
from .scanner import SecurityScanner, SEVERITY_ORDER, scan_repository

__all__ = ["SecurityScanner", "SEVERITY_ORDER", "scan_repository"]

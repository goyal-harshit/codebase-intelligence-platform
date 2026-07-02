"""Map architecture risks → actionable refactoring recommendations.

Each risk ``type`` from :class:`risk_detection.RiskDetector` maps to a template
(title, rationale, concrete suggestion, effort). Deterministic — no LLM needed
for the recommendations themselves; :func:`recommend_narrative` can layer a
short prioritized plan on top using the local model.
"""
from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING, Optional

from risk_detection import RiskDetector, SEVERITY_ORDER

if TYPE_CHECKING:
    from graph_db import ArcadeDBClient
    from llm import LLMClient

# risk type -> (title, rationale, suggestion template, effort)
_TEMPLATES: dict[str, tuple[str, str, str, str]] = {
    "god_object": (
        "Split god object",
        "A class with too many methods concentrates responsibility and is hard to test or change safely.",
        "Extract cohesive method groups from {target} into smaller collaborating classes/modules "
        "(e.g. {target}Service + {target}Repository).",
        "high",
    ),
    "dead_code": (
        "Remove dead code",
        "Functions with no callers add maintenance burden and obscure the live call graph.",
        "Confirm {target} is truly unused (including dynamic/reflection calls and tests), then delete it.",
        "low",
    ),
    "high_complexity": (
        "Reduce complexity",
        "High cyclomatic complexity means many branches — error-prone and hard to reason about.",
        "Decompose {target}: extract guard clauses and helper functions, and replace nested conditionals "
        "with early returns or a lookup/strategy.",
        "medium",
    ),
    "long_method": (
        "Break up long method",
        "Very long methods usually do several things and resist reuse and testing.",
        "Split {target} into a few well-named helpers, each with a single responsibility.",
        "medium",
    ),
    "shotgun_surgery": (
        "Stabilize a high-fan-in interface",
        "An entity called from many places makes every change ripple widely (shotgun surgery).",
        "Introduce a stable abstraction/facade in front of {target} so callers depend on an interface, "
        "not the implementation.",
        "high",
    ),
    "circular_dependency": (
        "Break circular dependency",
        "Cyclic module dependencies couple components and block independent change and testing.",
        "Break the cycle around {target} by extracting the shared contract into a separate module or "
        "inverting one dependency (dependency inversion / mediator).",
        "high",
    ),
    "deep_inheritance": (
        "Flatten deep inheritance",
        "Deep inheritance chains are rigid and make behavior hard to trace.",
        "Prefer composition over inheritance for {target}; collapse layers that add no real specialization.",
        "medium",
    ),
}

_EFFORT_ORDER = {"low": 0, "medium": 1, "high": 2}


def _rec_id(risk_type: str, target: str, file: str) -> str:
    return hashlib.sha1(f"{risk_type}|{target}|{file}".encode()).hexdigest()[:12]


class RefactoringRecommender:
    def __init__(self, client: "ArcadeDBClient") -> None:
        self.client = client

    def recommend(self, limit: int = 100) -> list[dict]:
        risks = RiskDetector(self.client).run_all_checks()
        recs: list[dict] = []
        for r in risks:
            tpl = _TEMPLATES.get(r["type"])
            if tpl is None:
                continue
            title, rationale, suggestion, effort = tpl
            target = r.get("target") or "this entity"
            recs.append({
                "id": _rec_id(r["type"], target, r.get("file") or ""),
                "type": r["type"],
                "title": title,
                "severity": r["severity"],
                "target": target,
                "file": r.get("file"),
                "rationale": rationale,
                "suggestion": suggestion.format(target=target),
                "effort": effort,
                "details": r.get("details"),
            })
        # Highest severity first, then lower effort (quick wins) first.
        recs.sort(key=lambda x: (SEVERITY_ORDER.get(x["severity"], 9), _EFFORT_ORDER.get(x["effort"], 9)))
        return recs[:limit]


def recommend_narrative(recs: list[dict], llm: "LLMClient", max_items: int = 12) -> Optional[str]:
    """One bounded LLM call producing a short prioritized plan. Returns None on
    failure so the endpoint degrades to recommendations-only."""
    if not recs:
        return None
    lines = [
        f"- [{r['severity']}/{r['effort']} effort] {r['title']}: {r['target']}"
        + (f" ({r['file']})" if r.get("file") else "")
        for r in recs[:max_items]
    ]
    prompt = (
        "You are a staff engineer planning a refactoring sprint. Given these "
        "detected issues, write a concise prioritized plan (5-8 bullet points). "
        "Group related items, call out quick wins vs. larger efforts, and note any "
        "sequencing/risk. Do not invent issues beyond the list.\n\n"
        + "\n".join(lines)
    )
    try:
        return llm.generate(prompt, temperature=0.2).strip() or None
    except Exception:  # noqa: BLE001 - LLM optional; degrade gracefully
        return None

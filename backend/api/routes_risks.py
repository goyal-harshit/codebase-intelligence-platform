from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request

from risk_detection import RiskDetector

from .audit import record_audit
from .deps import get_graph_client
from .result_cache import cached
from .security import Principal, get_principal

router = APIRouter()


def cached_risks(graph) -> list[dict]:
    """All architecture risks, cached until the next ingest. run_all_checks fires
    ~7 graph queries, so this is shared by the route and the post-ingest warmer."""
    return cached("risks", lambda: RiskDetector(graph).run_all_checks())


@router.get("/risks")
def risks(
    request: Request,
    severity: Optional[str] = None,
    graph=Depends(get_graph_client),
    principal: Principal = Depends(get_principal),
):
    record_audit(
        "risks", user_id=principal.user_id, detail={"severity": severity}, request=request
    )
    try:
        # The dashboard and risks page hit this on every load. Cache the full
        # result set (invalidated on ingest) and filter by severity in Python so
        # all severities share one compute.
        items = cached_risks(graph)
        if severity:
            items = [r for r in items if r["severity"] == severity]
        return {"risks": items, "total": len(items)}
    except Exception as e:
        raise HTTPException(503, f"graph backend unavailable: {e}")

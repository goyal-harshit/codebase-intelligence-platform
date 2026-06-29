from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request

from risk_detection import RiskDetector

from .audit import record_audit
from .deps import get_graph_client
from .security import Principal, get_principal

router = APIRouter()


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
        items = RiskDetector(graph).run_all_checks()
        if severity:
            items = [r for r in items if r["severity"] == severity]
        return {"risks": items, "total": len(items)}
    except Exception as e:
        raise HTTPException(503, f"graph backend unavailable: {e}")

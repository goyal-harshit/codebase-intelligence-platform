from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from risk_detection import RiskDetector

from .deps import get_graph_client

router = APIRouter()


@router.get("/risks")
def risks(severity: Optional[str] = None, graph=Depends(get_graph_client)):
    try:
        items = RiskDetector(graph).run_all_checks()
        if severity:
            items = [r for r in items if r["severity"] == severity]
        return {"risks": items, "total": len(items)}
    except Exception as e:
        raise HTTPException(503, f"graph backend unavailable: {e}")

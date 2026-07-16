"""AI summarization endpoint (Phase 4): summarize a file/module.

Provide ``code`` directly, or omit it to have the entities the graph knows about
for ``target`` used as context. Behind the standard data-route auth gate.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from . import summarizer as _summarizer
from .audit import record_audit
from .deps import get_graph_client, get_llm
from .security import Principal, get_principal
from .validators import ValidationError, validate_relative_path

router = APIRouter()


class SummarizeRequest(BaseModel):
    target: str = Field(..., description="file path or module name")
    kind: str = Field("file", description="file | module | class")
    code: Optional[str] = Field(None, description="optional source to summarize directly")


@router.post("/summarize")
def summarize_route(
    req: SummarizeRequest,
    request: Request,
    graph=Depends(get_graph_client),
    llm=Depends(get_llm),
    principal: Principal = Depends(get_principal),
):
    if req.code:
        context = req.code
    else:
        try:
            target = validate_relative_path(req.target)
        except ValidationError as e:
            raise HTTPException(400, str(e))
        # The graph stores whatever path the parser walked (absolute at ingest
        # time), so an exact match on the repo-relative input never hits —
        # resolve it the same way the impact endpoint does.
        from impact import ImpactAnalyzer

        try:
            resolved, suggestions = ImpactAnalyzer(graph).resolve_file_path(target)
        except Exception as e:
            raise HTTPException(503, f"graph backend unavailable: {e}")
        if resolved is None:
            detail = f"no indexed entities found for '{req.target}'"
            if suggestions:
                detail += "; did you mean: " + ", ".join(suggestions)
            raise HTTPException(404, detail)
        try:
            rows = graph.query(
                "MATCH (f:File {path: $path})-[:CONTAINS]->(e) "
                "RETURN e.name AS name, e.lines_of_code AS loc",
                params={"path": resolved},
            )
        except Exception as e:
            raise HTTPException(503, f"graph backend unavailable: {e}")
        if not rows:
            raise HTTPException(404, f"no indexed entities found for '{req.target}'")
        context = _summarizer.context_from_entities(rows)

    try:
        summary = _summarizer.summarize(llm, req.target, context, kind=req.kind)
    except Exception as e:
        raise HTTPException(503, f"LLM backend unavailable: {e}")
    record_audit("summarize", user_id=principal.user_id, target=req.target, request=request)
    return {"target": req.target, "kind": req.kind, "summary": summary}

"""Auto-documentation ("wiki") endpoints (roadmap v1.3).

``GET /api/v1/docgen/modules`` lists the documentable modules (source files
the graph knows). ``POST /api/v1/docgen/generate`` renders markdown pages for
selected (or all) modules; ``narrative=true`` adds a short LLM-written Purpose
section per module (best-effort — pages fall back to the deterministic
skeleton if the model is unreachable). ``GET /api/v1/docgen/wiki`` returns all
pages concatenated behind an index section.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from docgen import DocGenerator, build_wiki

from .audit import record_audit
from .deps import get_graph_client, get_llm
from .routes_files import _latest_repo_path

router = APIRouter()


def _generator(graph) -> DocGenerator:
    """DocGenerator with the latest ingest root as its (cosmetic) display root,
    so wiki titles are repo-relative instead of machine paths. Best-effort:
    docgen must keep working when the job store has no usable root."""
    try:
        root = _latest_repo_path()
    except Exception:  # noqa: BLE001
        root = None
    return DocGenerator(graph, display_root=root)


class GenerateRequest(BaseModel):
    modules: Optional[list[str]] = Field(
        None, description="module paths to document; omit for all known modules"
    )
    narrative: bool = Field(
        False, description="add an LLM-written Purpose section per module (best-effort)"
    )


@router.get("/docgen/modules")
def docgen_modules(graph=Depends(get_graph_client)):
    gen = _generator(graph)
    try:
        modules = gen.list_modules()
    except Exception as e:  # noqa: BLE001
        raise HTTPException(503, f"graph backend unavailable: {e}")
    return {
        "modules": modules,
        "total": len(modules),
        # Cosmetic prefix the UI may strip from module labels (repo root of
        # the latest completed ingest); "" when unknown.
        "display_root": gen.display_root or "",
    }


@router.post("/docgen/generate")
def docgen_generate(
    request: Request,
    req: Optional[GenerateRequest] = None,
    graph=Depends(get_graph_client),
):
    req = req or GenerateRequest()
    record_audit(
        "docgen_generate",
        detail={"narrative": req.narrative, "modules": len(req.modules or [])},
        request=request,
    )
    try:
        pages = _generator(graph).generate(
            modules=req.modules,
            narrative=req.narrative,
            llm=get_llm() if req.narrative else None,
        )
    except Exception as e:  # noqa: BLE001
        raise HTTPException(503, f"graph backend unavailable: {e}")
    return {"pages": pages, "total": len(pages), "narrative": req.narrative}


@router.get("/docgen/wiki")
def docgen_wiki(
    request: Request,
    narrative: bool = Query(default=False),
    graph=Depends(get_graph_client),
):
    record_audit("docgen_wiki", detail={"narrative": narrative}, request=request)
    try:
        pages = _generator(graph).generate(
            narrative=narrative, llm=get_llm() if narrative else None
        )
    except Exception as e:  # noqa: BLE001
        raise HTTPException(503, f"graph backend unavailable: {e}")
    return {
        "markdown": build_wiki(pages),
        "modules": [p["module"] for p in pages],
        "total": len(pages),
    }

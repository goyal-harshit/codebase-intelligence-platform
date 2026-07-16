"""Export endpoints: download risk reports and impact analysis as CSV/Excel.

Sits behind the same auth gate as the other data routes (wired in main.py) and
records an audit event per export.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response

from impact import ImpactAnalyzer
from risk_detection import RiskDetector

from . import exports as _exports
from . import report as _report
from .audit import record_audit
from .deps import get_graph_client, get_llm
from .security import Principal, get_principal
from .validators import ValidationError, validate_relative_path

router = APIRouter()


def _attachment(filename: str, fmt: str, body: bytes) -> Response:
    media_type, _ = _exports.FORMATS[fmt]
    return Response(
        content=body,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _check_format(fmt: str) -> None:
    if fmt not in _exports.FORMATS:
        raise HTTPException(400, f"format must be one of {list(_exports.FORMATS)}")


@router.get("/export/risks")
def export_risks(
    request: Request,
    format: str = Query("csv"),
    severity: Optional[str] = None,
    graph=Depends(get_graph_client),
    principal: Principal = Depends(get_principal),
):
    _check_format(format)
    try:
        items = RiskDetector(graph).run_all_checks()
    except Exception as e:
        raise HTTPException(503, f"graph backend unavailable: {e}")
    if severity:
        items = [r for r in items if r["severity"] == severity]
    headers, rows = _exports.risks_to_rows(items)
    body = _exports.render(format, headers, rows, sheet_title="risks")
    record_audit(
        "export.risks",
        user_id=principal.user_id,
        detail={"format": format, "severity": severity, "count": len(rows)},
        request=request,
    )
    _, suffix = _exports.FORMATS[format]
    return _attachment(f"risks.{suffix}", format, body)


@router.get("/export/security")
def export_security(
    request: Request,
    repo_path: Optional[str] = Query(default=None),
    format: str = Query("csv"),
    severity: Optional[str] = None,
    principal: Principal = Depends(get_principal),
):
    import os
    import time
    from security_scan import scan_repository
    from .routes_security import _latest_repo_path, _scan_cache, _CACHE_TTL_SECONDS
    
    _check_format(format)
    path = repo_path or _latest_repo_path()
    if not path or not os.path.isdir(path):
        raise HTTPException(400, "invalid or missing repo_path")
        
    cached = _scan_cache.get(path)
    if cached and time.monotonic() - cached[0] < _CACHE_TTL_SECONDS:
        result = cached[1]
    else:
        try:
            result = scan_repository(path, external=True)
            _scan_cache[path] = (time.monotonic(), result)
        except Exception as e:
            raise HTTPException(503, f"security scan failed: {e}")
            
    findings = result["findings"]
    if severity:
        findings = [f for f in findings if f.get("severity") == severity]
        
    headers, rows = _exports.security_to_rows(findings)
    body = _exports.render(format, headers, rows, sheet_title="security")
    
    record_audit(
        "export.security",
        user_id=principal.user_id,
        detail={"format": format, "severity": severity, "count": len(rows)},
        request=request,
    )
    _, suffix = _exports.FORMATS[format]
    return _attachment(f"security.{suffix}", format, body)


@router.get("/export/refactor")
def export_refactor(
    request: Request,
    format: str = Query("csv"),
    limit: int = Query(default=500, ge=1, le=2000),
    graph=Depends(get_graph_client),
    principal: Principal = Depends(get_principal),
):
    from refactoring import RefactoringRecommender
    
    _check_format(format)
    try:
        recs = RefactoringRecommender(graph).recommend(limit=limit)
    except Exception as e:
        raise HTTPException(503, f"graph backend unavailable: {e}")
        
    headers, rows = _exports.refactor_to_rows(recs)
    body = _exports.render(format, headers, rows, sheet_title="refactoring")
    
    record_audit(
        "export.refactor",
        user_id=principal.user_id,
        detail={"format": format, "count": len(rows)},
        request=request,
    )
    _, suffix = _exports.FORMATS[format]
    return _attachment(f"refactoring_recommendations.{suffix}", format, body)


@router.get("/export/impact/{file_path:path}")
def export_impact(
    file_path: str,
    request: Request,
    format: str = Query("csv"),
    depth: int = 5,
    graph=Depends(get_graph_client),
    principal: Principal = Depends(get_principal),
):
    _check_format(format)
    try:
        file_path = validate_relative_path(file_path)
    except ValidationError as e:
        raise HTTPException(400, str(e))
    analyzer = ImpactAnalyzer(graph)
    try:
        # Resolve the repo-relative input to the (absolute) path stored in the
        # graph — an unresolved path silently yields an empty export.
        resolved, suggestions = analyzer.resolve_file_path(file_path)
    except Exception as e:
        raise HTTPException(503, f"graph backend unavailable: {e}")
    if resolved is None:
        detail = f"file not found in graph: {file_path}"
        if suggestions:
            detail += "; did you mean: " + ", ".join(suggestions)
        raise HTTPException(404, detail)
    try:
        result = analyzer.analyze_file_impact(resolved, max_depth=depth)
    except Exception as e:
        raise HTTPException(503, f"graph backend unavailable: {e}")
    headers, rows = _exports.impact_to_rows(result)
    body = _exports.render(format, headers, rows, sheet_title="impact")
    record_audit(
        "export.impact",
        user_id=principal.user_id,
        target=file_path,
        detail={"format": format, "count": len(rows)},
        request=request,
    )
    _, suffix = _exports.FORMATS[format]
    safe = file_path.replace("/", "_").replace("\\", "_")
    return _attachment(f"impact_{safe}.{suffix}", format, body)


@router.get("/report/risks")
def report_risks(
    request: Request,
    format: str = Query("html", description="html or pdf"),
    graph=Depends(get_graph_client),
    principal: Principal = Depends(get_principal),
):
    if format not in ("html", "pdf"):
        raise HTTPException(400, "format must be 'html' or 'pdf'")
    try:
        items = RiskDetector(graph).run_all_checks()
    except Exception as e:
        raise HTTPException(503, f"graph backend unavailable: {e}")
    html = _report.build_html_report(items)
    record_audit(
        "report.risks",
        user_id=principal.user_id,
        detail={"format": format, "count": len(items)},
        request=request,
    )
    if format == "html":
        return Response(content=html, media_type="text/html")
    try:
        pdf = _report.to_pdf(html)
    except RuntimeError as e:
        raise HTTPException(503, str(e))
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="risk_report.pdf"'},
    )


@router.get("/report/narrative")
def report_narrative(
    request: Request,
    format: str = Query("html", description="html or pdf"),
    graph=Depends(get_graph_client),
    llm=Depends(get_llm),
    principal: Principal = Depends(get_principal),
):
    """AI-narrated risk report: an LLM executive summary on top of the findings
    table (Phase 4 item 4, building on the Phase 3 PDF pipeline)."""
    if format not in ("html", "pdf"):
        raise HTTPException(400, "format must be 'html' or 'pdf'")
    try:
        items = RiskDetector(graph).run_all_checks()
    except Exception as e:
        raise HTTPException(503, f"graph backend unavailable: {e}")
    try:
        narrative = _report.build_narrative(llm, items)
    except Exception as e:
        raise HTTPException(503, f"LLM backend unavailable: {e}")
    html = _report.build_html_report(items, narrative=narrative)
    record_audit(
        "report.narrative",
        user_id=principal.user_id,
        detail={"format": format, "count": len(items)},
        request=request,
    )
    if format == "html":
        return Response(content=html, media_type="text/html")
    try:
        pdf = _report.to_pdf(html)
    except RuntimeError as e:
        raise HTTPException(503, str(e))
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="narrative_report.pdf"'},
    )

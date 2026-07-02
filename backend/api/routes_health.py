"""Service health probe (plan Phase A.3).

``GET /api/v1/health/services`` pings the three external backends the query
path depends on — ArcadeDB (graph), ChromaDB (vectors), and the LLM (Ollama /
OpenAI-compatible) — so a down service shows up as an explicit red status in the
UI instead of surfacing later as a mysterious 503 on ``/query``.

Checks are cheap, time-bounded, and never raise: each returns ``ok: false`` with
a short reason rather than failing the whole endpoint.
"""
from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor

import requests
from fastapi import APIRouter

from .deps import get_graph_client, get_llm

router = APIRouter()

_TIMEOUT = 2.5


def _check_arcadedb() -> dict:
    client = get_graph_client()
    try:
        return {"ok": bool(client.is_alive()), "url": client.base_url}
    except Exception as e:  # noqa: BLE001 - health must never raise
        return {"ok": False, "url": getattr(client, "base_url", None), "error": str(e)}


def _check_chromadb() -> dict:
    host = os.getenv("CHROMA_HOST", "localhost")
    port = int(os.getenv("CHROMA_PORT", "8000"))
    base = f"http://{host}:{port}"
    # Heartbeat path moved from /api/v1 to /api/v2 across Chroma versions; try both.
    last_error = None
    for path in ("/api/v2/heartbeat", "/api/v1/heartbeat"):
        try:
            resp = requests.get(base + path, timeout=_TIMEOUT)
            if resp.status_code < 300:
                return {"ok": True, "url": base}
            last_error = f"HTTP {resp.status_code}"
        except requests.RequestException as e:
            last_error = str(e)
    return {"ok": False, "url": base, "error": last_error}


def _check_llm() -> dict:
    client = get_llm()
    base = client.base_url
    try:
        resp = requests.get(f"{base}/api/tags", timeout=_TIMEOUT)
        if resp.status_code < 300:
            models = [m.get("name") for m in resp.json().get("models", [])]
            return {
                "ok": True,
                "url": base,
                "model": client.model,
                "model_present": client.model in models if models else None,
            }
        return {"ok": False, "url": base, "model": client.model, "error": f"HTTP {resp.status_code}"}
    except requests.RequestException as e:
        return {"ok": False, "url": base, "model": client.model, "error": str(e)}


@router.get("/health/services")
def health_services() -> dict:
    # Probed concurrently so one slow/down service doesn't stack its timeout
    # on top of the others' — worst case is max(_TIMEOUT), not the sum.
    checks = {"arcadedb": _check_arcadedb, "chromadb": _check_chromadb, "ollama": _check_llm}
    with ThreadPoolExecutor(max_workers=len(checks)) as pool:
        futures = {name: pool.submit(fn) for name, fn in checks.items()}
        services = {name: f.result() for name, f in futures.items()}
    return {"services": services, "all_ok": all(s["ok"] for s in services.values())}

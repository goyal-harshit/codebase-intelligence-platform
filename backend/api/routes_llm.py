"""LLM configuration + local-model management (plan Phase C).

Free/local providers only — Ollama and any OpenAI-compatible local server. No
paid cloud providers. Endpoints:

- ``GET  /api/v1/llm-config``          effective provider/base_url/model (+ key-set flag)
- ``PUT  /api/v1/llm-config``          update it (JWT-protected); key encrypted at rest
- ``GET  /api/v1/llm-config/models``   models installed on the configured runtime
- ``POST /api/v1/llm-config/pull``     pull/download an Ollama model (background, WS progress)
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from auth import current_active_user
from llm import config as llm_config

from .audit import record_audit
from .deps import get_llm, llm_provider

router = APIRouter()


class LlmConfigUpdate(BaseModel):
    provider: str = Field(description="ollama | openai_compatible")
    base_url: Optional[str] = Field(default=None, max_length=2048)
    model: Optional[str] = Field(default=None, max_length=255)
    # Optional bearer token for local servers that require one. Omit to keep the
    # existing stored key; send "" to clear it.
    api_key: Optional[str] = Field(default=None, max_length=4096)


class ModelPull(BaseModel):
    model: str = Field(min_length=1, max_length=255)


@router.get("/llm-config")
def llm_config_get() -> dict:
    return llm_config.public_config()


@router.put("/llm-config")
def llm_config_put(body: LlmConfigUpdate, request: Request, user=Depends(current_active_user)):
    try:
        result = llm_config.set_config(
            body.provider,
            body.base_url,
            body.model,
            body.api_key,  # None → keep existing; "" → clear
        )
    except llm_config.ConfigError as e:
        raise HTTPException(400, str(e))
    record_audit(
        "llm.config.update",
        user_id=user.id,
        detail={"provider": body.provider, "model": body.model},
        request=request,
    )
    return result


@router.get("/llm-config/models")
def llm_config_models() -> dict:
    client = get_llm()
    lister = getattr(client, "list_models", None)
    if lister is None:
        return {"provider": llm_provider(), "available": False,
                "models": [], "error": "provider does not support model listing"}
    try:
        return {"provider": llm_provider(), "available": True, "models": lister()}
    except Exception as e:  # noqa: BLE001 - report unreachable runtime, don't 500
        return {"provider": llm_provider(), "available": False, "models": [], "error": str(e)}


@router.post("/llm-config/pull", status_code=202)
def llm_config_pull(body: ModelPull, request: Request, user=Depends(current_active_user)):
    """Pull an Ollama model in the background; progress arrives as notifications
    (in-app + WebSocket). Only valid when the active provider is Ollama."""
    if llm_provider() not in {"ollama"}:
        raise HTTPException(400, "model pull is only supported for the Ollama provider")
    from .tasks import dispatch_model_pull

    dispatch_model_pull(body.model, user.id)
    record_audit("llm.model.pull", user_id=user.id, detail={"model": body.model}, request=request)
    return {"status": "started", "model": body.model}

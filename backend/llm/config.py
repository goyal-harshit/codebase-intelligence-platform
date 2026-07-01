"""Effective LLM configuration: DB override layer over the ``LLM_*`` env vars.

The ``llm_settings`` row (if present) wins; otherwise the environment defaults
apply. ``deps.get_llm()`` builds a client from :func:`effective_config`, so a
runtime ``PUT /api/v1/llm-config`` change takes effect on the next request
without a restart. The API key is encrypted at rest and only decrypted here for
internal use — :func:`public_config` never exposes it.
"""
from __future__ import annotations

import os
from typing import Optional

import db as _db
from db import LlmSetting

from . import secretbox

_ROW_ID = "default"
# Free / local providers only: Ollama's native API, or any OpenAI-compatible
# local server (LM Studio, llama.cpp, vLLM, text-generation-webui).
_VALID_PROVIDERS = {"ollama", "openai_compatible"}


def _env_default(provider: str) -> tuple[str, str]:
    """(base_url, model) defaults for a provider from the environment."""
    model = os.getenv("LLM_MODEL") or os.getenv("OLLAMA_MODEL") or ""
    base = os.getenv("LLM_BASE_URL") or os.getenv("OLLAMA_URL") or "http://localhost:11434"
    return base, (model or "qwen2.5-coder:7b")


def _load_row() -> Optional[LlmSetting]:
    with _db.get_sessionmaker()() as s:
        return s.get(LlmSetting, _ROW_ID)


def effective_config() -> dict:
    """Full config for internal use — includes the decrypted ``api_key``."""
    row = _load_row()
    if row is None:
        provider = (os.getenv("LLM_PROVIDER") or "ollama").strip().lower()
        base_url, model = _env_default(provider)
        return {
            "provider": provider,
            "base_url": base_url,
            "model": model,
            "api_key": os.getenv("LLM_API_KEY") or "",
            "source": "env",
        }
    env_base, env_model = _env_default(row.provider)
    api_key = ""
    if row.api_key_encrypted:
        try:
            api_key = secretbox.decrypt(row.api_key_encrypted)
        except Exception:  # noqa: BLE001 - corrupt/rotated key → treat as unset
            api_key = ""
    return {
        "provider": row.provider,
        "base_url": row.base_url or env_base,
        "model": row.model or env_model,
        "api_key": api_key,
        "source": "db",
    }


def public_config() -> dict:
    """Config safe to return over the API — key replaced with a boolean."""
    cfg = effective_config()
    return {
        "provider": cfg["provider"],
        "base_url": cfg["base_url"],
        "model": cfg["model"],
        "api_key_set": bool(cfg["api_key"]),
        "source": cfg["source"],
    }


class ConfigError(ValueError):
    pass


def set_config(
    provider: str,
    base_url: Optional[str],
    model: Optional[str],
    api_key: Optional[str],
    *,
    clear_api_key: bool = False,
) -> dict:
    """Upsert the singleton config row. ``api_key`` semantics:

    - ``None`` and not ``clear_api_key`` → keep the existing stored key.
    - a non-empty string → encrypt and store it.
    - ``clear_api_key`` (or empty string) → remove the stored key.
    """
    provider = (provider or "").strip().lower()
    if provider not in _VALID_PROVIDERS:
        raise ConfigError(f"provider must be one of {sorted(_VALID_PROVIDERS)}")

    with _db.get_sessionmaker()() as s:
        row = s.get(LlmSetting, _ROW_ID)
        if row is None:
            row = LlmSetting(id=_ROW_ID)
            s.add(row)
        row.provider = provider
        row.base_url = (base_url or "").strip() or None
        row.model = (model or "").strip() or None
        if clear_api_key or api_key == "":
            row.api_key_encrypted = None
        elif api_key is not None:
            row.api_key_encrypted = secretbox.encrypt(api_key)
        s.commit()
    return public_config()

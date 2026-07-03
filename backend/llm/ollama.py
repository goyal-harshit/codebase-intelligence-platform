"""Local LLM access via Ollama.

``LLMClient`` is a minimal protocol so the retrieval/answer layers can be driven
by the real Ollama server or a fake in tests.

Config via the shared LLM_BASE_URL / LLM_MODEL convention used across the repo
(see ``backend/analysis/llm.py``); OLLAMA_URL / OLLAMA_MODEL are still honoured
as fallbacks for older configs. Defaults: ``http://localhost:11434`` and
``qwen2.5-coder:7b``. This client speaks the *native* Ollama API
(``/api/generate``), which lives at the server root, so an OpenAI-compatible
``/v1`` suffix on the base URL is stripped if present.
"""
from __future__ import annotations

import os
from typing import Protocol, runtime_checkable

import requests

from observability import LLM_CALLS


@runtime_checkable
class LLMClient(Protocol):
    def generate(self, prompt: str, temperature: float = 0.2) -> str:
        ...


def _resolve_base_url(explicit: str | None = None) -> str:
    """Server root for the native Ollama API, honouring the shared env vars."""
    raw = (explicit or os.getenv("LLM_BASE_URL") or os.getenv("OLLAMA_URL")
           or "http://localhost:11434").rstrip("/")
    if raw.endswith("/v1"):  # OpenAI-compatible suffix the *other* client wants
        raw = raw[: -len("/v1")]
    return raw


class OllamaClient:
    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        timeout: float | None = None,
    ) -> None:
        self.base_url = _resolve_base_url(base_url)
        self.model = model or os.getenv("LLM_MODEL") or os.getenv("OLLAMA_MODEL") or "qwen2.5-coder:7b"
        # CPU-only boxes need headroom: a cold call pays model load (~GBs from
        # disk) plus prompt eval, which regularly blows past 120s.
        self.timeout = timeout if timeout is not None else float(os.getenv("LLM_TIMEOUT", "300"))
        self._session = requests.Session()

    def generate(self, prompt: str, temperature: float = 0.2) -> str:
        LLM_CALLS.inc()
        resp = self._session.post(
            f"{self.base_url}/api/generate",
            json={
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                # Keep the model resident between calls: the default 5-minute
                # eviction makes the next query pay a cold load again.
                "keep_alive": os.getenv("LLM_KEEP_ALIVE", "60m"),
                # Ollama takes sampling params under "options", not top-level.
                "options": {"temperature": temperature},
            },
            timeout=self.timeout,
        )
        resp.raise_for_status()
        return resp.json()["response"].strip()

    def list_models(self, timeout: float = 5.0) -> list[str]:
        """Names of models installed on the Ollama server (``GET /api/tags``).

        Powers the Settings model-picker so users choose from what's pulled
        instead of typing a tag by hand. Raises on connection failure.
        """
        resp = self._session.get(f"{self.base_url}/api/tags", timeout=timeout)
        resp.raise_for_status()
        return [m.get("name") for m in resp.json().get("models", []) if m.get("name")]

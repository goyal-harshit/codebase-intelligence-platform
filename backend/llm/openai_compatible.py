"""OpenAI-compatible LLM client (plan Phase C).

Speaks the ``/v1/chat/completions`` API that LM Studio, llama.cpp's server,
vLLM, text-generation-webui, and hosted providers (OpenAI itself, etc.) all
expose. Implements the same ``generate()`` protocol as :class:`OllamaClient`, so
``deps.get_llm()`` can hand either one to ``QueryEngine`` unchanged.

Config via the shared convention:
  LLM_BASE_URL   default http://localhost:11434/v1  (normalised to end in /v1)
  LLM_MODEL      default qwen2.5-coder:7b
  LLM_API_KEY    optional bearer token for hosted endpoints
"""
from __future__ import annotations

import os

import requests

from observability import LLM_CALLS


def _resolve_base_url(explicit: str | None = None) -> str:
    raw = (explicit or os.getenv("LLM_BASE_URL") or os.getenv("OLLAMA_URL")
           or "http://localhost:11434/v1").rstrip("/")
    if not raw.endswith("/v1"):
        raw += "/v1"
    return raw


class OpenAICompatibleClient:
    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        api_key: str | None = None,
        timeout: float = 120.0,
    ) -> None:
        self.base_url = _resolve_base_url(base_url)
        self.model = model or os.getenv("LLM_MODEL") or os.getenv("OLLAMA_MODEL") or "qwen2.5-coder:7b"
        self.api_key = api_key or os.getenv("LLM_API_KEY") or ""
        self.timeout = timeout
        self._session = requests.Session()

    def _headers(self) -> dict:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def generate(self, prompt: str, temperature: float = 0.2) -> str:
        LLM_CALLS.inc()
        resp = self._session.post(
            f"{self.base_url}/chat/completions",
            headers=self._headers(),
            json={
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": temperature,
                "stream": False,
            },
            timeout=self.timeout,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()

    def list_models(self, timeout: float = 5.0) -> list[str]:
        resp = self._session.get(
            f"{self.base_url}/models", headers=self._headers(), timeout=timeout
        )
        resp.raise_for_status()
        return [m.get("id") for m in resp.json().get("data", []) if m.get("id")]

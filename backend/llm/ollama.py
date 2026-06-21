"""Local LLM access via Ollama.

``LLMClient`` is a minimal protocol so the retrieval/answer layers can be driven
by the real Ollama server or a fake in tests. Config via OLLAMA_URL (default
http://localhost:11434) and OLLAMA_MODEL (default ``mistral``).
"""
from __future__ import annotations

import os
from typing import Protocol, runtime_checkable

import requests


@runtime_checkable
class LLMClient(Protocol):
    def generate(self, prompt: str, temperature: float = 0.2) -> str:
        ...


class OllamaClient:
    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        timeout: float = 120.0,
    ) -> None:
        self.base_url = (base_url or os.getenv("OLLAMA_URL", "http://localhost:11434")).rstrip("/")
        self.model = model or os.getenv("OLLAMA_MODEL", "mistral")
        self.timeout = timeout
        self._session = requests.Session()

    def generate(self, prompt: str, temperature: float = 0.2) -> str:
        resp = self._session.post(
            f"{self.base_url}/api/generate",
            json={
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                # Ollama takes sampling params under "options", not top-level.
                "options": {"temperature": temperature},
            },
            timeout=self.timeout,
        )
        resp.raise_for_status()
        return resp.json()["response"].strip()

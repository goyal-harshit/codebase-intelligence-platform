"""LLM access layer (Phase 6). Free/local providers only — Ollama and any
OpenAI-compatible local server (LM Studio, llama.cpp, vLLM, text-generation-webui)."""
from .ollama import LLMClient, OllamaClient
from .openai_compatible import OpenAICompatibleClient

__all__ = ["LLMClient", "OllamaClient", "OpenAICompatibleClient"]

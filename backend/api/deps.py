"""Lazily-constructed singleton service clients for dependency injection.

Construction is cheap and does NOT open connections or load models, so the API
starts fine with no backends running; failures surface only when an endpoint
actually uses a backend (and are turned into 503s there).
"""
from __future__ import annotations

from functools import lru_cache

from graph_db import ArcadeDBClient
from llm import LLMClient, OllamaClient, OpenAICompatibleClient
from llm import config as llm_config
from retrieval import QueryEngine
from vector_db import VectorStoreBuilder


@lru_cache
def get_graph_client() -> ArcadeDBClient:
    return ArcadeDBClient()


@lru_cache
def get_vector_store() -> VectorStoreBuilder:
    return VectorStoreBuilder()


def llm_provider() -> str:
    """The effective LLM provider (DB config override, else ``LLM_*`` env)."""
    return llm_config.effective_config()["provider"]


def get_llm() -> LLMClient:
    """Build the client from the effective config (free/local providers only).

    Not cached: a runtime ``PUT /api/v1/llm-config`` change must take effect on
    the next request. Construction is cheap and opens no connection.
    """
    cfg = llm_config.effective_config()
    if cfg["provider"] in {"openai_compatible", "openai", "openai-compatible"}:
        return OpenAICompatibleClient(
            base_url=cfg["base_url"], model=cfg["model"], api_key=cfg["api_key"] or None
        )
    return OllamaClient(base_url=cfg["base_url"], model=cfg["model"])


def get_query_engine() -> QueryEngine:
    # Not cached so a live LLM-config change is picked up; the graph and vector
    # clients it depends on stay cached (stable, no per-request config).
    return QueryEngine(get_graph_client(), get_vector_store(), get_llm())

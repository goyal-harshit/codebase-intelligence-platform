"""Lazily-constructed singleton service clients for dependency injection.

Construction is cheap and does NOT open connections or load models, so the API
starts fine with no backends running; failures surface only when an endpoint
actually uses a backend (and are turned into 503s there).
"""
from __future__ import annotations

from functools import lru_cache

from graph_db import ArcadeDBClient
from llm import OllamaClient
from retrieval import QueryEngine
from vector_db import VectorStoreBuilder


@lru_cache
def get_graph_client() -> ArcadeDBClient:
    return ArcadeDBClient()


@lru_cache
def get_vector_store() -> VectorStoreBuilder:
    return VectorStoreBuilder()


@lru_cache
def get_llm() -> OllamaClient:
    return OllamaClient()


@lru_cache
def get_query_engine() -> QueryEngine:
    return QueryEngine(get_graph_client(), get_vector_store(), get_llm())

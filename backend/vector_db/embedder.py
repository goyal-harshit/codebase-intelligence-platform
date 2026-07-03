"""Embedding backends.

``Embedder`` is a minimal protocol so the vector store can take any encoder —
the real one (sentence-transformers / BAAI/bge-small-en-v1.5) or a fake in
tests. The heavy import is deferred until the model is actually used.
"""
from __future__ import annotations

from typing import Protocol, Sequence, runtime_checkable


@runtime_checkable
class Embedder(Protocol):
    def encode(self, texts: Sequence[str]) -> list[list[float]]:
        """Return one L2-normalized embedding vector per input text."""
        ...


class SentenceTransformerEmbedder:
    DEFAULT_MODEL = "BAAI/bge-small-en-v1.5"

    def __init__(self, model_name: str = DEFAULT_MODEL) -> None:
        self.model_name = model_name
        self._model = None  # lazily loaded; first load downloads ~130MB

    def _load(self):
        if self._model is None:
            import os
            # Disable HF Hub network checks to drastically speed up model initialization
            os.environ["HF_HUB_OFFLINE"] = "1"
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self.model_name)
        return self._model

    def encode(self, texts: Sequence[str]) -> list[list[float]]:
        model = self._load()
        return model.encode(list(texts), normalize_embeddings=True).tolist()

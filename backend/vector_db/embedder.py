"""Embedding backends.

``Embedder`` is a minimal protocol so the vector store can take any encoder —
the real one (sentence-transformers / BAAI/bge-small-en-v1.5) or a fake in
tests. The heavy import is deferred until the model is actually used.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Protocol, Sequence, runtime_checkable


@runtime_checkable
class Embedder(Protocol):
    def encode(self, texts: Sequence[str]) -> list[list[float]]:
        """Return one L2-normalized embedding vector per input text."""
        ...


@lru_cache(maxsize=4)
def _load_model(model_name: str, max_tokens: int):
    """Load (and cache) a SentenceTransformer once per process.

    The torch import + weight load costs ~20s. Without caching, every ingest
    rebuilds a fresh embedder and re-pays it; the long-lived API/worker process
    should load the model once and reuse it across ingests. Keyed by model name
    (and ``max_tokens``) so a config change still picks up a fresh model.
    """
    import os
    # Disable HF Hub network checks to drastically speed up model initialization
    os.environ["HF_HUB_OFFLINE"] = "1"
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(model_name)
    # Encode cost scales with sequence length: a code entity whose body fills the
    # model's native 512-token window costs ~2.2x a 256-token one on CPU (the only
    # device available here). For *search* the signal lives in the name, signature,
    # docstring, and first lines — so capping the window is a near-free ~2x speedup
    # on the pipeline's slowest step. Tune via EMBED_MAX_TOKENS (e.g. 128 for demos).
    if max_tokens and max_tokens < model.max_seq_length:
        model.max_seq_length = max_tokens
    return model


class SentenceTransformerEmbedder:
    DEFAULT_MODEL = "BAAI/bge-small-en-v1.5"
    DEFAULT_MAX_TOKENS = 256

    def __init__(self, model_name: str = DEFAULT_MODEL, max_tokens: int | None = None) -> None:
        import os

        self.model_name = model_name
        if max_tokens is None:
            max_tokens = int(os.getenv("EMBED_MAX_TOKENS", self.DEFAULT_MAX_TOKENS))
        self.max_tokens = max_tokens

    def _load(self):
        # Shared across instances/ingests via the module-level cache.
        return _load_model(self.model_name, self.max_tokens)

    def encode(self, texts: Sequence[str]) -> list[list[float]]:
        model = self._load()
        # Explicit batch_size (sentence-transformers otherwise defaults to a
        # conservative 32) and no progress bar — the outer ingest loop already
        # reports progress per chunk-batch, so a second nested tqdm is just
        # per-call overhead repeated hundreds of times during a large ingest.
        return model.encode(
            list(texts), normalize_embeddings=True, batch_size=128, show_progress_bar=False,
        ).tolist()

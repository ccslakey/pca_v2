"""
Mockable embedding seam (local ONNX model via fastembed).

Embeddings are computed in-process by a small open model (settings.EMBED_MODEL,
BAAI/bge-small-en-v1.5: 384-dim, quantized ONNX, ~65 MB), so retrieval needs no
API key and has no rate limit or network dependency. The Docker image bakes the
model files in at build time (FASTEMBED_CACHE_PATH, HF_HUB_OFFLINE); elsewhere
the first call downloads them once. As with `llm.py`, the import and model load
are lazy and tests monkeypatch `embed` / `embed_query`, so nothing loads a model
until something actually embeds.

Each process holds one copy of the model (~225 MB resident), loaded on first use.
"""
from __future__ import annotations

import threading
from typing import Any

from django.conf import settings

_model: Any = None
_lock = threading.Lock()  # gunicorn runs threaded workers; load the model once


def _get_model() -> Any:
    global _model
    if _model is None:
        with _lock:
            if _model is None:
                from fastembed import TextEmbedding  # lazy: heavy import, only needed to embed

                _model = TextEmbedding(settings.EMBED_MODEL)
    return _model


def embed(texts: list[str], input_type: str = "document") -> list[list[float]]:
    """Embed a batch of texts. `input_type` is 'document' or 'query', routed to
    the model's passage / query encoders.

    `VECTOR_DIM` must match the model's output and MethodologyChunk.embedding;
    the check guards against swapping EMBED_MODEL without a migration.
    """
    model = _get_model()
    encode = model.query_embed if input_type == "query" else model.passage_embed
    vectors = [v.tolist() for v in encode(texts)]
    if vectors and len(vectors[0]) != settings.VECTOR_DIM:
        raise ValueError(
            f"{settings.EMBED_MODEL} returned dim {len(vectors[0])}, expected {settings.VECTOR_DIM} "
            f"(VECTOR_DIM / MethodologyChunk.embedding). Reindex after aligning them."
        )
    return vectors


def embed_query(text: str) -> list[float]:
    return embed([text], input_type="query")[0]

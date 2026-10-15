from __future__ import annotations

import os
import threading
from typing import Any

from django.conf import settings

_model: Any = None
_lock = threading.Lock()


def _get_model() -> Any:
    global _model
    if _model is None:
        with _lock:
            if _model is None:
                # Official ONNX Runtime builds send usage telemetry to Microsoft;
                # it must be off before the runtime initializes (the Docker image
                # also sets this).
                os.environ.setdefault("ORT_DISABLE_TELEMETRY", "1")
                from fastembed import TextEmbedding

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

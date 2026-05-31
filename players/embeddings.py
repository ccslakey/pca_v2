"""
Mockable embedding seam (Voyage AI).

Anthropic has no embeddings endpoint, so the methodology RAG uses Voyage —
Anthropic's recommended embeddings partner. As with `llm.py`, the SDK import
and client are lazy and tests monkeypatch `embed` / `embed_query`, so nothing
needs a key until something actually embeds.

Voyage distinguishes `input_type`: documents are embedded with one prefix and
queries with another, which improves retrieval. We pass it through accordingly.
"""
from __future__ import annotations

from typing import Any

from django.conf import settings

_client: Any = None


def _get_client() -> Any:
    global _client
    if _client is None:
        import voyageai  # lazy: optional dependency, only needed when indexing/searching

        _client = voyageai.Client(api_key=settings.VOYAGE_API_KEY)
    return _client


def embed(texts: list[str], input_type: str = "document") -> list[list[float]]:
    """Embed a batch of texts. `input_type` is 'document' or 'query'.

    The installed voyageai SDK pins output to the model's default dimension
    (voyage-3.5-lite → 1024), which matches MethodologyChunk.embedding /
    settings.VECTOR_DIM. `_assert_dim` guards against a model/field mismatch.
    """
    result = _get_client().embed(texts, model=settings.EMBED_MODEL, input_type=input_type)
    vectors = result.embeddings
    if vectors and len(vectors[0]) != settings.VECTOR_DIM:
        raise ValueError(
            f"{settings.EMBED_MODEL} returned dim {len(vectors[0])}, expected {settings.VECTOR_DIM} "
            f"(VECTOR_DIM / MethodologyChunk.embedding). Reindex after aligning them."
        )
    return vectors


def embed_query(text: str) -> list[float]:
    return embed([text], input_type="query")[0]

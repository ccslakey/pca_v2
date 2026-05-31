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
    """Embed a batch of texts. `input_type` is 'document' or 'query'."""
    result = _get_client().embed(
        texts,
        model=settings.EMBED_MODEL,
        input_type=input_type,
        output_dimension=settings.VECTOR_DIM,
    )
    return result.embeddings


def embed_query(text: str) -> list[float]:
    return embed([text], input_type="query")[0]

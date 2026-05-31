"""
Semantic retrieval over the methodology corpus (step 3).

`search_methodology` embeds the query with Voyage and ranks stored chunks by
cosine distance in pgvector. It degrades to an empty result — never an error —
when RAG is disabled, the corpus is unindexed, or the embedding call fails, so
the narrative agent can call it safely regardless of configuration.
"""
from __future__ import annotations

from typing import Any

from django.conf import settings
from pgvector.django import CosineDistance

from . import embeddings
from .models import MethodologyChunk


def search_methodology(query: str, k: int = 3) -> list[dict[str, Any]]:
    if not query or not getattr(settings, "RAG_ENABLED", False):
        return []
    if not MethodologyChunk.objects.exists():
        return []
    try:
        qvec = embeddings.embed_query(query)
    except Exception:
        return []

    rows = (
        MethodologyChunk.objects
        .annotate(distance=CosineDistance("embedding", qvec))
        .order_by("distance")[:k]
    )
    return [
        {
            "slug": c.slug,
            "title": c.title,
            "content": c.content,
            "score": round(1.0 - float(c.distance), 3),  # cosine similarity, for display
        }
        for c in rows
    ]

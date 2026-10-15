"""
Semantic retrieval over the methodology corpus (step 3).

`search_methodology` embeds the query with the local model and ranks stored
chunks by cosine distance in pgvector. It degrades to an empty result — never an
error — when RAG is disabled, the corpus is unindexed, or embedding fails, so the
narrative agent can call it safely regardless of configuration. An embedding
failure is logged at ERROR (and so reported to Sentry), never swallowed silently.
"""
from __future__ import annotations

import hashlib
import logging
from typing import Any

from django.conf import settings
from django.core.cache import cache
from pgvector.django import CosineDistance

from . import embeddings
from .models import MethodologyChunk

logger = logging.getLogger(__name__)

_CACHE_TTL = 86_400  # results are static between re-indexes


def search_methodology(query: str, k: int = 3) -> list[dict[str, Any]]:
    if not query or not getattr(settings, "RAG_ENABLED", False):
        return []
    if not MethodologyChunk.objects.exists():
        return []

    # Cache by query so an interactive surface (metric explainers) skips the
    # embed + KNN on repeat views. Hash the query so the key is memcached-safe
    # (no spaces / length limits). Bump the version when the embedding model changes.
    digest = hashlib.md5(f"{k}:{query.strip().lower()}".encode()).hexdigest()
    cache_key = f"rag:v2:{digest}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    try:
        qvec = embeddings.embed_query(query)
    except Exception:
        logger.exception("methodology search: embedding failed for query %r", query)
        return []

    rows = (
        MethodologyChunk.objects
        .annotate(distance=CosineDistance("embedding", qvec))
        .order_by("distance")[:k]
    )
    results = [
        {
            "slug": c.slug,
            "title": c.title,
            "content": c.content,
            "score": round(1.0 - float(c.distance), 3),  # cosine similarity, for display
        }
        for c in rows
    ]
    cache.set(cache_key, results, _CACHE_TTL)
    return results

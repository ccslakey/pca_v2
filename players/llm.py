"""
Thin, mockable wrapper around the Anthropic SDK.

All Claude calls in this project funnel through here so that:
  * the SDK import and client construction are lazy — nothing touches the
    network (or requires a key) unless a feature actually calls out;
  * tests monkeypatch a single seam (`complete_text` / `complete`) instead of
    the SDK internals;
  * prompt caching is applied in one place.

The client is only built when `settings.ANTHROPIC_API_KEY` is set. Callers are
expected to gate on `settings.LLM_ENABLED` before reaching this module.
"""
from __future__ import annotations

from typing import Any

from django.conf import settings

_client: Any = None


def _get_client() -> Any:
    global _client
    if _client is None:
        from anthropic import Anthropic

        _client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    return _client


def complete(
    system: str,
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]] | None = None,
    max_tokens: int | None = None,
    model: str | None = None,
) -> Any:
    kwargs: dict[str, Any] = {
        "model": model or settings.NARRATIVE_MODEL,
        "max_tokens": max_tokens or settings.NARRATIVE_MAX_TOKENS,
        "system": [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
        "messages": messages,
    }
    if tools:
        kwargs["tools"] = tools
    return _get_client().messages.create(**kwargs)


def complete_text(system: str, user: str, max_tokens: int | None = None, model: str | None = None) -> str:
    resp = complete(system, [{"role": "user", "content": user}], max_tokens=max_tokens, model=model)
    return "".join(block.text for block in resp.content if getattr(block, "type", None) == "text").strip()

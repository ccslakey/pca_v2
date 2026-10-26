"""Prototype: chat tools for the Compare page (CopilotKit). Throwaway code.

Both chat variants call the same read-only tools: the narrative agent's TOOLS
plus find_player. The `agui` variant also runs its own Anthropic loop here.
"""
from __future__ import annotations

import json
import logging
import re
import time
import uuid
from collections.abc import Iterator
from typing import Any

from django.conf import settings
from rest_framework import filters
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory

from .narrative import _accumulate_allowed, verify_numbers
from .narrative_tools import TOOLS, run_tool

logger = logging.getLogger(__name__)

FIND_PLAYER = {
    "name": "find_player",
    "description": "Resolve a player name (or part of one) to Baseball Reference ids. "
    "Returns up to 8 matches with years active and primary position. Call this before "
    "any tool or page action that needs a player id; never guess ids.",
    "input_schema": {
        "type": "object",
        "properties": {"query": {"type": "string", "description": "Name to search, e.g. 'Babe Ruth'."}},
        "required": ["query"],
    },
}
COPILOT_TOOLS: list[dict[str, Any]] = [*TOOLS, FIND_PLAYER]
_BY_NAME = {t["name"]: t for t in COPILOT_TOOLS}
_MAX_ARG_LEN = 200


def validate_call(name: Any, args: Any) -> str | None:
    tool = _BY_NAME.get(name) if isinstance(name, str) else None
    if tool is None:
        return f"unknown tool {name!r}"
    if not isinstance(args, dict):
        return "args must be an object"
    props = tool["input_schema"]["properties"]
    extra = set(args) - set(props)
    if extra:
        return f"unexpected args {sorted(extra)}"
    for key in tool["input_schema"]["required"]:
        val = args.get(key)
        if not isinstance(val, str) or not val.strip() or len(val) > _MAX_ARG_LEN:
            return f"{key} must be a non-empty string under {_MAX_ARG_LEN} chars"
    return None


def find_player(query: str) -> dict[str, Any]:
    from .views import PlayerViewSet

    # Run the exact SearchFilter the /api/players/?search= endpoint uses.
    request = Request(APIRequestFactory().get("/", {"search": query}))
    qs = filters.SearchFilter().filter_queryset(request, PlayerViewSet.queryset, PlayerViewSet)
    return {
        "matches": [
            {
                "player_id": p.bbref_id,
                "name": f"{p.first_name} {p.last_name}",
                "years": f"{p.debut.year if p.debut else '?'}-{p.final_game.year if p.final_game else '?'}",
                "primary_position": p.primary_position,
            }
            for p in qs[:8]
        ]
    }


def run_copilot_tool(name: str, args: dict[str, Any], facts_cache: dict[str, Any]) -> dict[str, Any]:
    if name == "find_player":
        return find_player(args["query"])
    return run_tool(name, args, facts_cache)


# ---------------------------------------------------------------------------
# agui variant: an AG-UI endpoint that runs its own Anthropic tool loop
# ---------------------------------------------------------------------------

SYSTEM = (
    "You are the chat assistant on a baseball career-comparison page. The page's current "
    "compare state is in the context below. Change it only with the page tools "
    "(setPlayers, addPlayer, removePlayer, changeMetric, changeXMode). Resolve names "
    "with find_player first; never guess ids. Every statistic you state must come from a "
    "tool result in this conversation, so call a data tool before answering a stats "
    "question and never quote numbers from memory. Answer in one to three plain sentences. "
    "Do not mention player ids."
)
_MAX_STEPS = 8
_SERVER_TOOLS = {t["name"] for t in COPILOT_TOOLS}
_BBREF_ID = re.compile(r"\b[a-z][a-z'.]{1,7}\d{2}\b")


def _sse(event: dict[str, Any]) -> str:
    return f"data: {json.dumps(event)}\n\n"


def _to_anthropic(messages: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, str]]:
    """AG-UI messages -> Anthropic messages. Also returns tool_call_id -> tool name."""
    out: list[dict[str, Any]] = []
    names: dict[str, str] = {}
    answered: set[str] = set()

    def push(role: str, blocks: list[dict[str, Any]]) -> None:
        if out and out[-1]["role"] == role:
            out[-1]["content"].extend(blocks)
        else:
            out.append({"role": role, "content": blocks})

    for m in messages:
        role = m.get("role")
        if role == "user":
            content = m.get("content")
            text = content if isinstance(content, str) else " ".join(
                p.get("text", "") for p in content or [] if isinstance(p, dict)
            )
            push("user", [{"type": "text", "text": text or "(empty)"}])
        elif role == "assistant":
            blocks: list[dict[str, Any]] = []
            if m.get("content"):
                blocks.append({"type": "text", "text": m["content"]})
            for tc in m.get("toolCalls") or []:
                names[tc["id"]] = tc["function"]["name"]
                try:
                    args = json.loads(tc["function"].get("arguments") or "{}")
                except json.JSONDecodeError:
                    args = {}
                blocks.append({"type": "tool_use", "id": tc["id"], "name": tc["function"]["name"], "input": args})
            if blocks:
                push("assistant", blocks)
        elif role == "tool":
            answered.add(m["toolCallId"])
            content = m.get("content")
            push("user", [{
                "type": "tool_result",
                "tool_use_id": m["toolCallId"],
                "content": content if isinstance(content, str) else json.dumps(content),
            }])
    # A tool_use with no result (stopped run) is a 400, so close it out.
    missing = [tid for tid in names if tid not in answered]
    if missing:
        push("user", [{"type": "tool_result", "tool_use_id": t, "content": "no result"} for t in missing])
    return out, names


def _allowed_from_history(messages: list[dict[str, Any]], names: dict[str, str]) -> set[float]:
    allowed: set[float] = set()
    for m in messages:
        if m.get("role") == "tool" and names.get(m.get("toolCallId", "")) in _SERVER_TOOLS:
            try:
                _accumulate_allowed(json.loads(m["content"]), allowed)
            except (TypeError, ValueError):
                pass
    return allowed


def untraced_numbers(text: str, allowed: set[float]) -> list[str]:
    return verify_numbers(_BBREF_ID.sub("", text), allowed)


def run_agui(body: dict[str, Any]) -> Iterator[str]:
    thread_id, run_id = body.get("threadId", "t"), body.get("runId", "r")
    yield _sse({"type": "RUN_STARTED", "threadId": thread_id, "runId": run_id})

    def say(text: str) -> Iterator[str]:
        mid = str(uuid.uuid4())
        yield _sse({"type": "TEXT_MESSAGE_START", "messageId": mid, "role": "assistant"})
        yield _sse({"type": "TEXT_MESSAGE_CONTENT", "messageId": mid, "delta": text})
        yield _sse({"type": "TEXT_MESSAGE_END", "messageId": mid})

    if not settings.LLM_ENABLED:
        yield from say("Chat is unavailable: this server has no ANTHROPIC_API_KEY configured.")
        yield _sse({"type": "RUN_FINISHED", "threadId": thread_id, "runId": run_id})
        return

    from .llm import _get_client

    raw = body.get("messages") or []
    messages, names = _to_anthropic(raw)
    allowed = _allowed_from_history(raw, names)
    frontend_tools = [
        {"name": t["name"], "description": t.get("description", ""),
         "input_schema": t.get("parameters") or {"type": "object", "properties": {}}}
        for t in body.get("tools") or [] if t.get("name") not in _SERVER_TOOLS
    ]
    tools = [*COPILOT_TOOLS, *frontend_tools]
    context = "\n".join(f"- {c.get('description')}: {c.get('value')}" for c in body.get("context") or [])
    system = [{"type": "text", "text": SYSTEM, "cache_control": {"type": "ephemeral"}}]
    if context:
        system.append({"type": "text", "text": "Page context:\n" + context})

    facts_cache: dict[str, Any] = {}
    stats: dict[str, Any] = {"steps": 0, "tools": [], "ttft_ms": None, "flagged": [], "repaired": False}
    started = time.monotonic()
    try:
        for _ in range(_MAX_STEPS):
            stats["steps"] += 1
            mid = str(uuid.uuid4())
            opened = False
            with _get_client().messages.stream(
                model=settings.COPILOT_MODEL, max_tokens=2048, system=system,
                messages=messages, tools=tools, output_config={"effort": "low"},
            ) as stream:
                if not settings.COPILOT_VERIFY:
                    for delta in stream.text_stream:
                        if not opened:
                            opened = True
                            stats["ttft_ms"] = stats["ttft_ms"] or int((time.monotonic() - started) * 1000)
                            yield _sse({"type": "TEXT_MESSAGE_START", "messageId": mid, "role": "assistant"})
                        yield _sse({"type": "TEXT_MESSAGE_CONTENT", "messageId": mid, "delta": delta})
                final = stream.get_final_message()
            text = "".join(b.text for b in final.content if b.type == "text").strip()
            tool_uses = [b for b in final.content if b.type == "tool_use"]
            if settings.COPILOT_VERIFY and text:
                bad = untraced_numbers(text, allowed)
                if bad and not tool_uses and not stats["repaired"]:
                    stats["repaired"] = True
                    messages.append({"role": "assistant", "content": final.content})
                    messages.append({"role": "user", "content": (
                        f"These numbers are not in any tool result: {bad}. Rewrite the answer using "
                        "only numbers from tool results; call a tool if you need more data.")})
                    continue
                if bad:
                    stats["flagged"] = bad
                    text += f"\n\n(Unverified: {', '.join(bad)} not found in the data I looked up.)"
                opened = True
                stats["ttft_ms"] = stats["ttft_ms"] or int((time.monotonic() - started) * 1000)
                yield _sse({"type": "TEXT_MESSAGE_START", "messageId": mid, "role": "assistant"})
                yield _sse({"type": "TEXT_MESSAGE_CONTENT", "messageId": mid, "delta": text})
            if opened:
                yield _sse({"type": "TEXT_MESSAGE_END", "messageId": mid})
            if not tool_uses:
                break

            messages.append({"role": "assistant", "content": final.content})
            results, waiting_on_page = [], False
            for tu in tool_uses:
                stats["tools"].append(tu.name)
                yield _sse({"type": "TOOL_CALL_START", "toolCallId": tu.id, "toolCallName": tu.name,
                            "parentMessageId": mid})
                yield _sse({"type": "TOOL_CALL_ARGS", "toolCallId": tu.id, "delta": json.dumps(tu.input)})
                yield _sse({"type": "TOOL_CALL_END", "toolCallId": tu.id})
                if tu.name not in _SERVER_TOOLS:
                    waiting_on_page = True
                    continue
                err = validate_call(tu.name, tu.input)
                out = {"error": err} if err else run_copilot_tool(tu.name, tu.input, facts_cache)
                _accumulate_allowed(out, allowed)
                content = json.dumps(out)
                results.append({"type": "tool_result", "tool_use_id": tu.id, "content": content})
                yield _sse({"type": "TOOL_CALL_RESULT", "messageId": str(uuid.uuid4()),
                            "toolCallId": tu.id, "content": content, "role": "tool"})
            if waiting_on_page:
                break  # CopilotKit runs the page tools, then starts a follow-up run
            messages.append({"role": "user", "content": results})
    except Exception as exc:  # noqa: BLE001 - prototype: surface any failure as a run error
        logger.exception("copilot agui run failed")
        yield _sse({"type": "RUN_ERROR", "message": f"Chat failed: {type(exc).__name__}"})
        return
    stats["total_ms"] = int((time.monotonic() - started) * 1000)
    logger.info("copilot agui run %s", stats)
    yield _sse({"type": "RUN_FINISHED", "threadId": thread_id, "runId": run_id})

"""
Function-calling tools for the narrative agent (step 2).

Instead of pre-stuffing every fact into the prompt, the model *requests* what
it needs through these typed tools. Each tool wraps data we already compute in
`narrative.build_facts` and only ever returns real, stored statistics — the
model never sees a SQL string and cannot query anything but these four shapes
for a valid player id. The data a tool actually returns becomes the ground
truth the final narrative is verified against.
"""
from __future__ import annotations

from typing import Any

# Anthropic tool schema. player_id is the only input — the model identifies a
# player, the executor resolves and validates it.
_PLAYER_ARG = {
    "type": "object",
    "properties": {
        "player_id": {
            "type": "string",
            "description": "Baseball Reference player id, e.g. 'ruthba01'.",
        }
    },
    "required": ["player_id"],
}

TOOLS: list[dict[str, Any]] = [
    {
        "name": "get_career_totals",
        "description": "Career aggregate stats and bio for a player: WAR, HR, batting average, "
        "ERA, strikeouts, peak season, primary position, and years active.",
        "input_schema": _PLAYER_ARG,
    },
    {
        "name": "get_season_log",
        "description": "Season-by-season stat lines (year, age, WAR, and key rate/counting stats).",
        "input_schema": _PLAYER_ARG,
    },
    {
        "name": "get_awards",
        "description": "Awards and honors won by the player, with counts and the years won.",
        "input_schema": _PLAYER_ARG,
    },
    {
        "name": "get_similar_players",
        "description": "Names of the most statistically similar players, for context/comparison.",
        "input_schema": _PLAYER_ARG,
    },
    {
        "name": "search_methodology",
        "description": "Search the site's methodology documentation to correctly explain a metric "
        "or method (e.g. what OPS+ or WAR means here, how similarity is computed). Use this for "
        "definitions and wording — not for the player's own statistics.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "What to look up, e.g. 'how is OPS+ calculated'.",
                }
            },
            "required": ["query"],
        },
    },
]


def _facts_for(player_id: str, facts_cache: dict[str, Any]) -> dict[str, Any] | None:
    """Resolve and cache a player's facts within a single agent run. Returns
    None for an unknown id so the tool can report it back to the model."""
    if player_id not in facts_cache:
        from .models import Player  # lazy to avoid an import cycle with narrative
        from .narrative import build_facts

        player = Player.objects.filter(pk=player_id).first()
        facts_cache[player_id] = build_facts(player) if player else None
    return facts_cache[player_id]


def run_tool(name: str, args: dict[str, Any], facts_cache: dict[str, Any]) -> dict[str, Any]:
    """Execute one tool call. Returns a JSON-serializable dict (an `error` key
    when the player id is unknown or the tool name is unrecognized)."""
    # Methodology search is not player-scoped — handle it before resolving facts.
    if name == "search_methodology":
        from . import rag

        return {"results": rag.search_methodology(args.get("query", ""))}

    facts = _facts_for(args.get("player_id", ""), facts_cache)
    if facts is None:
        return {"error": f"No player found with id {args.get('player_id')!r}."}

    if name == "get_career_totals":
        return {
            "bio": facts["bio"],
            "batting": facts.get("batting"),
            "pitching": facts.get("pitching"),
            "career_war_total": facts["career_war_total"],
        }
    if name == "get_season_log":
        return {
            "batting_log": facts.get("batting_log"),
            "pitching_log": facts.get("pitching_log"),
        }
    if name == "get_awards":
        return {"awards": facts["awards"]}
    if name == "get_similar_players":
        return {"similar": facts["similar"]}
    return {"error": f"Unknown tool {name!r}."}

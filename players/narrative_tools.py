from __future__ import annotations

from typing import Any

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
    if player_id not in facts_cache:
        from .models import Player  # lazy to avoid an import cycle with narrative
        from .narrative import build_facts

        player = Player.objects.filter(pk=player_id).first()
        facts_cache[player_id] = build_facts(player) if player else None
    return facts_cache[player_id]


def run_tool(name: str, args: dict[str, Any], facts_cache: dict[str, Any]) -> dict[str, Any]:
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

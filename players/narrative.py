"""
Grounded career-narrative generation.

The contract: every number the model emits must trace back to this player's
real data. `build_facts` assembles the only information the model ever sees;
`verify_numbers` checks the output against the set of numbers that data allows;
`render_template` is a deterministic, number-safe fallback that is correct by
construction. `generate_narrative` ties them together with a generate → verify
→ repair → fall-back loop.

This mirrors the shape of `similarity.py`: pure helpers plus a cached entry
point, no view logic here.
"""
from __future__ import annotations

import json
import re
from typing import Any

from django.conf import settings
from django.utils import timezone

from . import llm
from .models import Player
from .similarity import similar_players

# ---------------------------------------------------------------------------
# Fact assembly — the only thing the model is allowed to see
# ---------------------------------------------------------------------------

_BAT_FIELDS = ("year", "war", "home_runs", "batting_avg", "ops", "ops_plus", "plate_appearances", "hits", "at_bats")
_PIT_FIELDS = ("year", "war", "era", "era_plus", "strikeouts", "ip_outs", "earned_runs", "wins", "losses", "saves")


def _round(v: float | None, n: int) -> float | None:
    return round(float(v), n) if v is not None else None


def _peak(seasons: list[dict]) -> tuple[float | None, int | None]:
    best = max((s for s in seasons if s.get("war") is not None), key=lambda s: s["war"], default=None)
    return (round(best["war"], 1), best["year"]) if best else (None, None)


def build_facts(player: Player) -> dict[str, Any]:
    """Assemble grounded career facts. Every number here defines what the
    narrative is permitted to say (see `allowed_numbers`)."""
    bat = list(player.batting_seasons.values(*_BAT_FIELDS).order_by("year"))
    pit = list(player.pitching_seasons.values(*_PIT_FIELDS).order_by("year"))
    awards = list(player.awards.values("year", "kind"))

    birth_year = player.birth_date.year if player.birth_date else None
    season_years = sorted(s["year"] for s in (bat + pit))
    debut_year = player.debut.year if player.debut else (season_years[0] if season_years else None)
    final_year = player.final_game.year if player.final_game else (season_years[-1] if season_years else None)

    def age(year: int) -> int | None:
        return year - birth_year if birth_year else None

    facts: dict[str, Any] = {
        "bio": {
            "name": f"{player.first_name} {player.last_name}",
            "primary_position": player.primary_position,
            "bats": player.bats,
            "throws": player.throws,
            "debut_year": debut_year,
            "final_year": final_year,
            "birth_year": birth_year,
            "seasons_played": len({s["year"] for s in (bat + pit)}),
        },
        "career_war_total": round(
            sum(s["war"] or 0 for s in bat) + sum(s["war"] or 0 for s in pit), 1
        ),
        "awards": {},
        "similar": [],
    }

    if bat:
        ab = sum(s["at_bats"] or 0 for s in bat)
        hits = sum(s["hits"] or 0 for s in bat)
        pa = sum(s["plate_appearances"] or 0 for s in bat)
        ops_num = sum((s["ops_plus"] or 0) * (s["plate_appearances"] or 0) for s in bat if s["ops_plus"] is not None)
        peak_war, peak_year = _peak(bat)
        facts["batting"] = {
            "career_war": round(sum(s["war"] or 0 for s in bat), 1),
            "peak_war": peak_war,
            "peak_year": peak_year,
            "career_hr": sum(s["home_runs"] or 0 for s in bat),
            "career_hits": hits,
            "career_avg": round(hits / ab, 3) if ab else None,
            "career_ops_plus": round(ops_num / pa) if pa else None,
        }
        facts["batting_log"] = [
            {
                "year": s["year"],
                "age": age(s["year"]),
                "war": _round(s["war"], 1),
                "hr": s["home_runs"],
                "avg": _round(s["batting_avg"], 3),
                "ops": _round(s["ops"], 3),
                "ops_plus": s["ops_plus"],
            }
            for s in bat
        ]

    if pit:
        ip_outs = sum(s["ip_outs"] or 0 for s in pit)
        er = sum(s["earned_runs"] or 0 for s in pit)
        era_num = sum((s["era_plus"] or 0) * (s["ip_outs"] or 0) for s in pit if s["era_plus"] is not None)
        peak_war, peak_year = _peak(pit)
        facts["pitching"] = {
            "career_war": round(sum(s["war"] or 0 for s in pit), 1),
            "peak_war": peak_war,
            "peak_year": peak_year,
            "career_wins": sum(s["wins"] or 0 for s in pit),
            "career_losses": sum(s["losses"] or 0 for s in pit),
            "career_so": sum(s["strikeouts"] or 0 for s in pit),
            "career_era": round(er * 27.0 / ip_outs, 2) if ip_outs else None,
            "career_era_plus": round(era_num / ip_outs) if ip_outs else None,
        }
        facts["pitching_log"] = [
            {
                "year": s["year"],
                "age": age(s["year"]),
                "war": _round(s["war"], 1),
                "era": _round(s["era"], 2),
                "era_plus": s["era_plus"],
                "so": s["strikeouts"],
            }
            for s in pit
        ]

    by_kind: dict[str, list[int]] = {}
    for a in awards:
        by_kind.setdefault(a["kind"], []).append(a["year"])
    facts["awards"] = {k: {"count": len(v), "years": sorted(v)} for k, v in by_kind.items()}

    sims = similar_players(player)
    facts["similar"] = [
        f"{p['first_name']} {p['last_name']}" for p in (sims.get("batters", []) + sims.get("pitchers", []))[:4]
    ]

    return facts


# ---------------------------------------------------------------------------
# Verification — the anti-hallucination check
# ---------------------------------------------------------------------------

# Comma-grouped (1,500) | decimal (2.31, .342) | bare integer (714)
_NUM_RE = re.compile(r"\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+\.\d+|\.\d+|\d+")
# Fixed reference points that are domain constants, not player facts.
_DOMAIN_SAFE = {100.0}  # league-average baseline for OPS+ / ERA+


def _parse_token(tok: str) -> tuple[float, int]:
    """Return (value, decimal_places) for a matched numeric token."""
    clean = tok.replace(",", "")
    decimals = len(clean.split(".")[1]) if "." in clean else 0
    return float(clean), decimals


def _collect_numbers(obj: Any, out: set[float]) -> None:
    if isinstance(obj, bool) or obj is None:
        return
    if isinstance(obj, (int, float)):
        out.add(float(obj))
    elif isinstance(obj, dict):
        for v in obj.values():
            _collect_numbers(v, out)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            _collect_numbers(v, out)


def allowed_numbers(facts: dict[str, Any]) -> set[float]:
    """Every number the narrative may mention: all values in `facts`, plus any
    year the player was active (safe to reference even if no stat line cites it)."""
    out: set[float] = set()
    _collect_numbers(facts, out)
    bio = facts.get("bio", {})
    d, f = bio.get("debut_year"), bio.get("final_year")
    if d and f:
        out.update(float(y) for y in range(int(d), int(f) + 1))
    return out


def verify_numbers(text: str, allowed: set[float]) -> list[str]:
    """Return numeric tokens in `text` that are NOT supported by `allowed`.
    An empty list means the text is fully grounded.

    A token matches if some allowed value rounds — at the token's own decimal
    precision — to the token. So ".342" matches 0.342, ".34" also matches
    0.342 (the model rounded), but ".350" matches nothing and is flagged."""
    allowed_all = allowed | _DOMAIN_SAFE
    bad: list[str] = []
    for tok in _NUM_RE.findall(text):
        val, decimals = _parse_token(tok)
        if any(abs(round(a, decimals) - val) < 5e-4 for a in allowed_all):
            continue
        bad.append(tok)
    return bad


# ---------------------------------------------------------------------------
# Deterministic fallback — correct by construction
# ---------------------------------------------------------------------------

_POS_NAME = {
    "C": "catcher", "1B": "first baseman", "2B": "second baseman", "3B": "third baseman",
    "SS": "shortstop", "LF": "left fielder", "CF": "center fielder", "RF": "right fielder",
    "DH": "designated hitter", "P": "pitcher",
}
_AWARD_LABEL = {
    "mvp": "MVP", "cy": "Cy Young", "roty": "Rookie of the Year", "gg": "Gold Glove",
    "ss": "Silver Slugger", "ws": "World Series title", "asg": "All-Star selection",
}


def render_template(facts: dict[str, Any]) -> str:
    """Number-safe narrative built straight from facts — every figure here is by
    definition in `allowed_numbers(facts)`, so it always passes verification."""
    bio = facts["bio"]
    name = bio["name"]
    pos = _POS_NAME.get(bio.get("primary_position") or "", "player")
    parts: list[str] = []

    span = ""
    if bio.get("debut_year") and bio.get("final_year"):
        span = f" from {bio['debut_year']} to {bio['final_year']}"
    parts.append(f"{name} was a {pos} who played {bio['seasons_played']} seasons{span}.")

    bat = facts.get("batting")
    if bat and bat.get("career_war") is not None:
        clause = f"He compiled {bat['career_war']} WAR"
        if bat.get("career_hr"):
            clause += f" with {bat['career_hr']} home runs"
        if bat.get("career_avg") is not None:
            clause += f" and a {bat['career_avg']:.3f} average"
        if bat.get("peak_war") and bat.get("peak_year"):
            clause += f", peaking at {bat['peak_war']} WAR in {bat['peak_year']}"
        parts.append(clause + ".")

    pit = facts.get("pitching")
    if pit and pit.get("career_war") is not None and not bat:
        clause = f"He posted {pit['career_war']} WAR"
        if pit.get("career_era") is not None:
            clause += f" with a {pit['career_era']} ERA"
        if pit.get("career_so"):
            clause += f" and {pit['career_so']} strikeouts"
        if pit.get("peak_war") and pit.get("peak_year"):
            clause += f", peaking at {pit['peak_war']} WAR in {pit['peak_year']}"
        parts.append(clause + ".")

    awards = facts.get("awards", {})
    honors = [
        f"{awards[k]['count']} {label}{'s' if awards[k]['count'] != 1 else ''}"
        for k, label in _AWARD_LABEL.items()
        if k in awards
    ]
    if honors:
        parts.append("Career honors include " + ", ".join(honors) + ".")

    return " ".join(parts)


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

_RULES = (
    "Rules:\n"
    "- Use ONLY numbers from the player's actual data. Never invent, estimate, "
    "or approximate a figure.\n"
    "- Do not round to 'over 500' style approximations — cite the exact figures.\n"
    "- Refer to standout seasons by their year.\n"
    "- Be plain and direct. No hype, no fabricated narrative detail."
)

SYSTEM_PROMPT = (
    "You are a baseball analyst writing a concise, factual scouting summary of a "
    "player's career. You will be given a JSON object of that player's real "
    "statistics. Write 2-3 sentences.\n\n" + _RULES
)

SYSTEM_PROMPT_TOOLS = (
    "You are a baseball analyst writing a concise, factual scouting summary of a "
    "player's career. First call the provided tools to retrieve that player's "
    "statistics, then write 2-3 sentences. Call get_career_totals at minimum; "
    "call get_season_log, get_awards, or get_similar_players if they add value. "
    "If you mention a metric like OPS+ or WAR, you may call search_methodology to "
    "describe it accurately in the project's own terms.\n\n" + _RULES
)

_MAX_TOOL_ITERATIONS = 5


def _result(text: str, source: str, model: str | None, flagged: list[str] | None = None) -> dict[str, Any]:
    return {
        "text": text,
        "source": source,          # "llm" | "template"
        "verified": True,          # we never serve an unverified number
        "model": model,
        "flagged": flagged or [],  # numbers the LLM tried to use that we rejected
        "generated_at": timezone.now().isoformat(),
    }


def generate_narrative(player: Player) -> dict[str, Any]:
    """Grounded career summary. Dispatches to the tool-using agent or the
    single-shot path, and always degrades to the deterministic template when
    the LLM is disabled, errors, or fails verification."""
    facts = build_facts(player)

    if not getattr(settings, "LLM_ENABLED", False):
        return _result(render_template(facts), "template", None)

    try:
        if getattr(settings, "NARRATIVE_USE_TOOLS", True):
            return _generate_agentic(player, facts)
        return _generate_single_shot(facts)
    except Exception:
        # Any API/SDK failure degrades to the always-correct template.
        return _result(render_template(facts), "template", None)


def _generate_single_shot(facts: dict[str, Any]) -> dict[str, Any]:
    """Step 1: hand the model the full facts payload in one call."""
    allowed = allowed_numbers(facts)
    user = json.dumps(facts)
    text = llm.complete_text(SYSTEM_PROMPT, user)
    bad = verify_numbers(text, allowed)
    if bad:
        repair = (
            f"{user}\n\nYour previous draft used these numbers, which are NOT in "
            f"the data and must be removed or corrected: {bad}"
        )
        text = llm.complete_text(SYSTEM_PROMPT, repair)
        bad = verify_numbers(text, allowed)
    if bad:
        return _result(render_template(facts), "template", None, flagged=bad)
    return _result(text, "llm", settings.NARRATIVE_MODEL)


def _collect_string_numbers(obj: Any, allowed: set[float]) -> None:
    """Numbers embedded in returned *text* (e.g. methodology prose) are also
    grounded — they come from our own published docs — so trust them too."""
    if isinstance(obj, str):
        for tok in _NUM_RE.findall(obj):
            allowed.add(_parse_token(tok)[0])
    elif isinstance(obj, dict):
        for v in obj.values():
            _collect_string_numbers(v, allowed)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            _collect_string_numbers(v, allowed)


def _accumulate_allowed(out: dict[str, Any], allowed: set[float]) -> None:
    """Fold a tool result's numbers into the allowed set — both numeric fields
    and numbers appearing in returned text. A bio block also makes every year
    the player was active safe to mention."""
    _collect_numbers(out, allowed)
    _collect_string_numbers(out, allowed)
    bio = out.get("bio") if isinstance(out, dict) else None
    if bio and bio.get("debut_year") and bio.get("final_year"):
        allowed.update(float(y) for y in range(int(bio["debut_year"]), int(bio["final_year"]) + 1))


def _text_of(content: list) -> str:
    return "".join(b.text for b in content if getattr(b, "type", None) == "text").strip()


def _generate_agentic(player: Player, facts: dict[str, Any]) -> dict[str, Any]:
    """Step 2: the model gathers its own facts via tool calls. The narrative is
    verified against the union of data the tools actually returned — if the
    agent cites a stat it never retrieved, that number is flagged."""
    from . import narrative_tools

    facts_cache: dict[str, Any] = {}
    allowed: set[float] = set()
    messages: list[dict[str, Any]] = [
        {
            "role": "user",
            "content": f"Write a scouting summary of the player with id "
            f"'{player.bbref_id}'. Use the tools to gather their statistics first.",
        }
    ]

    text = ""
    for _ in range(_MAX_TOOL_ITERATIONS):
        resp = llm.complete(SYSTEM_PROMPT_TOOLS, messages, tools=narrative_tools.TOOLS)
        tool_uses = [b for b in resp.content if getattr(b, "type", None) == "tool_use"]
        text = _text_of(resp.content)
        messages.append({"role": "assistant", "content": resp.content})

        if not tool_uses:
            break

        results = []
        for tu in tool_uses:
            out = narrative_tools.run_tool(tu.name, tu.input, facts_cache)
            _accumulate_allowed(out, allowed)
            results.append({"type": "tool_result", "tool_use_id": tu.id, "content": json.dumps(out)})
        messages.append({"role": "user", "content": results})

    if not text:
        return _result(render_template(facts), "template", None)

    bad = verify_numbers(text, allowed)
    if bad:
        return _result(render_template(facts), "template", None, flagged=bad)
    return _result(text, "llm", settings.NARRATIVE_MODEL)

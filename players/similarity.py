from __future__ import annotations

import math
import statistics
from typing import Callable

from django.core.cache import cache
from django.db.models import Max, Sum

from stats.models import BattingSeason, PitchingSeason
from .models import Player

_CACHE_TTL   = 3600
_MIN_WAR     = 1.0
BAT_WEIGHTS  = [2.0, 1.0, 1.5, 0.8, 0.8, 0.8]  # war, peak, ops+, hr_rate, pos_value, pos_kind
PIT_WEIGHTS  = [2.0, 1.0, 1.5, 1.0, 0.8, 0.6]  # war, peak, era+, k9, sp_pct, saves_rate

# Two-axis embedding of the defensive spectrum.
# pos_value: 0.0 (DH, no defense) → 1.0 (C, hardest to play)
# pos_kind:  -1.0 (corner/power) → +1.0 (up-the-middle/defense)
POS_EMBEDDING: dict[str, tuple[float, float]] = {
    "C":  (1.0,  1.0),
    "SS": (0.8,  0.5),
    "2B": (0.7,  0.5),
    "CF": (0.7,  0.5),
    "3B": (0.6,  0.0),
    "RF": (0.4, -0.5),
    "LF": (0.4, -0.5),
    "1B": (0.2, -1.0),
    "DH": (0.0, -1.0),
}


# ---------------------------------------------------------------------------
# Aggregate loaders (cached)
# ---------------------------------------------------------------------------

def _load_bat_agg() -> tuple[dict, dict, dict]:
    cached = cache.get("sim_bat_agg")
    if cached is not None:
        return cached  # type: ignore[return-value]

    bat_totals = {
        r["player_id"]: r
        for r in BattingSeason.objects.values("player_id").annotate(
            career_war=Sum("war"),
            peak_war=Max("war"),
            career_pa=Sum("plate_appearances"),
            career_hr=Sum("home_runs"),
        )
    }
    ops_num: dict[str, float] = {}
    ops_den: dict[str, int]   = {}
    for r in BattingSeason.objects.values("player_id", "ops_plus", "plate_appearances"):
        if r["ops_plus"] is None or not r["plate_appearances"]:
            continue
        pid = r["player_id"]
        ops_num[pid] = ops_num.get(pid, 0.0) + r["ops_plus"] * r["plate_appearances"]
        ops_den[pid] = ops_den.get(pid, 0)   + r["plate_appearances"]

    result = (bat_totals, ops_num, ops_den)
    cache.set("sim_bat_agg", result, timeout=_CACHE_TTL)
    return result


def _load_pit_agg() -> tuple[dict, dict, dict]:
    cached = cache.get("sim_pit_agg")
    if cached is not None:
        return cached  # type: ignore[return-value]

    pit_totals = {
        r["player_id"]: r
        for r in PitchingSeason.objects.values("player_id").annotate(
            career_war=Sum("war"),
            peak_war=Max("war"),
            career_ip=Sum("ip_outs"),
            career_so=Sum("strikeouts"),
            career_g=Sum("games"),
            career_gs=Sum("games_started"),
            career_saves=Sum("saves"),
        )
    }
    era_num: dict[str, float] = {}
    era_den: dict[str, int]   = {}
    for r in PitchingSeason.objects.values("player_id", "era_plus", "ip_outs"):
        if r["era_plus"] is None or not r["ip_outs"]:
            continue
        pid = r["player_id"]
        era_num[pid] = era_num.get(pid, 0.0) + r["era_plus"] * r["ip_outs"]
        era_den[pid] = era_den.get(pid, 0)   + r["ip_outs"]

    result = (pit_totals, era_num, era_den)
    cache.set("sim_pit_agg", result, timeout=_CACHE_TTL)
    return result


# ---------------------------------------------------------------------------
# Feature vectors
# ---------------------------------------------------------------------------

def _batter_vec(
    pid: str,
    bat_totals: dict,
    ops_num: dict[str, float],
    ops_den: dict[str, int],
    positions: dict[str, str | None],
) -> list[float]:
    t        = bat_totals.get(pid, {})
    war      = t.get("career_war") or 0.0
    peak     = t.get("peak_war")   or 0.0
    pa       = t.get("career_pa")  or 0
    hr       = t.get("career_hr")  or 0
    n, d     = ops_num.get(pid, 0.0), ops_den.get(pid, 0)
    ops_plus = n / d if d > 0 else 100.0   # 100 = league avg
    hr_rate  = hr / pa * 600 if pa > 0 else 0.0
    pos_val, pos_kind = POS_EMBEDDING.get(positions.get(pid) or "", (0.35, 0.0))
    return [war, peak, ops_plus, hr_rate, pos_val, pos_kind]


def _pitcher_vec(
    pid: str,
    pit_totals: dict,
    era_num: dict[str, float],
    era_den: dict[str, int],
) -> list[float]:
    t          = pit_totals.get(pid, {})
    war        = t.get("career_war")   or 0.0
    peak       = t.get("peak_war")     or 0.0
    ip         = t.get("career_ip")    or 0
    so         = t.get("career_so")    or 0
    g          = t.get("career_g")     or 1
    gs         = t.get("career_gs")    or 0
    saves      = t.get("career_saves") or 0
    n, d       = era_num.get(pid, 0.0), era_den.get(pid, 0)
    era_plus   = n / d if d > 0 else 100.0
    k9         = so / (ip / 27) if ip > 0 else 6.0
    sp_pct     = gs / g if g > 0 else 0.0
    relief_app = max(g - gs, 1)
    saves_rate = saves / relief_app if gs < g else 0.0  # 0 for pure starters
    return [war, peak, era_plus, k9, sp_pct, saves_rate]


# ---------------------------------------------------------------------------
# Scoring (pure maths — no Django)
# ---------------------------------------------------------------------------

def _rank_pool(
    target_pid: str,
    pool_pids: set[str],
    vec_fn: Callable[[str], list[float]],
    weights: list[float],
) -> list[tuple[str, int]]:
    """Return [(pid, similarity_score)] for the top 8 matches, best first."""
    pool_vecs  = {pid: vec_fn(pid) for pid in pool_pids}
    target_vec = vec_fn(target_pid)
    n_feat     = len(target_vec)

    stds: list[float] = []
    for i in range(n_feat):
        vals = [v[i] for v in pool_vecs.values()]
        try:
            s = statistics.stdev(vals)
        except statistics.StatisticsError:
            s = 1.0
        stds.append(s if s > 0 else 1.0)

    def dist(vec: list[float]) -> float:
        return math.sqrt(sum(
            weights[i] * ((target_vec[i] - vec[i]) / stds[i]) ** 2
            for i in range(n_feat)
        ))

    scored = sorted(
        [(dist(vec), pid) for pid, vec in pool_vecs.items() if pid != target_pid]
    )
    all_dists   = [d for d, _ in scored]
    median_dist = all_dists[len(all_dists) // 2] if all_dists else 1.0
    k           = -math.log(0.30) / max(median_dist, 1e-6)

    return [(pid, round(100 * math.exp(-k * d))) for d, pid in scored[:8]]


# ---------------------------------------------------------------------------
# DB hydration
# ---------------------------------------------------------------------------

def _hydrate(
    ranked: list[tuple[str, int]],
    bat_totals: dict,
    pit_totals: dict,
    pitcher_ids: set[str],
) -> list[dict]:
    """Fetch Player rows and build result dicts for the top 4 valid matches."""
    top_ids     = [pid for pid, _ in ranked]
    players_map = {
        p.bbref_id: p
        for p in Player.objects.filter(bbref_id__in=top_ids).only(
            "bbref_id", "first_name", "last_name", "debut", "final_game",
            "primary_position", "throws",
        )
    }
    results: list[dict] = []
    for pid, similarity in ranked:
        p = players_map.get(pid)
        if not p:
            continue
        career_war = (bat_totals.get(pid, {}).get("career_war") or 0.0) + \
                     (pit_totals.get(pid, {}).get("career_war") or 0.0)
        results.append({
            "bbref_id":         p.bbref_id,
            "first_name":       p.first_name,
            "last_name":        p.last_name,
            "debut":            p.debut.isoformat() if p.debut else None,
            "final_game":       p.final_game.isoformat() if p.final_game else None,
            "career_war":       round(career_war, 1),
            "primary_position": p.primary_position,
            "throws":           p.throws,
            "is_pitcher":       pid in pitcher_ids,
            "similarity":       similarity,
        })
        if len(results) == 4:
            break
    return results


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def similar_players(player: Player) -> dict:
    bat_totals, ops_num, ops_den = _load_bat_agg()
    pit_totals, era_num, era_den = _load_pit_agg()

    pitcher_ids = set(pit_totals.keys())
    batter_ids  = set(bat_totals.keys())
    pid         = player.bbref_id

    # Load primary_position for all batter pool members in one query
    bat_pool_ids = {p for p, t in bat_totals.items() if (t.get("career_war") or 0) >= _MIN_WAR}
    positions: dict[str, str | None] = {
        p.bbref_id: p.primary_position
        for p in Player.objects.filter(bbref_id__in=bat_pool_ids).only("bbref_id", "primary_position")
    }

    def batter_vec(p: str) -> list[float]:
        return _batter_vec(p, bat_totals, ops_num, ops_den, positions)

    def pitcher_vec(p: str) -> list[float]:
        return _pitcher_vec(p, pit_totals, era_num, era_den)

    bat_pool = {p for p, t in bat_totals.items() if (t.get("career_war") or 0) >= _MIN_WAR}
    pit_pool = {p for p, t in pit_totals.items() if (t.get("career_war") or 0) >= _MIN_WAR}

    hydrate_kwargs = dict(
        bat_totals=bat_totals, pit_totals=pit_totals, pitcher_ids=pitcher_ids
    )

    return {
        "batters":  _hydrate(_rank_pool(pid, bat_pool, batter_vec, BAT_WEIGHTS), **hydrate_kwargs)
                    if pid in batter_ids else [],
        "pitchers": _hydrate(_rank_pool(pid, pit_pool, pitcher_vec, PIT_WEIGHTS), **hydrate_kwargs)
                    if pid in pitcher_ids else [],
    }

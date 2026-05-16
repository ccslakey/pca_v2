"""
Position-based career WAR percentile rankings.

Pool is cached for 1 hour — avoids a full-table scan on every profile request.
"""
import bisect
from time import time

from django.db.models import Sum

_CACHE_TTL = 3600  # seconds


def _load_pool() -> dict[str, list[float]]:
    """Return {position: sorted_career_war_list} for all players with known position."""
    from stats.models import BattingSeason, PitchingSeason

    from .models import Player

    # Aggregate career WAR per player from batting + pitching
    bat = dict(
        BattingSeason.objects.values("player_id")
        .annotate(total=Sum("war"))
        .values_list("player_id", "total")
    )
    pit = dict(
        PitchingSeason.objects.values("player_id")
        .annotate(total=Sum("war"))
        .values_list("player_id", "total")
    )

    all_ids = set(bat) | set(pit)
    war_by_id: dict[str, float] = {}
    for pid in all_ids:
        total = (bat.get(pid) or 0) + (pit.get(pid) or 0)
        war_by_id[pid] = round(total, 1)

    pos_by_id: dict[str, str] = dict(
        Player.objects.filter(
            bbref_id__in=all_ids,
            primary_position__isnull=False,
        ).values_list("bbref_id", "primary_position")
    )

    pool: dict[str, list[float]] = {}
    for pid, war in war_by_id.items():
        pos = pos_by_id.get(pid)
        if pos:
            pool.setdefault(pos, []).append(war)

    for lst in pool.values():
        lst.sort()

    return pool


_pool_cache: dict[str, list[float]] | None = None
_pool_loaded_at: float = 0


def _get_pool() -> dict[str, list[float]]:
    global _pool_cache, _pool_loaded_at
    if _pool_cache is None or (time() - _pool_loaded_at) > _CACHE_TTL:
        _pool_cache = _load_pool()
        _pool_loaded_at = time()
    return _pool_cache


def war_percentile(bbref_id: str, primary_position: str | None) -> dict | None:
    """
    Return {"top_pct": float, "position": str, "n": int} or None.

    top_pct is the percentage of same-position players this player exceeds,
    expressed as "top X%" (e.g. top_pct=3.2 means top 3.2%).
    """
    if not primary_position:
        return None

    from stats.models import BattingSeason, PitchingSeason

    bat = BattingSeason.objects.filter(player_id=bbref_id).aggregate(t=Sum("war"))["t"] or 0
    pit = PitchingSeason.objects.filter(player_id=bbref_id).aggregate(t=Sum("war"))["t"] or 0
    career_war = round(float(bat + pit), 1)

    pool = _get_pool()
    lst = pool.get(primary_position)
    if not lst:
        return None

    n = len(lst)
    rank_from_bottom = bisect.bisect_left(lst, career_war)
    rank = n - rank_from_bottom  # 1 = best; n = worst (among same position)
    pct_from_top = (1 - rank_from_bottom / n) * 100

    return {
        "top_pct": round(pct_from_top, 1),
        "position": primary_position,
        "rank": max(rank, 1),
        "n": n,
    }

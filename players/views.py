from __future__ import annotations

from typing import TYPE_CHECKING, Any

from django.core.cache import cache
from django.db import connection
from django.db.models import Count, Max, Sum
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.serializers import BaseSerializer

from stats.models import BattingSeason, PitchingSeason, PlayerAward
from stats.serializers import (
    BattingSeasonSerializer,
    FieldingSeasonSerializer,
    PitchingSeasonSerializer,
    PlayerAwardSerializer,
    StatcastZoneBucketSerializer,
)

from .featured import FEATURED_COMPARISONS
from .models import Player
from .serializers import PlayerDetailSerializer, PlayerListSerializer
from .similarity import similar_players

if TYPE_CHECKING:
    from django.db.models import QuerySet

_LEADERBOARD_CACHE_KEY = "leaderboard:v2"
_LEADERBOARD_CACHE_TTL = 3600  # 1 hour

_FEATURED_CACHE_KEY = "featured:v1"
_FEATURED_CACHE_TTL = 3600  # 1 hour

_AGING_CURVE_CACHE_TTL = 86_400  # 24 hours — changes only on ingest


def _build_aging_curve(role: str) -> list[dict[str, Any]]:
    """
    Mean value per metric by age for qualifying seasons — all metrics in one payload.
    Batters: ≥100 PA → war, hr, avg, ops, ops_plus, so.
    Pitchers: ≥50 IP (150 ip_outs) → war, era, era_plus, so.
    Age approximated as season_year − birth_year (off by ≤1 yr, fine for pop averages).
    """
    if role == "P":
        sql = """
            SELECT
                age,
                ROUND(AVG(war)::numeric,      2) AS war,
                ROUND(AVG(era)::numeric,      2) AS era,
                ROUND(AVG(era_plus)::numeric, 2) AS era_plus,
                ROUND(AVG(so)::numeric,       2) AS so,
                COUNT(*)                          AS n
            FROM (
                SELECT
                    (s.year - EXTRACT(YEAR FROM p.birth_date)::int) AS age,
                    s.war, s.era, s.era_plus, s.strikeouts AS so
                FROM stats_pitchingseason s
                JOIN players_player p ON p.bbref_id = s.player_id
                WHERE s.ip_outs >= 150 AND p.birth_date IS NOT NULL
            ) sub
            WHERE age BETWEEN 18 AND 60  -- satchel paige loved the game
            GROUP BY age
            ORDER BY age
        """
    else:
        sql = """
            SELECT
                age,
                ROUND(AVG(war)::numeric,      2) AS war,
                ROUND(AVG(hr)::numeric,        2) AS hr,
                ROUND(AVG(avg_)::numeric,      3) AS avg,
                ROUND(AVG(ops)::numeric,       3) AS ops,
                ROUND(AVG(ops_plus)::numeric,  2) AS ops_plus,
                ROUND(AVG(so)::numeric,        2) AS so,
                COUNT(*)                           AS n
            FROM (
                SELECT
                    (s.year - EXTRACT(YEAR FROM p.birth_date)::int) AS age,
                    s.war,
                    s.home_runs   AS hr,
                    s.batting_avg AS avg_,
                    s.ops,
                    s.ops_plus,
                    s.strikeouts  AS so
                FROM stats_battingseason s
                JOIN players_player p ON p.bbref_id = s.player_id
                WHERE s.plate_appearances >= 100 AND p.birth_date IS NOT NULL
            ) sub
            WHERE age BETWEEN 18 AND 60  -- satchel paige loved the game
            GROUP BY age
            ORDER BY age
        """

    with connection.cursor() as cursor:
        cursor.execute(sql)
        rows = cursor.fetchall()
        col_names = [col[0] for col in cursor.description]

    result = []
    for row in rows:
        vals = dict(zip(col_names, row))
        pt: dict[str, Any] = {"age": int(vals["age"]), "n": int(vals["n"])}
        for k, v in vals.items():
            if k in ("age", "n"):
                continue
            if v is not None:
                pt[k] = float(v)
        result.append(pt)

    return result


def _build_featured_trios() -> list[dict[str, Any]]:
    """Resolve curated bbref_ids → name/id bundles in one query."""
    all_ids = {pid for c in FEATURED_COMPARISONS for pid in c["player_ids"]}
    by_id = {
        p["bbref_id"]: p
        for p in Player.objects.filter(bbref_id__in=all_ids).values("bbref_id", "first_name", "last_name")
    }
    return [
        {
            "slug": c["slug"],
            "label": c["label"],
            "players": [by_id[pid] for pid in c["player_ids"] if pid in by_id],
        }
        for c in FEATURED_COMPARISONS
    ]


def _get_featured_trios() -> list[dict[str, Any]]:
    trios = cache.get(_FEATURED_CACHE_KEY)
    if trios is None:
        trios = _build_featured_trios()
        cache.set(_FEATURED_CACHE_KEY, trios, _FEATURED_CACHE_TTL)
    return trios


def _build_leaderboard_rows() -> list[dict[str, Any]]:
    """
    Build career-stat rows for every player using 4 flat GROUP BY queries.
    Much faster than correlated subqueries — called once, then cached.
    """
    # 1. Batting totals per player
    batting: dict[str, dict] = {}
    for row in BattingSeason.objects.values("player_id").annotate(
        war_sum=Sum("war"), hr=Sum("home_runs"), peak_war=Max("war")
    ):
        batting[row["player_id"]] = row

    # 2. Pitching totals per player
    pitching: dict[str, dict] = {}
    for row in PitchingSeason.objects.values("player_id").annotate(
        war_sum=Sum("war"), er=Sum("earned_runs"), ip=Sum("ip_outs"), peak_war=Max("war")
    ):
        pitching[row["player_id"]] = row

    # 3. Award counts per (player, kind)
    award_counts: dict[str, dict[str, int]] = {}
    for row in PlayerAward.objects.values("player_id", "kind").annotate(c=Count("id")):
        award_counts.setdefault(row["player_id"], {})[row["kind"]] = row["c"]

    # 4. Player metadata
    players = {
        p["bbref_id"]: p
        for p in Player.objects.values(
            "bbref_id",
            "first_name",
            "last_name",
            "debut",
            "final_game",
            "primary_position",
            "throws",
        )
    }

    rows: list[dict[str, Any]] = []
    for pid in set(batting) | set(pitching):
        if pid not in players:
            continue
        bat = batting.get(pid, {})
        pit = pitching.get(pid, {})

        bwar = float(bat.get("war_sum") or 0)
        pwar = float(pit.get("war_sum") or 0)
        career_war = round(bwar + pwar, 1)
        if career_war <= 0:
            continue

        peak_war = round(max(float(bat.get("peak_war") or 0), float(pit.get("peak_war") or 0)), 1)
        is_pitcher = pwar > bwar

        ip = pit.get("ip") or 0
        era = round((pit.get("er") or 0) * 27.0 / ip, 2) if ip > 0 else None

        aw = award_counts.get(pid, {})
        p = players[pid]
        rows.append(
            {
                "bbref_id": pid,
                "first_name": p["first_name"],
                "last_name": p["last_name"],
                "debut": p["debut"].isoformat() if p["debut"] else None,
                "final_game": p["final_game"].isoformat() if p["final_game"] else None,
                "primary_position": p["primary_position"],
                "throws": p["throws"],
                "career_war": career_war,
                "peak_war": peak_war,
                "is_pitcher": is_pitcher,
                "career_hr": int(bat.get("hr") or 0) if not is_pitcher else None,
                "career_era": era if is_pitcher else None,
                "mvp_count": aw.get("mvp", 0),
                "cy_count": aw.get("cy", 0),
                "gg_count": aw.get("gg", 0),
                "asg_count": aw.get("asg", 0),
            }
        )

    return rows


def _get_leaderboard_rows() -> list[dict[str, Any]]:
    rows = cache.get(_LEADERBOARD_CACHE_KEY)
    if rows is None:
        rows = _build_leaderboard_rows()
        cache.set(_LEADERBOARD_CACHE_KEY, rows, _LEADERBOARD_CACHE_TTL)
    return rows


class PlayerViewSet(viewsets.ReadOnlyModelViewSet[Player]):
    queryset: QuerySet[Player] = Player.objects.select_related("james_score").order_by("last_name", "first_name")
    filter_backends = [filters.SearchFilter, DjangoFilterBackend]
    search_fields = ["first_name", "last_name", "bbref_id"]
    filterset_fields = ["bats", "throws", "birth_country", "primary_position"]

    def get_serializer_class(self) -> type[BaseSerializer[Player]]:
        if self.action == "list":
            return PlayerListSerializer
        return PlayerDetailSerializer

    @action(detail=True, url_path="batting")
    def batting(self, request: Request, pk: str | None = None) -> Response:
        player: Player = self.get_object()
        qs = player.batting_seasons.all().order_by("year", "stint")
        return Response(BattingSeasonSerializer(qs, many=True).data)

    @action(detail=True, url_path="pitching")
    def pitching(self, request: Request, pk: str | None = None) -> Response:
        player: Player = self.get_object()
        qs = player.pitching_seasons.all().order_by("year", "stint")
        return Response(PitchingSeasonSerializer(qs, many=True).data)

    @action(detail=True, url_path="fielding")
    def fielding(self, request: Request, pk: str | None = None) -> Response:
        player: Player = self.get_object()
        qs = player.fielding_seasons.prefetch_related("position_tokens").all().order_by("year", "stint")
        return Response(FieldingSeasonSerializer(qs, many=True).data)

    @action(detail=True, url_path="awards")
    def awards(self, request: Request, pk: str | None = None) -> Response:
        player: Player = self.get_object()
        qs = player.awards.all().order_by("-year", "kind")
        return Response(PlayerAwardSerializer(qs, many=True).data)

    @action(detail=True, url_path="pitch_zone")
    def pitch_zone(self, request: Request, pk: str | None = None) -> Response:
        player: Player = self.get_object()
        role = request.query_params.get("role", "B")
        outcome = request.query_params.get("outcome", "contact")

        VALID_ROLES = {"B", "P"}
        VALID_OUTCOMES = {"contact", "hits", "whiffs"}
        if role not in VALID_ROLES or outcome not in VALID_OUTCOMES:
            return Response({"detail": "Invalid role or outcome."}, status=400)

        qs = player.zone_buckets.filter(role=role, outcome=outcome)
        return Response(
            {
                "role": role,
                "outcome": outcome,
                "buckets": StatcastZoneBucketSerializer(qs, many=True).data,
            }
        )

    @action(detail=True, url_path="similar")
    def similar(self, request: Request, pk: str | None = None) -> Response:
        return Response(similar_players(self.get_object()))

    @action(detail=False, url_path="aging_curve")
    def aging_curve(self, request: Request) -> Response:
        """Mean WAR by age for a role group. ?role=B (default) or ?role=P."""
        role = request.query_params.get("role", "B")
        if role not in ("B", "P"):
            role = "B"
        cache_key = f"aging_curve:v1:{role}"
        data = cache.get(cache_key)
        if data is None:
            data = _build_aging_curve(role)
            cache.set(cache_key, data, _AGING_CURVE_CACHE_TTL)
        return Response(data)

    @action(detail=False, url_path="featured")
    def featured(self, request: Request) -> Response:
        """Curated comparison groups for the Compare page landing state."""
        return Response({"trios": _get_featured_trios()})

    @action(detail=False, url_path="leaderboard")
    def leaderboard(self, request: Request) -> Response:
        pos_filter = request.query_params.get("pos", "")
        min_war = request.query_params.get("min_war", "0")
        era_start = request.query_params.get("era_start", "")
        era_end = request.query_params.get("era_end", "")
        sort_by = request.query_params.get("sort", "career_war")
        order = request.query_params.get("order", "desc")
        try:
            page_size = min(int(request.query_params.get("page_size", "25")), 250)
            page = max(int(request.query_params.get("page", "1")), 1)
        except ValueError:
            page_size, page = 25, 1

        try:
            min_war_val = float(min_war) if min_war else 0.0
        except ValueError:
            min_war_val = 0.0
        try:
            era_start_val = int(era_start) if era_start else None
            era_end_val = int(era_end) if era_end else None
        except ValueError:
            era_start_val = era_end_val = None

        VALID_SORTS = {"career_war", "peak_war", "career_hr", "asg_count"}
        if sort_by not in VALID_SORTS:
            sort_by = "career_war"

        rows = _get_leaderboard_rows()

        # --- filter in Python (cache holds all players) ---
        filtered: list[dict] = []
        for row in rows:
            if min_war_val > 0 and row["career_war"] < min_war_val:
                continue
            if pos_filter == "P" and not row["is_pitcher"]:
                continue
            if pos_filter == "B" and row["is_pitcher"]:
                continue
            if pos_filter not in {"", "P", "B"} and row["primary_position"] != pos_filter:
                continue
            debut_year = int(row["debut"][:4]) if row["debut"] else 0
            final_year = int(row["final_game"][:4]) if row["final_game"] else 9999
            if era_start_val and final_year < era_start_val:
                continue
            if era_end_val and debut_year > era_end_val:
                continue
            filtered.append(row)

        # --- sort in Python ---
        reverse = order != "asc"
        filtered.sort(
            key=lambda r: (-(r[sort_by] or 0) if reverse else (r[sort_by] or 0), r["last_name"], r["first_name"]),
            reverse=False,  # key already encodes direction
        )

        # --- paginate ---
        total = len(filtered)
        total_pages = max(1, (total + page_size - 1) // page_size)
        offset = (page - 1) * page_size
        results = filtered[offset : offset + page_size]

        return Response(
            {
                "count": total,
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages,
                "results": results,
            }
        )

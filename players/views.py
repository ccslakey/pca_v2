from __future__ import annotations

import math
import statistics
from typing import TYPE_CHECKING

from django.db.models import Max, Sum
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.serializers import BaseSerializer

from stats.models import BattingSeason, PitchingSeason
from stats.serializers import (
    BattingSeasonSerializer,
    PitchingSeasonSerializer,
    PlayerAwardSerializer,
    StatcastZoneBucketSerializer,
)

from .models import Player
from .serializers import PlayerDetailSerializer, PlayerListSerializer

if TYPE_CHECKING:
    from django.db.models import QuerySet


class PlayerViewSet(viewsets.ReadOnlyModelViewSet[Player]):
    queryset: QuerySet[Player] = Player.objects.all().order_by(
        "last_name", "first_name"
    )
    filter_backends = [filters.SearchFilter, DjangoFilterBackend]
    search_fields = ["first_name", "last_name", "bbref_id"]
    filterset_fields = ["bats", "throws", "birth_country"]

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

    @action(detail=True, url_path="awards")
    def awards(self, request: Request, pk: str | None = None) -> Response:
        player: Player = self.get_object()
        qs = player.awards.all().order_by("-year", "kind")
        return Response(PlayerAwardSerializer(qs, many=True).data)

    @action(detail=True, url_path="pitch_zone")
    def pitch_zone(self, request: Request, pk: str | None = None) -> Response:
        player: Player = self.get_object()
        role    = request.query_params.get("role", "B")
        outcome = request.query_params.get("outcome", "contact")

        VALID_ROLES    = {"B", "P"}
        VALID_OUTCOMES = {"contact", "hits", "whiffs"}
        if role not in VALID_ROLES or outcome not in VALID_OUTCOMES:
            return Response({"detail": "Invalid role or outcome."}, status=400)

        qs = player.zone_buckets.filter(role=role, outcome=outcome)
        return Response({
            "role": role,
            "outcome": outcome,
            "buckets": StatcastZoneBucketSerializer(qs, many=True).data,
        })

    @action(detail=True, url_path="similar")
    def similar(self, request: Request, pk: str | None = None) -> Response:
        player: Player = self.get_object()

        # --- Batting aggregates ---
        bat_totals: dict[str, dict] = {
            r["player_id"]: r
            for r in BattingSeason.objects.values("player_id").annotate(
                career_war=Sum("war"),
                peak_war=Max("war"),
                career_pa=Sum("plate_appearances"),
                career_hr=Sum("home_runs"),
            )
        }
        # PA-weighted career OPS+ (era-adjusted, 100 = league avg; skip null rows)
        _bat_ops_num: dict[str, float] = {}
        _bat_ops_den: dict[str, int] = {}
        for r in BattingSeason.objects.values("player_id", "ops_plus", "plate_appearances"):
            if r["ops_plus"] is None or not r["plate_appearances"]:
                continue
            pid = r["player_id"]
            _bat_ops_num[pid] = _bat_ops_num.get(pid, 0.0) + r["ops_plus"] * r["plate_appearances"]
            _bat_ops_den[pid] = _bat_ops_den.get(pid, 0) + r["plate_appearances"]

        # --- Pitching aggregates ---
        pit_totals: dict[str, dict] = {
            r["player_id"]: r
            for r in PitchingSeason.objects.values("player_id").annotate(
                career_war=Sum("war"),
                peak_war=Max("war"),
                career_ip=Sum("ip_outs"),
                career_so=Sum("strikeouts"),
                career_g=Sum("games"),
                career_gs=Sum("games_started"),
            )
        }
        # IP-weighted career ERA+ (era-adjusted, 100 = league avg, higher = better; skip null rows)
        _pit_era_num: dict[str, float] = {}
        _pit_era_den: dict[str, int] = {}
        for r in PitchingSeason.objects.values("player_id", "era_plus", "ip_outs"):
            if r["era_plus"] is None or not r["ip_outs"]:
                continue
            pid = r["player_id"]
            _pit_era_num[pid] = _pit_era_num.get(pid, 0.0) + r["era_plus"] * r["ip_outs"]
            _pit_era_den[pid] = _pit_era_den.get(pid, 0) + r["ip_outs"]

        pitcher_ids: set[str] = set(pit_totals.keys())
        target_is_pitcher = player.bbref_id in pitcher_ids

        def batter_vec(pid: str) -> list[float]:
            t = bat_totals.get(pid, {})
            war     = t.get("career_war") or 0.0
            peak    = t.get("peak_war")   or 0.0
            pa      = t.get("career_pa")  or 0
            hr      = t.get("career_hr")  or 0
            n, d    = _bat_ops_num.get(pid, 0.0), _bat_ops_den.get(pid, 0)
            ops_plus = n / d if d > 0 else 100.0  # 100 = league avg
            hr_rate  = hr / pa * 600 if pa > 0 else 0.0  # HR per 600 PA
            return [war, peak, ops_plus, hr_rate]

        def pitcher_vec(pid: str) -> list[float]:
            t = pit_totals.get(pid, {})
            war  = t.get("career_war") or 0.0
            peak = t.get("peak_war")   or 0.0
            ip   = t.get("career_ip")  or 0
            so   = t.get("career_so")  or 0
            g    = t.get("career_g")   or 1
            gs   = t.get("career_gs")  or 0
            n, d     = _pit_era_num.get(pid, 0.0), _pit_era_den.get(pid, 0)
            era_plus = n / d if d > 0 else 100.0  # 100 = league avg, higher = better
            k9       = so / (ip / 27) if ip > 0 else 6.0
            sp_pct   = gs / g if g > 0 else 0.0   # 0 = pure RP, 1 = pure SP
            return [war, peak, era_plus, k9, sp_pct]

        # Build comparison pool (same role, minimum 1 career WAR)
        if target_is_pitcher:
            pool = {pid for pid, t in pit_totals.items() if (t.get("career_war") or 0) >= 1.0}
            pool_vecs = {pid: pitcher_vec(pid) for pid in pool}
            weights   = [2.0, 1.0, 1.5, 1.0, 0.8]  # war, peak, era, k9, sp_pct
            target_vec = pitcher_vec(player.bbref_id)
        else:
            pool = {pid for pid, t in bat_totals.items() if (t.get("career_war") or 0) >= 1.0}
            pool_vecs = {pid: batter_vec(pid) for pid in pool}
            weights   = [2.0, 1.0, 1.5, 0.8]  # war, peak, ops, hr_rate
            target_vec = batter_vec(player.bbref_id)

        # Normalize each feature by its std dev across the pool
        n_feat = len(target_vec)
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

        scored: list[tuple[float, str]] = [
            (dist(vec), pid)
            for pid, vec in pool_vecs.items()
            if pid != player.bbref_id
        ]
        scored.sort(key=lambda x: x[0])
        top_ids = [pid for _, pid in scored[:8]]

        players_map = {
            p.bbref_id: p
            for p in Player.objects.filter(bbref_id__in=top_ids).only(
                "bbref_id", "first_name", "last_name", "mlb_played_first", "mlb_played_last"
            )
        }

        results = []
        for _, pid in scored[:8]:
            p = players_map.get(pid)
            if not p:
                continue
            career_war = (bat_totals.get(pid, {}).get("career_war") or 0.0) + \
                         (pit_totals.get(pid, {}).get("career_war") or 0.0)
            results.append({
                "bbref_id": p.bbref_id,
                "first_name": p.first_name,
                "last_name": p.last_name,
                "mlb_played_first": p.mlb_played_first,
                "mlb_played_last": p.mlb_played_last,
                "career_war": round(career_war, 1),
                "is_pitcher": pid in pitcher_ids,
            })

        return Response(results[:4])

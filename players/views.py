from __future__ import annotations

from typing import TYPE_CHECKING

from django.db.models import Sum
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.serializers import BaseSerializer

from .models import Player
from .serializers import PlayerListSerializer, PlayerDetailSerializer
from stats.models import BattingSeason, PitchingSeason
from stats.serializers import BattingSeasonSerializer, PitchingSeasonSerializer

if TYPE_CHECKING:
    from django.db.models import QuerySet


class PlayerViewSet(viewsets.ReadOnlyModelViewSet[Player]):
    queryset: QuerySet[Player] = Player.objects.all().order_by('last_name', 'first_name')
    filter_backends = [filters.SearchFilter, DjangoFilterBackend]
    search_fields = ['first_name', 'last_name', 'bbref_id']
    filterset_fields = ['bats', 'throws', 'birth_country']

    def get_serializer_class(self) -> type[BaseSerializer[Player]]:
        if self.action == 'list':
            return PlayerListSerializer
        return PlayerDetailSerializer

    @action(detail=True, url_path='batting')
    def batting(self, request: Request, pk: str | None = None) -> Response:
        player: Player = self.get_object()
        qs = player.batting_seasons.all().order_by('year', 'stint')
        return Response(BattingSeasonSerializer(qs, many=True).data)

    @action(detail=True, url_path='pitching')
    def pitching(self, request: Request, pk: str | None = None) -> Response:
        player: Player = self.get_object()
        qs = player.pitching_seasons.all().order_by('year', 'stint')
        return Response(PitchingSeasonSerializer(qs, many=True).data)

    @action(detail=True, url_path='similar')
    def similar(self, request: Request, pk: str | None = None) -> Response:
        player: Player = self.get_object()

        player_bat_war: float = BattingSeason.objects.filter(player=player).aggregate(s=Sum('war'))['s'] or 0.0
        player_pit_war: float = PitchingSeason.objects.filter(player=player).aggregate(s=Sum('war'))['s'] or 0.0
        player_war = player_bat_war + player_pit_war
        is_pitcher = PitchingSeason.objects.filter(player=player).exists()

        # Bulk-aggregate WAR per player (two queries, no N+1)
        bat_wars: dict[str, float] = {
            r['player_id']: r['s'] or 0.0
            for r in BattingSeason.objects.values('player_id').annotate(s=Sum('war'))
        }
        pit_wars: dict[str, float] = {
            r['player_id']: r['s'] or 0.0
            for r in PitchingSeason.objects.values('player_id').annotate(s=Sum('war'))
        }
        pitcher_ids: set[str] = set(
            PitchingSeason.objects.values_list('player_id', flat=True).distinct()
        )

        scored: list[tuple[float, Player, float]] = []
        for p in Player.objects.exclude(bbref_id=player.bbref_id).only(
            'bbref_id', 'first_name', 'last_name', 'mlb_played_first', 'mlb_played_last'
        ):
            p_war = (bat_wars.get(p.bbref_id, 0.0) or 0.0) + (pit_wars.get(p.bbref_id, 0.0) or 0.0)
            if abs(p_war) < 1.0:
                continue
            pos_penalty = 0.0 if (p.bbref_id in pitcher_ids) == is_pitcher else 6.0
            scored.append((abs(p_war - player_war) + pos_penalty, p, p_war))

        scored.sort(key=lambda x: x[0])

        return Response([
            {
                'bbref_id': p.bbref_id,
                'first_name': p.first_name,
                'last_name': p.last_name,
                'mlb_played_first': p.mlb_played_first,
                'mlb_played_last': p.mlb_played_last,
                'career_war': round(war, 1),
                'is_pitcher': p.bbref_id in pitcher_ids,
            }
            for _, p, war in scored[:4]
        ])

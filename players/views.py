from __future__ import annotations

from typing import TYPE_CHECKING

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.serializers import BaseSerializer

from .models import Player
from .serializers import PlayerListSerializer, PlayerDetailSerializer
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

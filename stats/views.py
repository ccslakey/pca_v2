from __future__ import annotations

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, viewsets
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import BattingSeason, IngestionLog, PitchingSeason
from .serializers import BattingSeasonSerializer, PitchingSeasonSerializer


@api_view(["GET"])
def meta(request):
    last = (
        IngestionLog.objects
        .filter(status="success")
        .order_by("-completed_at")
        .values_list("completed_at", flat=True)
        .first()
    )
    return Response({
        "last_updated": last.date().isoformat() if last else None,
    })


class BattingSeasonViewSet(viewsets.ReadOnlyModelViewSet[BattingSeason]):
    """
    Season batting stats. Filter by player, year, team, or league.
    Supports ordering on any numeric field via ?ordering=war or ?ordering=-home_runs.
    """
    queryset = BattingSeason.objects.select_related('player').order_by('year', 'stint')
    serializer_class = BattingSeasonSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['player', 'year', 'team', 'league']
    ordering_fields = [
        'year', 'games', 'plate_appearances', 'at_bats', 'runs', 'hits',
        'doubles', 'triples', 'home_runs', 'rbi', 'stolen_bases',
        'walks', 'strikeouts', 'batting_avg', 'on_base_pct',
        'slugging_pct', 'ops', 'ops_plus', 'war',
    ]


class PitchingSeasonViewSet(viewsets.ReadOnlyModelViewSet[PitchingSeason]):
    """
    Season pitching stats. Filter by player, year, team, or league.
    """
    queryset = PitchingSeason.objects.select_related('player').order_by('year', 'stint')
    serializer_class = PitchingSeasonSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['player', 'year', 'team', 'league']
    ordering_fields = [
        'year', 'games', 'games_started', 'wins', 'losses', 'saves',
        'ip_outs', 'strikeouts', 'walks', 'era', 'era_plus',
        'fip', 'whip', 'war',
    ]

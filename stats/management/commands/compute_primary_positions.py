from __future__ import annotations

from collections import defaultdict

from django.core.management.base import BaseCommand
from django.db.models import Prefetch

from players.models import Player
from stats.models import FieldingPositionToken, FieldingSeason, PitchingSeason
from stats.positions import choose_primary_position


class Command(BaseCommand):
    help = "Compute Player.primary_position from decoded BRef fielding positions."

    def handle(self, *args, **options) -> None:
        position_games: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

        token_qs = FieldingPositionToken.objects.order_by("rank")
        seasons = (
            FieldingSeason.objects
            .prefetch_related(Prefetch("position_tokens", queryset=token_qs))
            .only("player_id")
        )
        for season in seasons:
            tokens = [
                t for t in season.position_tokens.all()
                if t.position != "H"
            ]
            if not tokens:
                continue
            # Prefer BBref's * primary marker; fall back to first non-minor token
            primary_token = (
                next((t for t in tokens if t.is_primary_marker), None)
                or next((t for t in tokens if not t.is_minor_marker), None)
                or tokens[0]
            )
            # Count seasons (games field is not populated in the ingest)
            position_games[season.player_id][primary_token.position] += 1

        pitcher_ids = set(PitchingSeason.objects.values_list("player_id", flat=True).distinct())
        updates: list[Player] = []
        for player in Player.objects.only("bbref_id", "primary_position"):
            primary = choose_primary_position(position_games.get(player.bbref_id, {}))
            if primary is None and player.bbref_id in pitcher_ids:
                primary = "P"
            if player.primary_position != primary:
                player.primary_position = primary
                updates.append(player)

        if updates:
            Player.objects.bulk_update(updates, ["primary_position"], batch_size=500)

        self.stdout.write(self.style.SUCCESS(f"Updated {len(updates):,} player primary positions."))

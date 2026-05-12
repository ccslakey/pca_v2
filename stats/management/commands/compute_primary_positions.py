from __future__ import annotations

from collections import defaultdict

from django.core.management.base import BaseCommand
from players.models import Player
from stats.models import FieldingSeason, PitchingSeason
from stats.positions import choose_primary_position


class Command(BaseCommand):
    help = "Compute Player.primary_position from decoded BRef fielding positions."

    def handle(self, *args, **options) -> None:
        position_games: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

        seasons = (
            FieldingSeason.objects
            .prefetch_related("position_tokens")
            .only("player_id", "games")
        )
        for season in seasons:
            primary_token = next(
                (token for token in season.position_tokens.all() if token.position != "H"),
                None,
            )
            if primary_token is None:
                continue
            position_games[season.player_id][primary_token.position] += season.games or 0

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

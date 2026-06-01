"""
Pre-generate and persist player narratives so profiles serve instantly.

    python manage.py pregenerate_narratives --bbref-ids ruthba01 mayswi01
    python manage.py pregenerate_narratives --limit 50
    python manage.py pregenerate_narratives --limit 50 --force   # regenerate even if cached

Requires either --bbref-ids or --limit so a stray invocation can't generate a
narrative for every player in the database. Each run is keyed to the current
data version; cached rows for that version are skipped unless --force.
"""
from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from players import narrative
from players.models import Player
from players.views import _get_last_updated


class Command(BaseCommand):
    help = "Generate and persist grounded narratives for players."

    def add_arguments(self, parser):
        parser.add_argument("--bbref-ids", nargs="+", metavar="ID", help="Specific players to process.")
        parser.add_argument("--limit", type=int, help="Process up to N players that have season data.")
        parser.add_argument("--force", action="store_true", help="Regenerate even if already cached.")

    def handle(self, *args, **options):
        ids = options["bbref_ids"]
        limit = options["limit"]
        if not ids and not limit:
            raise CommandError("Pass --bbref-ids or --limit to bound generation.")

        if ids:
            players = list(Player.objects.filter(bbref_id__in=ids).order_by("bbref_id"))
        else:
            players = list(
                Player.objects
                .exclude(batting_seasons__isnull=True, pitching_seasons__isnull=True)
                .distinct()
                .order_by("bbref_id")[:limit]
            )
        if not players:
            raise CommandError("No matching players found.")

        data_version = _get_last_updated()
        for p in players:
            result = narrative.get_or_generate(p, data_version, force=options["force"])
            self.stdout.write(f"  {p.bbref_id}: {result['source']}")

        self.stdout.write(self.style.SUCCESS(f"Processed {len(players)} players (data_version={data_version})."))

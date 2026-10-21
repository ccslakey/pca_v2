"""Write pipeline/fixtures/eval_players.json from the local database: the
SAMPLE_PLAYERS rows plus their batting, pitching, and award rows, which is
everything build_facts, the narrative tools, and similar_players read. The
narrative eval CI job loads it into a freshly migrated, empty database.

    python pipeline/make_eval_fixture.py
"""
from __future__ import annotations

import os
import sys
from itertools import chain
from pathlib import Path

import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pca_backend.settings")
django.setup()

from django.core import serializers

from pipeline.eval_narrative import SAMPLE_PLAYERS
from players.models import Player
from stats.models import BattingSeason, PitchingSeason, PlayerAward

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "eval_players.json"


def main() -> None:
    players = Player.objects.filter(pk__in=SAMPLE_PLAYERS).order_by("pk")
    missing = sorted(set(SAMPLE_PLAYERS) - set(players.values_list("pk", flat=True)))
    if missing:
        sys.exit(f"SAMPLE_PLAYERS not in the database: {' '.join(missing)}")

    related = (
        model.objects.filter(player_id__in=SAMPLE_PLAYERS).order_by("pk")
        for model in (BattingSeason, PitchingSeason, PlayerAward)
    )
    FIXTURE.write_text(serializers.serialize("json", chain(players, *related), indent=1) + "\n")
    print(f"wrote {FIXTURE} ({FIXTURE.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()

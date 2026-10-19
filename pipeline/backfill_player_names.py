"""
pipeline/backfill_player_names.py

Re-splits every stored player name with parse_name(), anchored on the
Chadwick register's surname. Rows ingested before parse_name handled
suffixes and multi-word surnames hold splits like "Ken Griffey" / "Jr."
or "Tony La" / "Russa". The full name (first + " " + last) is unchanged,
so re-running is a no-op.

Usage:
  python pipeline/backfill_player_names.py --dry-run
  python pipeline/backfill_player_names.py
"""

from __future__ import annotations

import argparse
import os
import sys

import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pca_backend.settings")
django.setup()

from pipeline.ingest_bref_history import build_chadwick_index, parse_name
from players.models import Player

BATCH_SIZE = 500


def run(last_names: dict[str, str], dry_run: bool) -> int:
    players = list(Player.objects.only("bbref_id", "first_name", "last_name"))
    to_update: list[Player] = []
    for p in players:
        old = (p.first_name, p.last_name)
        new = parse_name(f"{p.first_name} {p.last_name}", last_names.get(p.bbref_id))
        if new != old:
            if dry_run:
                print(f"  {p.bbref_id:<10} {old[0]!r} / {old[1]!r}  ->  {new[0]!r} / {new[1]!r}")
            p.first_name, p.last_name = new
            to_update.append(p)

    print(f"{len(to_update):,} of {len(players):,} players re-split")
    if dry_run:
        print("[dry-run] No changes written.")
    else:
        Player.objects.bulk_update(to_update, ["first_name", "last_name"], batch_size=BATCH_SIZE)
    return len(to_update)


def main() -> None:
    parser = argparse.ArgumentParser(description="Re-split stored player names into first/last")
    parser.add_argument("--dry-run", action="store_true", help="Print each change without writing")
    args = parser.parse_args()

    index = build_chadwick_index()
    last_names = {bbref: str(row["name_last"]) for bbref, row in index.items() if row.get("name_last")}
    run(last_names=last_names, dry_run=args.dry_run)


if __name__ == "__main__":
    main()

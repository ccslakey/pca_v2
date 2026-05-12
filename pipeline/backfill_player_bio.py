"""
pipeline/backfill_player_bio.py

Fills null biographical fields on existing Player rows using two sources —
no page-by-page scraping, no rate limits.

Sources (in priority order):
  1. Chadwick register (GitHub CSV, fetched automatically via pybaseball)
       → birth_year, birth_country, bats, throws,
          mlb_played_first, mlb_played_last
  2. Lahman People.csv (must be supplied via --people-csv)
       → debut, final_game
       → gap-fills birth_year, birth_country, bats, throws

Getting People.csv:
  Download it from the SABR-hosted Lahman database:
  https://sabr.app.box.com/s/y1prhc795jk8zvmelfd3jq7tl389y6cd/file/2084263017537
  Then pass the path with --people-csv.

If --people-csv is omitted, the script runs on Chadwick only (debut and
final_game will remain null).

Usage:
  python pipeline/backfill_player_bio.py --people-csv ~/Downloads/People.csv
  python pipeline/backfill_player_bio.py --people-csv ~/Downloads/People.csv --dry-run
  python pipeline/backfill_player_bio.py --dry-run               # Chadwick-only
  python pipeline/backfill_player_bio.py --overwrite             # replace non-null values too
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import date

import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pca_backend.settings")
django.setup()

import pandas as pd
import pybaseball

pybaseball.cache.enable()

from players.models import Player

BATCH_SIZE = 500


# ---------------------------------------------------------------------------
# Source loaders
# ---------------------------------------------------------------------------

def load_chadwick() -> dict[str, dict]:
    """
    Returns bbref_id → {birth_country, bats, throws}
    Chadwick only carries birth_year (integer) — full birth_date is
    built from Lahman which has year + month + day.
    """
    print("Fetching Chadwick register...")
    reg = pybaseball.chadwick_register()
    print(f"  {len(reg):,} rows")

    out: dict[str, dict] = {}
    for _, row in reg.iterrows():
        bbref = row.get("key_bbref")
        if not bbref or pd.isna(bbref):
            continue
        bbref = str(bbref).strip()

        def _str(col: str) -> str | None:
            v = row.get(col)
            return str(v).strip() or None if pd.notna(v) else None

        def _char(col: str) -> str | None:
            v = _str(col)
            return v[0].upper() if v else None

        out[bbref] = {
            "birth_country": _str("birth_country"),
            "bats":          _char("bats"),
            "throws":        _char("throws"),
        }

    print(f"  {len(out):,} players with a bbref_id in Chadwick")
    return out


def load_lahman_people(people_csv: str) -> dict[str, dict]:
    """
    Returns bbref_id → {debut, final_game, and bio gap-fills}
    Reads People.csv from a local path (download from SABR Box:
    https://sabr.app.box.com/s/y1prhc795jk8zvmelfd3jq7tl389y6cd/file/2084263017537)
    Column layout: playerID, birthYear, birthCountry, bats, throws, debut, finalGame, ...
    """
    print(f"Reading {people_csv}...")
    people = pd.read_csv(people_csv, low_memory=False)
    print(f"  {len(people):,} rows")

    out: dict[str, dict] = {}
    for _, row in people.iterrows():
        # Lahman people() uses 'playerID' which is the bbref_id.
        # Some builds also have 'bbrefID' as a separate column — fall back.
        bbref = row.get("playerID") or row.get("bbrefID")
        if not bbref or pd.isna(bbref):
            continue
        bbref = str(bbref).strip()

        def _date(col: str) -> date | None:
            v = row.get(col)
            if pd.isna(v) or not v:
                return None
            try:
                return pd.to_datetime(v).date()
            except Exception:
                return None

        def _int(col: str) -> int | None:
            v = row.get(col)
            return int(v) if pd.notna(v) and v != 0 else None

        def _str(col: str) -> str | None:
            v = row.get(col)
            return str(v).strip() or None if pd.notna(v) else None

        def _char(col: str) -> str | None:
            v = _str(col)
            return v[0].upper() if v else None

        # Construct birth_date only when we have at least year + month;
        # day defaults to 1 if missing. Avoids storing misleading Jan 1 dates
        # when only birth_year is known.
        by = _int("birthYear")
        bm = _int("birthMonth")
        bd = _int("birthDay") or 1
        birth_date: date | None = None
        if by and bm:
            try:
                birth_date = date(by, bm, bd)
            except ValueError:
                birth_date = date(by, bm, 1)

        out[bbref] = {
            "birth_date":    birth_date,
            "debut":         _date("debut"),
            "final_game":    _date("finalGame"),
            # gap-fills for fields also in Chadwick
            "birth_country": _str("birthCountry"),
            "bats":          _char("bats"),
            "throws":        _char("throws"),
        }

    print(f"  {len(out):,} players with a playerID in Lahman people")
    return out


# ---------------------------------------------------------------------------
# Merge logic
# ---------------------------------------------------------------------------

FIELDS = [
    "birth_date", "birth_country", "bats", "throws",
    "debut", "final_game",
]


def merge(chadwick: dict[str, dict], lahman: dict[str, dict]) -> dict[str, dict]:
    """
    Chadwick wins for birth_country/bats/throws; Lahman provides
    birth_date, debut, and final_game (which Chadwick doesn't carry).
    """
    all_ids = set(chadwick) | set(lahman)
    merged: dict[str, dict] = {}
    for bbref in all_ids:
        ch = chadwick.get(bbref, {})
        lh = lahman.get(bbref, {})
        row: dict = {}
        for field in FIELDS:
            # Chadwick is primary; Lahman fills gaps
            row[field] = ch.get(field) or lh.get(field)
        merged[bbref] = row
    return merged


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run(dry_run: bool, overwrite: bool, verbose: bool, people_csv: str | None) -> None:
    chadwick = load_chadwick()
    if people_csv:
        lahman = load_lahman_people(people_csv)
    else:
        print("No --people-csv supplied — skipping debut/final_game (Chadwick only)")
        lahman = {}
    bio = merge(chadwick, lahman)

    players = list(Player.objects.all().only("bbref_id", *FIELDS))
    print(f"\n{len(players):,} Player rows in DB")

    to_update: list[Player] = []
    stats = {f: 0 for f in FIELDS}
    no_match = 0

    for p in players:
        row = bio.get(p.bbref_id)
        if not row:
            no_match += 1
            if verbose:
                print(f"  [no match] {p.bbref_id}")
            continue

        changed = False
        for field in FIELDS:
            new_val = row.get(field)
            if new_val is None:
                continue
            current = getattr(p, field)
            if current is None or overwrite:
                if current != new_val:
                    setattr(p, field, new_val)
                    stats[field] += 1
                    changed = True

        if changed:
            to_update.append(p)

    print(f"\nPlayers to update: {len(to_update):,}  (no source match: {no_match:,})")
    print("Field fill counts:")
    for field, count in stats.items():
        print(f"  {field:<20} {count:,}")

    if dry_run:
        print("\n[dry-run] No changes written.")
        return

    # Bulk update in batches
    for i in range(0, len(to_update), BATCH_SIZE):
        batch = to_update[i : i + BATCH_SIZE]
        Player.objects.bulk_update(batch, FIELDS)
        print(f"  updated {min(i + BATCH_SIZE, len(to_update)):,} / {len(to_update):,}", end="\r")

    print(f"\nDone. {len(to_update):,} players updated.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill Player biographical fields")
    parser.add_argument("--people-csv", metavar="PATH", help="Path to Lahman People.csv (for debut/final_game)")
    parser.add_argument("--dry-run",    action="store_true", help="Show what would change without writing")
    parser.add_argument("--overwrite",  action="store_true", help="Replace existing non-null values too")
    parser.add_argument("--verbose",    action="store_true", help="Print each unmatched player ID")
    args = parser.parse_args()

    run(dry_run=args.dry_run, overwrite=args.overwrite, verbose=args.verbose, people_csv=args.people_csv)


if __name__ == "__main__":
    main()

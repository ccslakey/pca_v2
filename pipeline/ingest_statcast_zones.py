"""
Ingest Statcast pitch-location data into StatcastZoneBucket.

Usage:
    python pipeline/ingest_statcast_zones.py [options]

Options:
    --min-war FLOAT       Minimum career WAR to include (default: 10.0)
    --limit INT           Stop after this many players (useful for testing)
    --force               Re-ingest even if already logged as successful
    --dry-run             Print what would be ingested without writing to DB
    --verbose             Print per-player bucket counts
    --roles B|P|both      Which role to ingest (default: both)
    --bbref-ids ID…       Ingest specific players by bbref_id (skips WAR filter)
    --start-date DATE     Start date YYYY-MM-DD (default: 2015-03-01)
    --end-date DATE       End date YYYY-MM-DD (default: today)

When --start-date is not the default (2015-03-01), the script runs in
incremental mode: new bucket counts are merged into existing DB rows rather
than replacing them.  The IngestionLog key includes the date range so the
idempotency check is per-range, not per-player.
"""

import argparse
import os
import sys
import time
import warnings
from datetime import date

import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pca_backend.settings')
django.setup()

import pandas as pd

# pybaseball reads multi-year CSVs with mixed-type columns; the DtypeWarning
# is harmless since pandas falls back to object dtype safely.
warnings.filterwarnings('ignore', category=pd.errors.DtypeWarning, module='pybaseball')

from django.db.models import Sum
from pybaseball import statcast_batter, statcast_pitcher

from players.models import Player
from stats.models import BattingSeason, PitchingSeason, StatcastZoneBucket
from pipeline.ingest_utils import already_ingested, log_error, log_success

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_START_DATE = '2015-03-01'
DEFAULT_END_DATE   = date.today().strftime('%Y-%m-%d')

BATTER_OUTCOMES = {
    'contact': lambda df: df['description'] == 'hit_into_play',
    'hits':    lambda df: df['events'].isin(['single', 'double', 'triple', 'home_run']),
    'whiffs':  lambda df: df['description'].isin(['swinging_strike', 'swinging_strike_blocked']),
}

PITCHER_OUTCOMES = {
    'whiffs':  lambda df: df['description'].isin(['swinging_strike', 'swinging_strike_blocked']),
    'contact': lambda df: df['description'] == 'hit_into_play',
    'hits':    lambda df: df['events'].isin(['single', 'double', 'triple', 'home_run']),
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def aggregate_buckets(df: pd.DataFrame, outcome_fns: dict) -> list[dict]:
    """
    Given a raw Statcast DataFrame, return a list of bucket dicts:
      {outcome, plate_x, plate_z, count, total}
    plate_x and plate_z are rounded to 0.1 ft.
    """
    df = df.dropna(subset=['plate_x', 'plate_z']).reset_index(drop=True)
    if df.empty:
        return []

    df = df.copy()
    df['px'] = (df['plate_x'] * 10).round() / 10
    df['pz'] = (df['plate_z'] * 10).round() / 10

    total_by_loc = df.groupby(['px', 'pz']).size().rename('total')

    buckets = []
    for outcome, mask_fn in outcome_fns.items():
        mask = mask_fn(df)
        counts = df[mask].groupby(['px', 'pz']).size().rename('count')
        merged = counts.to_frame().join(total_by_loc, how='left')
        for (px, pz), row in merged.iterrows():
            buckets.append({
                'outcome': outcome,
                'plate_x': px,
                'plate_z': pz,
                'count':   int(row['count']),
                'total':   int(row['total']),
            })
    return buckets


def write_buckets(player: Player, role: str, buckets: list[dict],
                  dry_run: bool, incremental: bool = False) -> int:
    if dry_run or not buckets:
        return len(buckets)

    if not incremental:
        StatcastZoneBucket.objects.filter(player=player, role=role).delete()
        objs = [
            StatcastZoneBucket(
                player=player,
                role=role,
                outcome=b['outcome'],
                plate_x=b['plate_x'],
                plate_z=b['plate_z'],
                count=b['count'],
                total=b['total'],
            )
            for b in buckets
        ]
        StatcastZoneBucket.objects.bulk_create(objs)
        return len(objs)

    # Incremental: add new counts to existing rows, insert new locations
    existing = {
        (r.outcome, r.plate_x, r.plate_z): r
        for r in StatcastZoneBucket.objects.filter(player=player, role=role)
    }
    new_objs:    list[StatcastZoneBucket] = []
    update_objs: list[StatcastZoneBucket] = []
    for b in buckets:
        key = (b['outcome'], b['plate_x'], b['plate_z'])
        if key in existing:
            row = existing[key]
            row.count += b['count']
            row.total += b['total']
            update_objs.append(row)
        else:
            new_objs.append(StatcastZoneBucket(
                player=player, role=role,
                outcome=b['outcome'],
                plate_x=b['plate_x'],
                plate_z=b['plate_z'],
                count=b['count'],
                total=b['total'],
            ))
    if new_objs:
        StatcastZoneBucket.objects.bulk_create(new_objs)
    if update_objs:
        StatcastZoneBucket.objects.bulk_update(update_objs, ['count', 'total'])
    return len(new_objs) + len(update_objs)


def ingest_player_role(player: Player, role: str, force: bool,
                       dry_run: bool, verbose: bool,
                       start_date: str, end_date: str,
                       incremental: bool = False) -> int:
    # Incremental runs get a date-range-specific key so the full-ingest log
    # doesn't prevent them from running, and re-running the same range is idempotent.
    if incremental:
        source_key = f'statcast_zone_{role.lower()}_{player.bbref_id}_{start_date}_{end_date}'
    else:
        source_key = f'statcast_zone_{role.lower()}_{player.bbref_id}'

    if not force and not dry_run and already_ingested(source_key):
        if verbose:
            print(f'    [{player.bbref_id}] {role} already ingested — skipping')
        return 0

    mlbam = player.mlbam_id
    if mlbam is None:
        if verbose:
            print(f'    [{player.bbref_id}] no mlbam_id — skipping')
        return 0

    try:
        if role == 'B':
            df = statcast_batter(start_date, end_date, mlbam)
            outcome_fns = BATTER_OUTCOMES
        else:
            df = statcast_pitcher(start_date, end_date, mlbam)
            outcome_fns = PITCHER_OUTCOMES

        buckets = aggregate_buckets(df, outcome_fns)
        n = write_buckets(player, role, buckets, dry_run, incremental=incremental)

        if not dry_run:
            log_success(source_key, n)
        if verbose:
            print(f'    [{player.bbref_id}] {role} → {n} buckets')
        return n

    except Exception as exc:
        print(f'    ERROR [{player.bbref_id}] {role}: {exc}')
        if not dry_run:
            log_error(source_key, exc)
        return 0


# ---------------------------------------------------------------------------
# Player selection
# ---------------------------------------------------------------------------

def players_by_war(min_war: float, roles: set[str]) -> list[tuple[Player, set[str]]]:
    """
    Return [(player, {roles})] for players with career WAR >= min_war
    and mlbam_id available and at least one season >= 2015.
    """
    bat_war = {
        r['player_id']: r['s'] or 0.0
        for r in BattingSeason.objects.values('player_id').annotate(s=Sum('war'))
    }
    pit_war = {
        r['player_id']: r['s'] or 0.0
        for r in PitchingSeason.objects.values('player_id').annotate(s=Sum('war'))
    }
    # Players with at least one season >= 2015 (Statcast era)
    recent_bat = set(BattingSeason.objects.filter(year__gte=2015).values_list('player_id', flat=True).distinct())
    recent_pit = set(PitchingSeason.objects.filter(year__gte=2015).values_list('player_id', flat=True).distinct())
    recent_ids = recent_bat | recent_pit

    batter_ids  = set(BattingSeason.objects.values_list('player_id', flat=True).distinct())
    pitcher_ids = set(PitchingSeason.objects.values_list('player_id', flat=True).distinct())

    results = []
    qs = Player.objects.filter(
        mlbam_id__isnull=False,
        bbref_id__in=recent_ids,
    )
    for p in qs:
        career_war = (bat_war.get(p.bbref_id, 0.0) or 0.0) + \
                     (pit_war.get(p.bbref_id, 0.0) or 0.0)
        if career_war < min_war:
            continue
        player_roles: set[str] = set()
        if 'B' in roles and p.bbref_id in batter_ids:
            player_roles.add('B')
        if 'P' in roles and p.bbref_id in pitcher_ids:
            player_roles.add('P')
        if player_roles:
            results.append((p, player_roles))

    results.sort(key=lambda x: -(
        (bat_war.get(x[0].bbref_id, 0.0) or 0.0) +
        (pit_war.get(x[0].bbref_id, 0.0) or 0.0)
    ))
    return results


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description='Ingest Statcast pitch zone data')
    parser.add_argument('--min-war', type=float, default=10.0,
                        help='Minimum career WAR to include (default: 10.0)')
    parser.add_argument('--limit', type=int, default=None,
                        help='Stop after N players')
    parser.add_argument('--force', action='store_true',
                        help='Re-ingest even if already logged')
    parser.add_argument('--dry-run', action='store_true',
                        help='Parse without writing to DB')
    parser.add_argument('--verbose', action='store_true',
                        help='Print per-player bucket counts')
    parser.add_argument('--roles', choices=['B', 'P', 'both'], default='both',
                        help='Which role to ingest (default: both)')
    parser.add_argument('--bbref-ids', nargs='+', metavar='ID',
                        help='Ingest specific players by bbref_id')
    parser.add_argument('--start-date', default=DEFAULT_START_DATE,
                        help=f'Start date YYYY-MM-DD (default: {DEFAULT_START_DATE})')
    parser.add_argument('--end-date', default=DEFAULT_END_DATE,
                        help='End date YYYY-MM-DD (default: today)')
    args = parser.parse_args()

    start_date  = args.start_date
    end_date    = args.end_date
    # When fetching a sub-range, merge into existing buckets rather than replace
    incremental = (start_date != DEFAULT_START_DATE)

    roles: set[str] = {'B', 'P'} if args.roles == 'both' else {args.roles}

    if args.bbref_ids:
        targets = []
        for bbref_id in args.bbref_ids:
            try:
                p = Player.objects.get(bbref_id=bbref_id)
            except Player.DoesNotExist:
                print(f'  WARNING: {bbref_id} not found in DB')
                continue
            player_roles = set()
            if 'B' in roles and BattingSeason.objects.filter(player=p).exists():
                player_roles.add('B')
            if 'P' in roles and PitchingSeason.objects.filter(player=p).exists():
                player_roles.add('P')
            if not player_roles:
                print(f'  WARNING: {bbref_id} has no seasons for roles {roles}')
                continue
            targets.append((p, player_roles))
    else:
        targets = players_by_war(args.min_war, roles)

    if args.limit:
        targets = targets[:args.limit]

    print(f'Players to ingest: {len(targets)}')
    print(f'Date range: {start_date} → {end_date}', end='')
    if incremental:
        print('  (incremental — merging into existing buckets)', end='')
    print()
    if args.dry_run:
        print('  (dry-run — no DB writes)')

    total_buckets = 0
    for i, (player, player_roles) in enumerate(targets, 1):
        print(f'  [{i}/{len(targets)}] {player.bbref_id} — {player.first_name} {player.last_name}')
        for role in sorted(player_roles):
            n = ingest_player_role(player, role, args.force, args.dry_run, args.verbose,
                                   start_date, end_date, incremental)
            total_buckets += n
            # Statcast has its own rate limiting but we add a small gap
            # between players to be polite to the API
            if not args.dry_run:
                time.sleep(2)

    print(f'\nDone. Total buckets written: {total_buckets:,}')


if __name__ == '__main__':
    main()

"""
Ingest Statcast pitch-location data into StatcastZoneBucket.

Usage:
    python pipeline/ingest_statcast_zones.py [options]

Options:
    --min-war FLOAT   Minimum career WAR to include (default: 10.0)
    --limit INT       Stop after this many players (useful for testing)
    --force           Re-ingest even if already logged as successful
    --dry-run         Print what would be ingested without writing to DB
    --verbose         Print per-player bucket counts
    --roles B|P|both  Which role to ingest (default: both)
    --bbref-ids ID…   Ingest specific players by bbref_id (skips WAR filter)
"""

import argparse
import os
import sys
import time

import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pca_backend.settings')
django.setup()

import pandas as pd
from pybaseball import statcast_batter, statcast_pitcher

from django.db.models import Sum
from stats.models import StatcastZoneBucket, IngestionLog, BattingSeason, PitchingSeason
from players.models import Player

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

START_DATE = '2015-03-01'
END_DATE   = '2024-11-01'

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

def already_ingested(source_key: str) -> bool:
    return IngestionLog.objects.filter(source=source_key, status='success').exists()


def log_success(source_key: str, rows: int) -> None:
    IngestionLog.objects.create(source=source_key, rows_loaded=rows, status='success')


def log_error(source_key: str, exc: Exception) -> None:
    IngestionLog.objects.create(source=source_key, rows_loaded=0,
                                status='error', error_msg=str(exc))


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


def write_buckets(player: Player, role: str, buckets: list[dict], dry_run: bool) -> int:
    if dry_run or not buckets:
        return len(buckets)

    # Delete existing rows for this (player, role) and replace
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


def ingest_player_role(player: Player, role: str, force: bool,
                       dry_run: bool, verbose: bool) -> int:
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
            df = statcast_batter(START_DATE, END_DATE, mlbam)
            outcome_fns = BATTER_OUTCOMES
        else:
            df = statcast_pitcher(START_DATE, END_DATE, mlbam)
            outcome_fns = PITCHER_OUTCOMES

        buckets = aggregate_buckets(df, outcome_fns)
        n = write_buckets(player, role, buckets, dry_run)

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
    args = parser.parse_args()

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
    if args.dry_run:
        print('  (dry-run — no DB writes)')

    total_buckets = 0
    for i, (player, player_roles) in enumerate(targets, 1):
        print(f'  [{i}/{len(targets)}] {player.bbref_id} — {player.first_name} {player.last_name}')
        for role in sorted(player_roles):
            n = ingest_player_role(player, role, args.force, args.dry_run, args.verbose)
            total_buckets += n
            # Statcast has its own rate limiting but we add a small gap
            # between players to be polite to the API
            if not args.dry_run:
                time.sleep(2)

    print(f'\nDone. Total buckets written: {total_buckets:,}')


if __name__ == '__main__':
    main()

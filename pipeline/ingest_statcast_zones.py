"""
Ingest Statcast pitch-location data into StatcastZoneCell: per player, role
and season, every pitch counted in the pitch zone heatmap's cell, with how
many were contact, hits and whiffs.

Usage:
    python pipeline/ingest_statcast_zones.py [options]

Options:
    --min-war FLOAT       Minimum career WAR to include (default: 10.0)
    --limit INT           Stop after this many players (useful for testing)
    --force               Re-ingest even if already logged as successful
    --dry-run             Print what would be ingested without writing to DB
    --verbose             Print per-player cell counts
    --roles B|P|both      Which role to ingest (default: both)
    --bbref-ids ID…       Ingest specific players by bbref_id (skips WAR filter)
    --season YEAR         Rebuild one season from a bulk Savant pull
                          (default: every season since 2015, per player)
"""

import argparse
import os
import sys
import time
import warnings
from datetime import date
from typing import TypedDict

import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pca_backend.settings')
django.setup()

import numpy as np
import pandas as pd
import pybaseball

# pybaseball reads multi-year CSVs with mixed-type columns; the DtypeWarning
# is harmless since pandas falls back to object dtype safely.
warnings.filterwarnings('ignore', category=pd.errors.DtypeWarning, module='pybaseball')

pybaseball.cache.enable()

from django.db import InterfaceError, OperationalError, close_old_connections
from django.db.models import Sum
from pybaseball import statcast, statcast_batter, statcast_pitcher

from pipeline.ingest_utils import already_ingested, log_error, log_success
from players.models import Player
from stats.models import (
    ZONE_GRID,
    ZONE_X_MAX,
    ZONE_X_MIN,
    ZONE_Z_MAX,
    ZONE_Z_MIN,
    BattingSeason,
    PitchingSeason,
    StatcastZoneCell,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

FIRST_SEASON = 2015

# The same pitches count for a batter and for the pitcher who threw them.
OUTCOMES = {
    'contact': lambda df: df['description'] == 'hit_into_play',
    'hits':    lambda df: df['events'].isin(['single', 'double', 'triple', 'home_run']),
    'whiffs':  lambda df: df['description'].isin(['swinging_strike', 'swinging_strike_blocked']),
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class Cell(TypedDict):
    season:  int
    cell_x:  int
    cell_z:  int
    pitches: int
    contact: int
    hits:    int
    whiffs:  int


def season_window(season: int | None) -> tuple[date, date]:
    today = date.today()
    if season is None:
        return date(FIRST_SEASON, 3, 1), today
    return date(season, 3, 1), min(date(season, 12, 31), today)


def cell_index(plate_x: pd.Series, plate_z: pd.Series) -> tuple[pd.Series, pd.Series]:
    """Each pitch's heatmap cell, as PitchZone.tsx bins it; outside the grid, a cell beyond 0..ZONE_GRID-1."""
    cell_x = np.floor((plate_x - ZONE_X_MIN) / (ZONE_X_MAX - ZONE_X_MIN) * ZONE_GRID).astype(int)
    cell_z = np.floor((ZONE_Z_MAX - plate_z) / (ZONE_Z_MAX - ZONE_Z_MIN) * ZONE_GRID).astype(int)
    return cell_x, cell_z


def aggregate_cells(df: pd.DataFrame | None) -> list[Cell]:
    """Every cell with a pitch, per season: all its pitches, and each outcome's count, 0 when none happened."""
    if df is None or df.empty:
        return []
    df = df.dropna(subset=['plate_x', 'plate_z'])
    if df.empty:
        return []

    cell_x, cell_z = cell_index(df['plate_x'], df['plate_z'])
    pitches = pd.DataFrame({
        'season':  df['game_year'].astype(int),
        'cell_x':  cell_x,
        'cell_z':  cell_z,
        'pitches': 1,
        **{outcome: rule(df).astype(int) for outcome, rule in OUTCOMES.items()},
    })
    cells = pitches.groupby(['season', 'cell_x', 'cell_z'], as_index=False).sum()
    return [{key: int(value) for key, value in row.items()} for row in cells.to_dict('records')]  # type: ignore[misc]


def write_cells(player: Player, role: str, cells: list[Cell], dry_run: bool) -> int:
    if dry_run or not cells:
        return len(cells)

    seasons = {c['season'] for c in cells}
    StatcastZoneCell.objects.filter(player=player, role=role, season__in=seasons).delete()
    StatcastZoneCell.objects.bulk_create(
        (StatcastZoneCell(player=player, role=role, **c) for c in cells), batch_size=2000,
    )
    return len(cells)


def write_cells_retrying(player: Player, role: str, cells: list[Cell], dry_run: bool) -> int:
    """
    write_cells, once more if the database connection dropped. Outside a
    request Django never reconnects by itself, so the broken connection is
    closed first and the retry opens a new one.
    """
    try:
        return write_cells(player, role, cells, dry_run)
    except (OperationalError, InterfaceError):
        close_old_connections()
        return write_cells(player, role, cells, dry_run)


def _source_key(player: Player, role: str, season: int | None) -> str:
    key = f'statcast_zone_{role.lower()}_{player.bbref_id}'
    if season is None:
        return key
    _, end = season_window(season)
    return f'{key}_{season}_{end}'


def ingest_player_role(player: Player, role: str, force: bool,
                       dry_run: bool, verbose: bool) -> int:
    source_key = _source_key(player, role, None)

    if not force and not dry_run and already_ingested(source_key):
        if verbose:
            print(f'    [{player.bbref_id}] {role} already ingested — skipping')
        return 0

    mlbam = player.mlbam_id
    if mlbam is None:
        if verbose:
            print(f'    [{player.bbref_id}] no mlbam_id — skipping')
        return 0

    start, end = season_window(None)
    try:
        if role == 'B':
            df = statcast_batter(str(start), str(end), mlbam)
        else:
            df = statcast_pitcher(str(start), str(end), mlbam)
        n = write_cells(player, role, aggregate_cells(df), dry_run)

        if not dry_run:
            log_success(source_key, n)
        if verbose:
            print(f'    [{player.bbref_id}] {role} → {n} cells')
        return n

    except Exception as exc:
        print(f'    ERROR [{player.bbref_id}] {role}: {exc}')
        if not dry_run:
            log_error(source_key, exc)
        return 0


def ingest_bulk(targets: list[tuple[Player, set[str]]], season: int,
                force: bool, dry_run: bool, verbose: bool) -> int:
    pending: list[tuple[Player, set[str]]] = []
    for player, player_roles in targets:
        if player.mlbam_id is None:
            if verbose:
                print(f'  [{player.bbref_id}] no mlbam_id — skipping')
            continue
        active_roles: set[str] = set()
        for role in player_roles:
            key = _source_key(player, role, season)
            if force or dry_run or not already_ingested(key):
                active_roles.add(role)
            elif verbose:
                print(f'    [{player.bbref_id}] {role} already ingested — skipping')
        if active_roles:
            pending.append((player, active_roles))

    if not pending:
        print('All targets already ingested for this season.')
        return 0

    start, end = season_window(season)
    print(f'Bulk-pulling Statcast pitches {start} → {end}...')
    df = statcast(str(start), str(end), verbose=verbose, parallel=True)
    if df is None or df.empty:
        print('  no pitches returned for window')
        return 0
    print(f'  pulled {len(df):,} pitches')

    target_mlbams = {p.mlbam_id for p, _ in pending}
    # groupby() drops rows where the key is NaN by default — fine here since
    # we only want target mlbam IDs.
    bat_df = df[df['batter'].isin(target_mlbams)]
    pit_df = df[df['pitcher'].isin(target_mlbams)]
    by_batter = {mlbam: g for mlbam, g in bat_df.groupby('batter')}
    by_pitcher = {mlbam: g for mlbam, g in pit_df.groupby('pitcher')}

    total = 0
    for i, (player, player_roles) in enumerate(pending, 1):
        print(f'  [{i}/{len(pending)}] {player.bbref_id} — {player.first_name} {player.last_name}')
        for role in sorted(player_roles):
            source_key = _source_key(player, role, season)
            pdf = by_batter.get(player.mlbam_id) if role == 'B' else by_pitcher.get(player.mlbam_id)

            try:
                n = write_cells_retrying(player, role, aggregate_cells(pdf), dry_run)
                if not dry_run:
                    log_success(source_key, n)
                total += n
                if verbose:
                    print(f'    [{player.bbref_id}] {role} → {n} cells')
            except Exception as exc:
                print(f'    ERROR [{player.bbref_id}] {role}: {exc}')
                if not dry_run:
                    # The failure may have been the connection: drop it if so, so the log and the next player reconnect.
                    close_old_connections()
                    log_error(source_key, exc)
    return total


# ---------------------------------------------------------------------------
# Player selection
# ---------------------------------------------------------------------------

def players_by_war(min_war: float, roles: set[str],
                   current_year: int | None = None,
                   active_min_pa: int = 50,
                   active_min_bfp: int = 50) -> list[tuple[Player, set[str]]]:
    """
    Return [(player, {roles})] for players with mlbam_id and a Statcast-era
    season (>= 2015) who match either:
      - career WAR >= min_war, or
      - active in current_year above the PA/BFP threshold (bypasses WAR).

    The current-year bypass surfaces rookies and callups who would otherwise
    be excluded by the career WAR floor. Pass current_year=None to disable.
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

    active_bat: set[str] = set()
    active_pit: set[str] = set()
    if current_year is not None:
        active_bat = set(BattingSeason.objects.filter(
            year=current_year, plate_appearances__gte=active_min_pa,
        ).values_list('player_id', flat=True))
        active_pit = set(PitchingSeason.objects.filter(
            year=current_year, bfp__gte=active_min_bfp,
        ).values_list('player_id', flat=True))

    results = []
    qs = Player.objects.filter(
        mlbam_id__isnull=False,
        bbref_id__in=recent_ids,
    )
    for p in qs:
        career_war = (bat_war.get(p.bbref_id, 0.0) or 0.0) + \
                     (pit_war.get(p.bbref_id, 0.0) or 0.0)
        is_active = p.bbref_id in active_bat or p.bbref_id in active_pit
        if career_war < min_war and not is_active:
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
                        help='Print per-player cell counts')
    parser.add_argument('--roles', choices=['B', 'P', 'both'], default='both',
                        help='Which role to ingest (default: both)')
    parser.add_argument('--bbref-ids', nargs='+', metavar='ID',
                        help='Ingest specific players by bbref_id')
    parser.add_argument('--season', type=int, default=None,
                        help='Rebuild one season from a bulk Savant pull '
                             f'(default: every season since {FIRST_SEASON}, per player)')
    parser.add_argument('--current-year', type=int, default=date.today().year,
                        help='Year used for active-player bypass of the WAR filter '
                             '(default: current calendar year). Pass 0 to disable.')
    parser.add_argument('--active-min-pa', type=int, default=50,
                        help='Min current-year PA for batter active-bypass (default: 50)')
    parser.add_argument('--active-min-bfp', type=int, default=50,
                        help='Min current-year BFP for pitcher active-bypass (default: 50)')
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
        current_year = args.current_year if args.current_year > 0 else None
        targets = players_by_war(
            args.min_war, roles,
            current_year=current_year,
            active_min_pa=args.active_min_pa,
            active_min_bfp=args.active_min_bfp,
        )

    if args.limit:
        targets = targets[:args.limit]

    print(f'Players to ingest: {len(targets)}')
    if args.dry_run:
        print('  (dry-run — no DB writes)')

    if args.season is not None:
        print(f'Rebuilding season {args.season} from a bulk Savant pull')
        total_cells = ingest_bulk(targets, args.season, args.force, args.dry_run, args.verbose)
    else:
        print(f'Rebuilding every season since {FIRST_SEASON} with per-player Savant calls')
        total_cells = 0
        for i, (player, player_roles) in enumerate(targets, 1):
            print(f'  [{i}/{len(targets)}] {player.bbref_id} — {player.first_name} {player.last_name}')
            for role in sorted(player_roles):
                n = ingest_player_role(player, role, args.force, args.dry_run, args.verbose)
                total_cells += n
                if not args.dry_run:
                    time.sleep(2)

    print(f'\nDone. Total cells written: {total_cells:,}')


if __name__ == '__main__':
    main()

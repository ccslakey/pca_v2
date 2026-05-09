"""
pipeline/ingest_bref_history.py

Scrapes Baseball Reference standard batting and pitching pages for every
season in MLB history (1871–present) and loads into Django models.

URL strategy:
  1901–present → /leagues/MLB/{year}-standard-{type}.shtml  (both AL+NL)
  1876–1900    → /leagues/NL/{year}-standard-{type}.shtml
  1882–1891    → /leagues/AA/{year}-standard-{type}.shtml
  1890         → /leagues/PL/1890-standard-{type}.shtml
  1884         → /leagues/UA/1884-standard-{type}.shtml
  1871–1875    → /leagues/NA/{year}-standard-{type}.shtml

Rate limit: BRefSession enforces 10 req/min (6s between requests).
Total pages: ~300 → approximately 30 minutes end-to-end.

Idempotent: completed year/league combos are logged in IngestionLog and
skipped on re-runs unless --force is passed.

Usage:
  python pipeline/ingest_bref_history.py
  python pipeline/ingest_bref_history.py --start-year 1950 --end-year 2024
  python pipeline/ingest_bref_history.py --batting-only
  python pipeline/ingest_bref_history.py --pitching-only
  python pipeline/ingest_bref_history.py --dry-run
  python pipeline/ingest_bref_history.py --force   # re-ingest already-logged years
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from collections.abc import Callable, Generator
from typing import Any

import django
import requests

# ---------------------------------------------------------------------------
# Django setup — must happen before any model imports
# ---------------------------------------------------------------------------
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pca_backend.settings')
django.setup()

import pybaseball
import pandas as pd
from bs4 import BeautifulSoup, Comment

pybaseball.cache.enable()

from players.models import Player
from stats.models import BattingSeason, PitchingSeason, IngestionLog
from pybaseball.datasources.bref import BRefSession

# ---------------------------------------------------------------------------
# League → year range mapping
# Pre-1901 leagues are scraped in addition to the MLB page (which only
# starts in 1901). Some years have multiple active leagues.
# ---------------------------------------------------------------------------
PRE_MLB_LEAGUES: dict[str, tuple[int, int]] = {
    'NA': (1871, 1875),
    'NL': (1876, 1900),
    'AA': (1882, 1891),
    'UA': (1884, 1884),
    'PL': (1890, 1890),
}

BREF_BASE = "https://www.baseball-reference.com/leagues"

MULTI_TEAM_MARKERS: set[str] = {'2TM', '3TM', '4TM', '5TM', 'TOT'}

TRANSIENT_ERRORS = (
    requests.exceptions.ConnectionError,
    requests.exceptions.Timeout,
    requests.exceptions.ChunkedEncodingError,
)

# Maps BRef data-stat column name → (model field name, converter function)
ColMap = dict[str, tuple[str, Callable[[Any], Any]]]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def build_chadwick_index() -> dict[str, dict[str, int | str | None]]:
    """
    Returns a dict: bbref_id → {mlbam_id, fangraphs_id, retro_id}
    sourced from the Chadwick register (GitHub).
    """
    print("Loading Chadwick register for player ID cross-reference...")
    reg = pybaseball.chadwick_register()
    index: dict[str, dict[str, int | str | None]] = {}
    for _, row in reg.iterrows():
        bbref = row.get('key_bbref')
        if not bbref or pd.isna(bbref):
            continue
        mlbam = row.get('key_mlbam')
        fg    = row.get('key_fangraphs')
        retro = row.get('key_retro')
        index[str(bbref)] = {
            'mlbam_id':     int(mlbam) if pd.notna(mlbam) and int(mlbam) > 0 else None,
            'fangraphs_id': int(fg)    if pd.notna(fg)    and int(fg)    > 0 else None,
            'retro_id':     str(retro) if pd.notna(retro) else None,
        }
    print(f"  {len(index):,} players indexed from Chadwick register.")
    return index


def league_urls(
    stat_type: str,
    start_year: int,
    end_year: int,
) -> Generator[tuple[int, str, str], None, None]:
    """
    Yields (year, league_code, url) tuples for every page that needs
    to be scraped. stat_type is 'batting' or 'pitching'.
    """
    for year in range(start_year, end_year + 1):
        if year >= 1901:
            yield year, 'MLB', f"{BREF_BASE}/MLB/{year}-standard-{stat_type}.shtml"
        for league, (ly_start, ly_end) in PRE_MLB_LEAGUES.items():
            if ly_start <= year <= ly_end:
                yield year, league, f"{BREF_BASE}/{league}/{year}-standard-{stat_type}.shtml"


def extract_table(html_bytes: bytes, table_id: str) -> pd.DataFrame:
    """
    Parses a BRef standard stats table from raw HTML.
    Returns a DataFrame where every row has a 'bbref_id' column.
    Modern BRef embeds tables inside HTML comments; older pages expose them
    directly — this handles both.
    """
    soup = BeautifulSoup(html_bytes, 'lxml')

    table = soup.find('table', {'id': table_id})
    if table is None:
        for comment in soup.find_all(string=lambda x: isinstance(x, Comment)):
            csoup = BeautifulSoup(comment, 'lxml')
            table = csoup.find('table', {'id': table_id})
            if table:
                break

    if table is None:
        return pd.DataFrame()

    rows: list[dict[str, str]] = []
    for tr in table.find('tbody').find_all('tr'):
        if 'thead' in tr.get('class', []):
            continue
        row: dict[str, str] = {}
        for cell in tr.find_all(['th', 'td']):
            stat = cell.get('data-stat')
            if not stat:
                continue
            if stat == 'name_display':
                row['bbref_id'] = cell.get('data-append-csv', '').strip()
            row[stat] = cell.get_text(strip=True)
        if row.get('bbref_id'):
            rows.append(row)

    return pd.DataFrame(rows)


def ip_to_outs(ip_str: Any) -> int | None:
    """
    Converts BRef's decimal IP format to total outs recorded.
    "6.1" → 19 (6 full innings + 1 out)
    "6.2" → 20 (6 full innings + 2 outs)
    """
    if not ip_str or ip_str in ('', '--'):
        return None
    try:
        parts = str(ip_str).split('.')
        full = int(parts[0])
        extra = int(parts[1]) if len(parts) > 1 and parts[1] else 0
        return full * 3 + extra
    except (ValueError, IndexError):
        return None


def to_int(val: Any) -> int | None:
    try:
        v = str(val).strip()
        return int(float(v)) if v not in ('', '--', 'NA') else None
    except (ValueError, TypeError):
        return None


def to_float(val: Any) -> float | None:
    try:
        v = str(val).strip()
        return float(v) if v not in ('', '--', 'NA') else None
    except (ValueError, TypeError):
        return None


def parse_name(display_name: str) -> tuple[str, str]:
    """
    Splits "Babe Ruth" or "Ruth, Babe*" into (first, last).
    BRef occasionally marks HOFers or active players with * or #.
    """
    name = display_name.strip().rstrip('*#').strip()
    if ',' in name:
        last, first = name.split(',', 1)
        return first.strip(), last.strip()
    parts = name.split()
    if len(parts) >= 2:
        return ' '.join(parts[:-1]), parts[-1]
    return name, ''


# ---------------------------------------------------------------------------
# Player upsert
# ---------------------------------------------------------------------------

def upsert_player(
    bbref_id: str,
    display_name: str,
    chadwick_index: dict[str, dict[str, int | str | None]],
    dry_run: bool,
) -> Player | None:
    """
    Creates or updates a Player record. Returns the Player instance or None.
    Cross-references Chadwick register for mlbam_id / fangraphs_id / retro_id.
    """
    if not bbref_id:
        return None

    first_name, last_name = parse_name(display_name)
    cross_ref = chadwick_index.get(bbref_id, {})

    defaults: dict[str, Any] = {
        'first_name':    first_name,
        'last_name':     last_name,
        'mlbam_id':      cross_ref.get('mlbam_id'),
        'fangraphs_id':  cross_ref.get('fangraphs_id'),
        'retro_id':      cross_ref.get('retro_id'),
    }

    if dry_run:
        return Player(bbref_id=bbref_id, **defaults)

    player, _ = Player.objects.update_or_create(
        bbref_id=bbref_id,
        defaults=defaults,
    )
    return player


# ---------------------------------------------------------------------------
# Retry wrapper
# ---------------------------------------------------------------------------

def fetch_with_retry(
    session: BRefSession,
    url: str,
    retries: int = 3,
    backoff: int = 20,
) -> requests.Response:
    """
    Fetches a URL via BRefSession, retrying on transient network errors.
    Waits backoff * attempt seconds between tries (20s, 40s, 60s by default).
    """
    for attempt in range(1, retries + 1):
        try:
            return session.get(url)
        except TRANSIENT_ERRORS as exc:
            if attempt == retries:
                raise
            wait = backoff * attempt
            print(f"    network error ({exc}), retrying in {wait}s (attempt {attempt}/{retries})")
            time.sleep(wait)
    raise RuntimeError("fetch_with_retry exhausted retries without returning or raising")


# ---------------------------------------------------------------------------
# Column maps
# ---------------------------------------------------------------------------

BATTING_COL_MAP: ColMap = {
    'b_games':                    ('games',            to_int),
    'b_pa':                       ('plate_appearances', to_int),
    'b_ab':                       ('at_bats',          to_int),
    'b_r':                        ('runs',             to_int),
    'b_h':                        ('hits',             to_int),
    'b_doubles':                  ('doubles',          to_int),
    'b_triples':                  ('triples',          to_int),
    'b_hr':                       ('home_runs',        to_int),
    'b_rbi':                      ('rbi',              to_int),
    'b_sb':                       ('stolen_bases',     to_int),
    'b_cs':                       ('caught_stealing',  to_int),
    'b_bb':                       ('walks',            to_int),
    'b_so':                       ('strikeouts',       to_int),
    'b_ibb':                      ('ibb',              to_int),
    'b_hbp':                      ('hbp',              to_int),
    'b_sh':                       ('sacrifice_hits',   to_int),
    'b_sf':                       ('sacrifice_flies',  to_int),
    'b_gidp':                     ('gidp',             to_int),
    'b_tb':                       ('total_bases',      to_int),
    'b_batting_avg':              ('batting_avg',      to_float),
    'b_onbase_perc':              ('on_base_pct',      to_float),
    'b_slugging_perc':            ('slugging_pct',     to_float),
    'b_onbase_plus_slugging':     ('ops',              to_float),
    'b_onbase_plus_slugging_plus':('ops_plus',         to_int),
    'b_war':                      ('war',              to_float),
}

PITCHING_COL_MAP: ColMap = {
    'p_w':                              ('wins',               to_int),
    'p_l':                              ('losses',             to_int),
    'p_g':                              ('games',              to_int),
    'p_gs':                             ('games_started',      to_int),
    'p_cg':                             ('complete_games',     to_int),
    'p_sho':                            ('sho',                to_int),
    'p_sv':                             ('saves',              to_int),
    'p_gf':                             ('games_finished',     to_int),
    'p_ip':                             ('ip_outs',            ip_to_outs),
    'p_h':                              ('hits_allowed',       to_int),
    'p_r':                              ('runs_allowed',       to_int),
    'p_er':                             ('earned_runs',        to_int),
    'p_hr':                             ('home_runs',          to_int),
    'p_bb':                             ('walks',              to_int),
    'p_ibb':                            ('ibb',                to_int),
    'p_so':                             ('strikeouts',         to_int),
    'p_hbp':                            ('hbp',                to_int),
    'p_wp':                             ('wild_pitches',       to_int),
    'p_bk':                             ('balks',              to_int),
    'p_bfp':                            ('bfp',                to_int),
    'p_sf':                             ('sacrifice_flies',    to_int),
    'p_gdp':                            ('gidp',               to_int),
    'p_earned_run_avg':                 ('era',                to_float),
    'p_earned_run_avg_plus':            ('era_plus',           to_int),
    'p_fip':                            ('fip',                to_float),
    'p_whip':                           ('whip',               to_float),
    'p_hits_per_nine':                  ('hits_per_nine',      to_float),
    'p_hr_per_nine':                    ('home_runs_per_nine', to_float),
    'p_bb_per_nine':                    ('walks_per_nine',     to_float),
    'p_so_per_nine':                    ('strikeouts_per_nine',to_float),
    'p_strikeouts_per_base_on_balls':   ('strikeouts_per_walk',to_float),
    'p_war':                            ('war',                to_float),
}


# ---------------------------------------------------------------------------
# Ingest functions
# ---------------------------------------------------------------------------

def ingest_batting_page(
    session: BRefSession,
    year: int,
    league: str,
    url: str,
    chadwick_index: dict[str, dict[str, int | str | None]],
    dry_run: bool,
    verbose: bool,
) -> int:
    df = extract_table(fetch_with_retry(session, url).content, 'players_standard_batting')
    if df.empty:
        return 0

    if 'team_name_abbr' in df.columns:
        df = df[~df['team_name_abbr'].isin(MULTI_TEAM_MARKERS)]

    records: list[BattingSeason] = []
    stint_tracker: dict[str, int] = {}

    for _, row in df.iterrows():
        bbref_id: str = row.get('bbref_id', '').strip()
        if not bbref_id:
            continue

        team   = row.get('team_name_abbr', '').strip()
        player = upsert_player(bbref_id, row.get('name_display', ''), chadwick_index, dry_run)
        if player is None:
            continue

        stint = stint_tracker.get(bbref_id, 0) + 1
        stint_tracker[bbref_id] = stint

        kwargs: dict[str, Any] = {
            'player_id': player.bbref_id,
            'year':      year,
            'stint':     stint,
            'team':      team,
            'league':    league,
        }
        for bref_col, (model_field, converter) in BATTING_COL_MAP.items():
            if bref_col in row:
                kwargs[model_field] = converter(row[bref_col])

        records.append(BattingSeason(**kwargs))

    if not dry_run and records:
        BattingSeason.objects.bulk_create(
            records,
            update_conflicts=True,
            unique_fields=['player', 'year', 'stint', 'team'],
            update_fields=[f for f in BATTING_COL_MAP.values() for f in [f[0]]],
        )

    if verbose:
        print(f"    {len(records)} batting rows {'(dry run)' if dry_run else 'written'}")
    return len(records)


def ingest_pitching_page(
    session: BRefSession,
    year: int,
    league: str,
    url: str,
    chadwick_index: dict[str, dict[str, int | str | None]],
    dry_run: bool,
    verbose: bool,
) -> int:
    df = extract_table(fetch_with_retry(session, url).content, 'players_standard_pitching')
    if df.empty:
        return 0

    if 'team_name_abbr' in df.columns:
        df = df[~df['team_name_abbr'].isin(MULTI_TEAM_MARKERS)]

    records: list[PitchingSeason] = []
    stint_tracker: dict[str, int] = {}

    for _, row in df.iterrows():
        bbref_id: str = row.get('bbref_id', '').strip()
        if not bbref_id:
            continue

        team   = row.get('team_name_abbr', '').strip()
        player = upsert_player(bbref_id, row.get('name_display', ''), chadwick_index, dry_run)
        if player is None:
            continue

        stint = stint_tracker.get(bbref_id, 0) + 1
        stint_tracker[bbref_id] = stint

        kwargs: dict[str, Any] = {
            'player_id': player.bbref_id,
            'year':      year,
            'stint':     stint,
            'team':      team,
            'league':    league,
        }
        for bref_col, (model_field, converter) in PITCHING_COL_MAP.items():
            if bref_col in row:
                kwargs[model_field] = converter(row[bref_col])

        records.append(PitchingSeason(**kwargs))

    if not dry_run and records:
        PitchingSeason.objects.bulk_create(
            records,
            update_conflicts=True,
            unique_fields=['player', 'year', 'stint', 'team'],
            update_fields=[f for f in PITCHING_COL_MAP.values() for f in [f[0]]],
        )

    if verbose:
        print(f"    {len(records)} pitching rows {'(dry run)' if dry_run else 'written'}")
    return len(records)


# ---------------------------------------------------------------------------
# Ingestion log helpers
# ---------------------------------------------------------------------------

def already_ingested(source_key: str) -> bool:
    return IngestionLog.objects.filter(source=source_key, status='success').exists()


def log_success(source_key: str, rows: int) -> None:
    IngestionLog.objects.create(source=source_key, rows_loaded=rows, status='success')


def log_error(source_key: str, exc: Exception) -> None:
    IngestionLog.objects.create(source=source_key, rows_loaded=0, status='error', error_msg=str(exc))


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description='Ingest BRef batting/pitching history into Django.')
    parser.add_argument('--start-year',    type=int, default=1871)
    parser.add_argument('--end-year',      type=int, default=2025)
    parser.add_argument('--batting-only',  action='store_true')
    parser.add_argument('--pitching-only', action='store_true')
    parser.add_argument('--dry-run',       action='store_true', help='Parse and print counts without writing to DB')
    parser.add_argument('--force',         action='store_true', help='Re-ingest even if already logged as success')
    parser.add_argument('--verbose',       action='store_true', default=True)
    args = parser.parse_args()

    do_batting  = not args.pitching_only
    do_pitching = not args.batting_only

    session = BRefSession()
    chadwick_index = build_chadwick_index()

    IngestFn = Callable[
        [BRefSession, int, str, str, dict[str, dict[str, int | str | None]], bool, bool],
        int,
    ]
    stat_types: list[tuple[str, IngestFn]] = []
    if do_batting:
        stat_types.append(('batting',  ingest_batting_page))
    if do_pitching:
        stat_types.append(('pitching', ingest_pitching_page))

    total_rows = 0

    for stat_type, ingest_fn in stat_types:
        print(f"\n{'='*60}")
        print(f"Ingesting {stat_type.upper()} | {args.start_year}–{args.end_year}")
        print(f"{'='*60}")

        for year, league, url in league_urls(stat_type, args.start_year, args.end_year):
            source_key = f"bref_{stat_type}_{league}_{year}"

            if not args.force and not args.dry_run and already_ingested(source_key):
                if args.verbose:
                    print(f"  [{year} {league}] already ingested, skipping")
                continue

            print(f"  [{year} {league}] {url}")

            try:
                rows = ingest_fn(
                    session, year, league, url,
                    chadwick_index, args.dry_run, args.verbose,
                )
                total_rows += rows
                if not args.dry_run:
                    log_success(source_key, rows)
            except Exception as exc:
                print(f"    ERROR: {exc}")
                if not args.dry_run:
                    log_error(source_key, exc)

    print(f"\nDone. Total rows processed: {total_rows:,}")


if __name__ == '__main__':
    main()

"""
Tests for pipeline/ingest_statcast_zones.py.

Covers:
  - aggregate_buckets correctness
  - bulk path parity: groupby slice produces identical buckets to per-player filter
  - float64 batter/pitcher dtype tolerance (statcast CSV uses float64 when NaN rows present)
  - write_buckets: non-incremental replace, incremental merge
  - ingest_bulk: skips already-ingested, logs success/error

Run from project root:
    python -m pytest pipeline/test_statcast_zones.py -v
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pca_backend.settings')

import numpy as np
import pandas as pd
from django.test import TestCase
from unittest.mock import patch, MagicMock

from pipeline.ingest_statcast_zones import (
    BATTER_OUTCOMES,
    BULK_THRESHOLD_DAYS,
    PITCHER_OUTCOMES,
    _source_key,
    aggregate_buckets,
    ingest_bulk,
    write_buckets,
)
from players.models import Player
from stats.models import BattingSeason, IngestionLog, PitchingSeason, StatcastZoneBucket


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_pitch_df(rows: list[dict]) -> pd.DataFrame:
    """Build a minimal statcast-shaped DataFrame from a list of row dicts."""
    defaults = {
        'batter':      np.float64(0),
        'pitcher':     np.float64(0),
        'plate_x':     0.0,
        'plate_z':     2.5,
        'description': 'ball',
        'events':      None,
    }
    return pd.DataFrame([{**defaults, **r} for r in rows])


def _make_player(bbref_id: str, mlbam_id: int) -> Player:
    p, _ = Player.objects.update_or_create(
        bbref_id=bbref_id,
        defaults={'first_name': 'Test', 'last_name': 'Player', 'mlbam_id': mlbam_id},
    )
    return p


# ---------------------------------------------------------------------------
# aggregate_buckets
# ---------------------------------------------------------------------------

class TestAggregateBuckets(TestCase):
    def test_counts_whiffs_correctly(self):
        df = _make_pitch_df([
            {'plate_x': 0.0, 'plate_z': 2.0, 'description': 'swinging_strike'},
            {'plate_x': 0.0, 'plate_z': 2.0, 'description': 'swinging_strike'},
            {'plate_x': 0.0, 'plate_z': 2.0, 'description': 'ball'},
        ])
        buckets = aggregate_buckets(df, BATTER_OUTCOMES)
        whiff = next(b for b in buckets if b['outcome'] == 'whiffs')
        self.assertEqual(whiff['count'], 2)
        self.assertEqual(whiff['total'], 3)

    def test_empty_dataframe_returns_empty_list(self):
        self.assertEqual(aggregate_buckets(pd.DataFrame(), BATTER_OUTCOMES), [])

    def test_drops_rows_missing_plate_coordinates(self):
        df = _make_pitch_df([
            {'plate_x': np.nan, 'plate_z': 2.0, 'description': 'swinging_strike'},
            {'plate_x': 0.0,    'plate_z': 2.0, 'description': 'swinging_strike'},
        ])
        buckets = aggregate_buckets(df, BATTER_OUTCOMES)
        whiff = next(b for b in buckets if b['outcome'] == 'whiffs')
        self.assertEqual(whiff['count'], 1)
        self.assertEqual(whiff['total'], 1)

    def test_coordinates_rounded_to_one_decimal(self):
        df = _make_pitch_df([
            {'plate_x': 0.04, 'plate_z': 2.04, 'description': 'swinging_strike'},
            {'plate_x': 0.06, 'plate_z': 2.06, 'description': 'swinging_strike'},
        ])
        buckets = aggregate_buckets(df, BATTER_OUTCOMES)
        xs = {b['plate_x'] for b in buckets if b['outcome'] == 'whiffs'}
        # 0.04 rounds to 0.0, 0.06 rounds to 0.1 → two distinct buckets
        self.assertEqual(xs, {0.0, 0.1})


# ---------------------------------------------------------------------------
# Bulk path parity
# ---------------------------------------------------------------------------

class TestBulkPathParity(TestCase):
    """
    Verify that running aggregate_buckets on a per-player slice of the bulk
    DataFrame produces identical results to running it on the full DataFrame
    filtered by batter/pitcher — the two code paths are equivalent.
    """

    def _make_multi_player_df(self) -> pd.DataFrame:
        # Two batters, one pitcher, with batter column as float64 (CSV dtype)
        rows = [
            # batter 1001: 2 whiffs, 1 contact
            {'batter': np.float64(1001), 'pitcher': np.float64(9001), 'plate_x': 0.0, 'plate_z': 2.0,
             'description': 'swinging_strike', 'events': None},
            {'batter': np.float64(1001), 'pitcher': np.float64(9001), 'plate_x': 0.0, 'plate_z': 2.0,
             'description': 'swinging_strike', 'events': None},
            {'batter': np.float64(1001), 'pitcher': np.float64(9001), 'plate_x': 0.5, 'plate_z': 2.0,
             'description': 'hit_into_play',   'events': 'single'},
            # batter 1002: 1 whiff
            {'batter': np.float64(1002), 'pitcher': np.float64(9001), 'plate_x': 0.0, 'plate_z': 2.0,
             'description': 'swinging_strike', 'events': None},
            # stolen base — no batter/pitcher assignment (NaN rows common in real data)
            {'batter': np.nan,           'pitcher': np.nan,           'plate_x': 0.0, 'plate_z': 2.0,
             'description': 'ball',      'events': None},
        ]
        return pd.DataFrame([{
            'batter':      r['batter'],
            'pitcher':     r['pitcher'],
            'plate_x':     r['plate_x'],
            'plate_z':     r['plate_z'],
            'description': r['description'],
            'events':      r['events'],
        } for r in rows])

    def test_batter_slice_matches_per_player_filter(self):
        df = self._make_multi_player_df()

        target_mlbams = {1001, 1002}
        bat_df = df[df['batter'].isin(target_mlbams)]
        by_batter = {mlbam: g for mlbam, g in bat_df.groupby('batter')}

        # Per-player path: filter then aggregate
        per_player_1001 = aggregate_buckets(
            df[df['batter'] == np.float64(1001)].reset_index(drop=True),
            BATTER_OUTCOMES,
        )
        # Bulk path: groupby slice then aggregate (int key lookup)
        bulk_1001 = aggregate_buckets(by_batter.get(1001), BATTER_OUTCOMES)

        self.assertEqual(
            sorted(per_player_1001, key=lambda b: (b['outcome'], b['plate_x'], b['plate_z'])),
            sorted(bulk_1001,       key=lambda b: (b['outcome'], b['plate_x'], b['plate_z'])),
        )

    def test_float64_batter_column_isin_with_int_targets(self):
        """isin() must work when df['batter'] is float64 but target_mlbams is a set of ints."""
        df = self._make_multi_player_df()
        mask = df['batter'].isin({1001, 1002})
        self.assertEqual(mask.sum(), 4)  # 3 rows for 1001, 1 for 1002; NaN row excluded

    def test_int_key_lookup_against_float64_groupby_keys(self):
        """dict.get(int) must find a key stored as float64 via Python hash equality."""
        df = self._make_multi_player_df()
        bat_df = df[df['batter'].isin({1001})]
        by_batter = {mlbam: g for mlbam, g in bat_df.groupby('batter')}
        self.assertIsNotNone(by_batter.get(1001))   # int key finds float64 group key
        self.assertIsNone(by_batter.get(9999))      # missing key returns None

    def test_nan_rows_excluded_from_groups(self):
        """NaN batter rows (stolen bases etc.) must not appear in any group."""
        df = self._make_multi_player_df()
        bat_df = df[df['batter'].isin({1001, 1002})]
        by_batter = {mlbam: g for mlbam, g in bat_df.groupby('batter')}
        total_rows = sum(len(g) for g in by_batter.values())
        self.assertEqual(total_rows, 4)  # NaN row excluded


# ---------------------------------------------------------------------------
# write_buckets
# ---------------------------------------------------------------------------

class TestWriteBuckets(TestCase):
    def setUp(self):
        self.player = _make_player('troutmi01', 1001)

    def test_non_incremental_replaces_existing(self):
        StatcastZoneBucket.objects.create(
            player=self.player, role='B', outcome='whiffs',
            plate_x=0.0, plate_z=2.0, count=99, total=100,
        )
        buckets = [{'outcome': 'whiffs', 'plate_x': 0.0, 'plate_z': 2.0, 'count': 1, 'total': 5}]
        write_buckets(self.player, 'B', buckets, dry_run=False, incremental=False)
        row = StatcastZoneBucket.objects.get(player=self.player, role='B', outcome='whiffs')
        self.assertEqual(row.count, 1)
        self.assertEqual(row.total, 5)

    def test_incremental_adds_to_existing(self):
        StatcastZoneBucket.objects.create(
            player=self.player, role='B', outcome='whiffs',
            plate_x=0.0, plate_z=2.0, count=10, total=20,
        )
        buckets = [{'outcome': 'whiffs', 'plate_x': 0.0, 'plate_z': 2.0, 'count': 5, 'total': 5}]
        write_buckets(self.player, 'B', buckets, dry_run=False, incremental=True)
        row = StatcastZoneBucket.objects.get(player=self.player, role='B', outcome='whiffs')
        self.assertEqual(row.count, 15)
        self.assertEqual(row.total, 25)

    def test_incremental_inserts_new_location(self):
        buckets = [{'outcome': 'whiffs', 'plate_x': 1.0, 'plate_z': 3.0, 'count': 3, 'total': 7}]
        write_buckets(self.player, 'B', buckets, dry_run=False, incremental=True)
        self.assertTrue(
            StatcastZoneBucket.objects.filter(
                player=self.player, role='B', outcome='whiffs', plate_x=1.0
            ).exists()
        )

    def test_dry_run_writes_nothing(self):
        buckets = [{'outcome': 'whiffs', 'plate_x': 0.0, 'plate_z': 2.0, 'count': 5, 'total': 10}]
        write_buckets(self.player, 'B', buckets, dry_run=True, incremental=False)
        self.assertFalse(StatcastZoneBucket.objects.filter(player=self.player).exists())


# ---------------------------------------------------------------------------
# ingest_bulk
# ---------------------------------------------------------------------------

class TestIngestBulk(TestCase):
    def setUp(self):
        self.player = _make_player('troutmi01', 1001)
        BattingSeason.objects.create(player=self.player, year=2023, stint=1, team='LAA')

    def _bulk_df(self):
        return _make_pitch_df([
            {'batter': np.float64(1001), 'pitcher': np.float64(9001),
             'plate_x': 0.0, 'plate_z': 2.0, 'description': 'swinging_strike'},
            {'batter': np.float64(1001), 'pitcher': np.float64(9001),
             'plate_x': 0.0, 'plate_z': 2.0, 'description': 'hit_into_play', 'events': 'single'},
        ])

    @patch('pipeline.ingest_statcast_zones.statcast')
    def test_writes_buckets_for_target_player(self, mock_statcast):
        mock_statcast.return_value = self._bulk_df()
        targets = [(self.player, {'B'})]
        n = ingest_bulk(targets, '2024-05-01', '2024-05-08',
                        force=False, dry_run=False, verbose=False, incremental=True)
        self.assertGreater(n, 0)
        self.assertTrue(StatcastZoneBucket.objects.filter(player=self.player, role='B').exists())

    @patch('pipeline.ingest_statcast_zones.statcast')
    def test_skips_already_ingested_player(self, mock_statcast):
        mock_statcast.return_value = self._bulk_df()
        key = _source_key(self.player, 'B', incremental=True,
                          start_date='2024-05-01', end_date='2024-05-08')
        IngestionLog.objects.create(source=key, rows_loaded=5, status='success')

        ingest_bulk([(self.player, {'B'})], '2024-05-01', '2024-05-08',
                    force=False, dry_run=False, verbose=False, incremental=True)
        # statcast should not have been called since all players are already ingested
        mock_statcast.assert_not_called()

    @patch('pipeline.ingest_statcast_zones.statcast')
    def test_force_flag_overrides_skip(self, mock_statcast):
        mock_statcast.return_value = self._bulk_df()
        key = _source_key(self.player, 'B', incremental=True,
                          start_date='2024-05-01', end_date='2024-05-08')
        IngestionLog.objects.create(source=key, rows_loaded=5, status='success')

        ingest_bulk([(self.player, {'B'})], '2024-05-01', '2024-05-08',
                    force=True, dry_run=False, verbose=False, incremental=True)
        mock_statcast.assert_called_once()

    @patch('pipeline.ingest_statcast_zones.statcast')
    def test_dry_run_does_not_write(self, mock_statcast):
        mock_statcast.return_value = self._bulk_df()
        ingest_bulk([(self.player, {'B'})], '2024-05-01', '2024-05-08',
                    force=False, dry_run=True, verbose=False, incremental=True)
        self.assertFalse(StatcastZoneBucket.objects.filter(player=self.player).exists())

    @patch('pipeline.ingest_statcast_zones.statcast')
    def test_player_with_no_mlbam_skipped(self, mock_statcast):
        mock_statcast.return_value = self._bulk_df()
        no_mlbam = _make_player('nomlbam01', None)
        no_mlbam.mlbam_id = None
        no_mlbam.save()
        ingest_bulk([(no_mlbam, {'B'})], '2024-05-01', '2024-05-08',
                    force=False, dry_run=False, verbose=False, incremental=True)
        mock_statcast.assert_not_called()

    @patch('pipeline.ingest_statcast_zones.statcast')
    def test_empty_statcast_response_handled(self, mock_statcast):
        mock_statcast.return_value = pd.DataFrame()
        n = ingest_bulk([(self.player, {'B'})], '2024-05-01', '2024-05-08',
                        force=False, dry_run=False, verbose=False, incremental=True)
        self.assertEqual(n, 0)

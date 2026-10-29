"""
Tests for pipeline/ingest_statcast_zones.py.

Covers:
  - aggregate_cells correctness, on the heatmap's grid
  - bulk path parity: groupby slice produces identical cells to per-player filter
  - float64 batter/pitcher dtype tolerance (statcast CSV uses float64 when NaN rows present)
  - ingest_bulk: skips already-ingested, logs success/error

Run from project root:
    python -m pytest pipeline/test_statcast_zones.py -v
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pca_backend.settings")

from datetime import date
from unittest.mock import patch

import numpy as np
import pandas as pd
from django.db import OperationalError
from django.test import TestCase
from django.urls import reverse

from pipeline.ingest_statcast_zones import (
    _source_key,
    aggregate_cells,
    cell_index,
    ingest_bulk,
    main,
    players_by_war,
    write_cells,
    write_cells_retrying,
)
from players.models import Player
from stats.models import BattingSeason, IngestionLog, PitchingSeason, StatcastZoneCell

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_pitch_df(rows: list[dict]) -> pd.DataFrame:
    """Build a minimal statcast-shaped DataFrame from a list of row dicts."""
    defaults = {
        "batter": np.float64(0),
        "pitcher": np.float64(0),
        "plate_x": 0.0,
        "plate_z": 2.5,
        "description": "ball",
        "events": None,
        "game_date": date(2024, 5, 1),
        "game_year": 2024,
    }
    return pd.DataFrame([{**defaults, **r} for r in rows])


class FakeSavant:
    def __init__(self, pitches: pd.DataFrame):
        self.pitches = pitches

    def statcast(self, start_dt: str, end_dt: str, **_kwargs) -> pd.DataFrame:
        game_date = self.pitches["game_date"]
        in_window = (game_date >= date.fromisoformat(start_dt)) & (game_date <= date.fromisoformat(end_dt))
        return self.pitches[in_window].reset_index(drop=True)


def _frozen_date(today: date) -> type[date]:
    class FrozenDate(date):
        @classmethod
        def today(cls) -> date:
            return today

    return FrozenDate


def _make_player(bbref_id: str, mlbam_id: int) -> Player:
    p, _ = Player.objects.update_or_create(
        bbref_id=bbref_id,
        defaults={"first_name": "Test", "last_name": "Player", "mlbam_id": mlbam_id},
    )
    return p


# ---------------------------------------------------------------------------
# aggregate_cells
# ---------------------------------------------------------------------------


def _cell(season: int, cell_x: int, cell_z: int, pitches: int, contact: int = 0, hits: int = 0, whiffs: int = 0) -> dict:
    return {"season": season, "cell_x": cell_x, "cell_z": cell_z, "pitches": pitches, "contact": contact, "hits": hits, "whiffs": whiffs}


class TestAggregateCells(TestCase):
    def test_counts_every_pitch_and_each_outcome_in_a_cell(self):
        df = _make_pitch_df(
            [
                {"plate_x": 0.0, "plate_z": 2.0, "description": "swinging_strike"},
                {"plate_x": 0.0, "plate_z": 2.0, "description": "swinging_strike"},
                {"plate_x": 0.0, "plate_z": 2.0, "description": "ball"},
                {"plate_x": 0.05, "plate_z": 2.0, "description": "hit_into_play", "events": "double"},
            ]
        )
        self.assertEqual(aggregate_cells(df), [_cell(2024, 10, 13, 4, contact=1, hits=1, whiffs=2)])

    def test_a_cell_where_no_outcome_happened_keeps_its_pitches(self):
        df = _make_pitch_df([{"plate_x": 1.0, "plate_z": 1.0, "description": "ball"}])
        self.assertEqual(aggregate_cells(df), [_cell(2024, 15, 17, 1)])

    def test_empty_dataframe_returns_empty_list(self):
        self.assertEqual(aggregate_cells(pd.DataFrame()), [])
        self.assertEqual(aggregate_cells(None), [])

    def test_drops_rows_missing_plate_coordinates(self):
        df = _make_pitch_df(
            [
                {"plate_x": np.nan, "plate_z": 2.0, "description": "swinging_strike"},
                {"plate_x": 0.0, "plate_z": 2.0, "description": "swinging_strike"},
            ]
        )
        self.assertEqual(aggregate_cells(df), [_cell(2024, 10, 13, 1, whiffs=1)])

    def test_cells_are_the_heatmaps(self):
        # PitchZone.tsx: 20 cells over x -2.0 to 2.0 and z 5.0 down to 0.5, left edge and top edge inclusive.
        cell_x, cell_z = cell_index(pd.Series([-2.0, 1.99, 2.0, 0.0]), pd.Series([5.0, 0.51, 0.5, 2.75]))
        self.assertEqual(list(cell_x), [0, 19, 20, 10])
        self.assertEqual(list(cell_z), [0, 19, 20, 10])

    def test_keeps_pitches_outside_the_grid_in_cells_beyond_it(self):
        df = _make_pitch_df([{"plate_x": -5.1, "plate_z": 9.6, "description": "ball"}])
        self.assertEqual(aggregate_cells(df), [_cell(2024, -16, -21, 1)])

    def test_splits_seasons(self):
        df = _make_pitch_df(
            [
                {"plate_x": 0.0, "plate_z": 2.0, "description": "swinging_strike", "game_year": 2023},
                {"plate_x": 0.0, "plate_z": 2.0, "description": "ball", "game_year": 2024},
            ]
        )
        self.assertEqual(aggregate_cells(df), [_cell(2023, 10, 13, 1, whiffs=1), _cell(2024, 10, 13, 1)])


# ---------------------------------------------------------------------------
# Bulk path parity
# ---------------------------------------------------------------------------


class TestBulkPathParity(TestCase):
    """
    Verify that running aggregate_cells on a per-player slice of the bulk
    DataFrame produces identical results to running it on the full DataFrame
    filtered by batter/pitcher — the two code paths are equivalent.
    """

    def _make_multi_player_df(self) -> pd.DataFrame:
        # Two batters, one pitcher, with batter column as float64 (CSV dtype)
        rows = [
            # batter 1001: 2 whiffs, 1 contact
            {
                "batter": np.float64(1001),
                "pitcher": np.float64(9001),
                "plate_x": 0.0,
                "plate_z": 2.0,
                "description": "swinging_strike",
                "events": None,
            },
            {
                "batter": np.float64(1001),
                "pitcher": np.float64(9001),
                "plate_x": 0.0,
                "plate_z": 2.0,
                "description": "swinging_strike",
                "events": None,
            },
            {
                "batter": np.float64(1001),
                "pitcher": np.float64(9001),
                "plate_x": 0.5,
                "plate_z": 2.0,
                "description": "hit_into_play",
                "events": "single",
            },
            # batter 1002: 1 whiff
            {
                "batter": np.float64(1002),
                "pitcher": np.float64(9001),
                "plate_x": 0.0,
                "plate_z": 2.0,
                "description": "swinging_strike",
                "events": None,
            },
            # stolen base — no batter/pitcher assignment (NaN rows common in real data)
            {
                "batter": np.nan,
                "pitcher": np.nan,
                "plate_x": 0.0,
                "plate_z": 2.0,
                "description": "ball",
                "events": None,
            },
        ]
        return _make_pitch_df(rows)

    def test_batter_slice_matches_per_player_filter(self):
        df = self._make_multi_player_df()

        target_mlbams = {1001, 1002}
        bat_df = df[df["batter"].isin(target_mlbams)]
        by_batter = {mlbam: g for mlbam, g in bat_df.groupby("batter")}

        # Per-player path: filter then aggregate
        per_player_1001 = aggregate_cells(df[df["batter"] == np.float64(1001)].reset_index(drop=True))
        # Bulk path: groupby slice then aggregate (int key lookup)
        bulk_1001 = aggregate_cells(by_batter.get(1001))

        self.assertEqual(per_player_1001, bulk_1001)
        self.assertEqual(sum(c["pitches"] for c in bulk_1001), 3)

    def test_float64_batter_column_isin_with_int_targets(self):
        """isin() must work when df['batter'] is float64 but target_mlbams is a set of ints."""
        df = self._make_multi_player_df()
        mask = df["batter"].isin({1001, 1002})
        self.assertEqual(mask.sum(), 4)  # 3 rows for 1001, 1 for 1002; NaN row excluded

    def test_int_key_lookup_against_float64_groupby_keys(self):
        """dict.get(int) must find a key stored as float64 via Python hash equality."""
        df = self._make_multi_player_df()
        bat_df = df[df["batter"].isin({1001})]
        by_batter = {mlbam: g for mlbam, g in bat_df.groupby("batter")}
        self.assertIsNotNone(by_batter.get(1001))  # int key finds float64 group key
        self.assertIsNone(by_batter.get(9999))  # missing key returns None

    def test_nan_rows_excluded_from_groups(self):
        """NaN batter rows (stolen bases etc.) must not appear in any group."""
        df = self._make_multi_player_df()
        bat_df = df[df["batter"].isin({1001, 1002})]
        by_batter = {mlbam: g for mlbam, g in bat_df.groupby("batter")}
        total_rows = sum(len(g) for g in by_batter.values())
        self.assertEqual(total_rows, 4)  # NaN row excluded


# ---------------------------------------------------------------------------
# write_cells
# ---------------------------------------------------------------------------


class TestWriteCells(TestCase):
    def setUp(self):
        self.player = _make_player("troutmi01", 1001)

    def _stored(self) -> list[tuple[int, int, int]]:
        rows = StatcastZoneCell.objects.filter(player=self.player, role="B").order_by("season")
        return [(r.season, r.whiffs, r.pitches) for r in rows]

    def test_replaces_written_season(self):
        write_cells(self.player, "B", [_cell(2024, 10, 13, 100, whiffs=99)], dry_run=False)
        write_cells(self.player, "B", [_cell(2024, 10, 13, 5, whiffs=1)], dry_run=False)
        self.assertEqual(self._stored(), [(2024, 1, 5)])

    def test_keeps_other_seasons(self):
        write_cells(self.player, "B", [_cell(2023, 10, 13, 20, whiffs=10)], dry_run=False)
        write_cells(self.player, "B", [_cell(2024, 10, 13, 5, whiffs=5)], dry_run=False)
        self.assertEqual(self._stored(), [(2023, 10, 20), (2024, 5, 5)])

    def test_dry_run_writes_nothing(self):
        write_cells(self.player, "B", [_cell(2024, 10, 13, 10, whiffs=5)], dry_run=True)
        self.assertFalse(StatcastZoneCell.objects.filter(player=self.player).exists())

    def test_reconnects_and_retries_once_after_a_dropped_connection(self):
        calls = []

        def drops_once(*args, **kwargs):
            calls.append(1)
            if len(calls) == 1:
                raise OperationalError("server closed the connection unexpectedly")
            return write_cells(*args, **kwargs)

        with (
            patch("pipeline.ingest_statcast_zones.write_cells", side_effect=drops_once),
            patch("pipeline.ingest_statcast_zones.close_old_connections") as reconnect,
        ):
            n = write_cells_retrying(self.player, "B", [_cell(2024, 10, 13, 5, whiffs=1)], dry_run=False)
        self.assertEqual((n, len(calls), reconnect.call_count), (1, 2, 1))
        self.assertEqual(self._stored(), [(2024, 1, 5)])


# ---------------------------------------------------------------------------
# ingest_bulk
# ---------------------------------------------------------------------------


class TestIngestBulk(TestCase):
    def setUp(self):
        self.player = _make_player("troutmi01", 1001)
        BattingSeason.objects.create(player=self.player, year=2023, stint=1, team="LAA")

    def _bulk_df(self):
        return _make_pitch_df(
            [
                {
                    "batter": np.float64(1001),
                    "pitcher": np.float64(9001),
                    "plate_x": 0.0,
                    "plate_z": 2.0,
                    "description": "swinging_strike",
                },
                {
                    "batter": np.float64(1001),
                    "pitcher": np.float64(9001),
                    "plate_x": 0.0,
                    "plate_z": 2.0,
                    "description": "hit_into_play",
                    "events": "single",
                },
            ]
        )

    @patch("pipeline.ingest_statcast_zones.statcast")
    def test_writes_cells_for_target_player(self, mock_statcast):
        mock_statcast.side_effect = FakeSavant(self._bulk_df()).statcast
        ingest_bulk([(self.player, {"B"})], 2024, force=False, dry_run=False, verbose=False)
        stored = StatcastZoneCell.objects.filter(player=self.player, role="B").values_list(
            "season", "pitches", "contact", "hits", "whiffs"
        )
        self.assertEqual(list(stored), [(2024, 2, 1, 1, 1)])

    @patch("pipeline.ingest_statcast_zones.statcast")
    def test_skips_already_ingested_player(self, mock_statcast):
        mock_statcast.return_value = self._bulk_df()
        key = _source_key(self.player, "B", 2024)
        IngestionLog.objects.create(source=key, rows_loaded=5, status="success")

        ingest_bulk([(self.player, {"B"})], 2024, force=False, dry_run=False, verbose=False)
        # statcast should not have been called since all players are already ingested
        mock_statcast.assert_not_called()

    @patch("pipeline.ingest_statcast_zones.statcast")
    def test_force_flag_overrides_skip(self, mock_statcast):
        mock_statcast.side_effect = FakeSavant(self._bulk_df()).statcast
        key = _source_key(self.player, "B", 2024)
        IngestionLog.objects.create(source=key, rows_loaded=5, status="success")

        n = ingest_bulk([(self.player, {"B"})], 2024, force=True, dry_run=False, verbose=False)
        self.assertEqual(n, 1)

    @patch("pipeline.ingest_statcast_zones.statcast")
    def test_dry_run_does_not_write(self, mock_statcast):
        mock_statcast.return_value = self._bulk_df()
        ingest_bulk([(self.player, {"B"})], 2024, force=False, dry_run=True, verbose=False)
        self.assertFalse(StatcastZoneCell.objects.filter(player=self.player).exists())

    @patch("pipeline.ingest_statcast_zones.statcast")
    def test_player_with_no_mlbam_skipped(self, mock_statcast):
        mock_statcast.return_value = self._bulk_df()
        no_mlbam = _make_player("nomlbam01", None)
        no_mlbam.mlbam_id = None
        no_mlbam.save()
        ingest_bulk([(no_mlbam, {"B"})], 2024, force=False, dry_run=False, verbose=False)
        mock_statcast.assert_not_called()

    @patch("pipeline.ingest_statcast_zones.statcast")
    def test_empty_statcast_response_handled(self, mock_statcast):
        mock_statcast.return_value = pd.DataFrame()
        n = ingest_bulk([(self.player, {"B"})], 2024, force=False, dry_run=False, verbose=False)
        self.assertEqual(n, 0)


# ---------------------------------------------------------------------------
# players_by_war
# ---------------------------------------------------------------------------


class TestPlayersByWar(TestCase):
    """
    Active-bypass behaviour: rookies and callups should appear in the target
    list when they meet the current-year PA/BFP threshold, even with zero
    career WAR.
    """

    def setUp(self):
        # Veteran with high career WAR — passes the WAR filter
        self.vet = _make_player("vetbatt01", 1001)
        BattingSeason.objects.create(
            player=self.vet, year=2020, stint=1, team="LAA",
            war=8.0, plate_appearances=600,
        )

        # Rookie with zero career WAR, active in 2026 above threshold
        self.rookie = _make_player("rookiebat01", 1002)
        BattingSeason.objects.create(
            player=self.rookie, year=2026, stint=1, team="NYM",
            war=0.5, plate_appearances=120,
        )

        # Bench player active in 2026 but below threshold
        self.bench = _make_player("benchbat01", 1003)
        BattingSeason.objects.create(
            player=self.bench, year=2026, stint=1, team="CHC",
            war=0.0, plate_appearances=10,
        )

        # Pitcher rookie active in 2026
        self.pitcher_rookie = _make_player("rookiepit01", 1004)
        PitchingSeason.objects.create(
            player=self.pitcher_rookie, year=2026, stint=1, team="SFG",
            war=0.3, bfp=200,
        )

    def _ids(self, results):
        return {p.bbref_id for p, _ in results}

    def test_war_only_excludes_rookies_when_current_year_disabled(self):
        results = players_by_war(min_war=5.0, roles={"B", "P"}, current_year=None)
        ids = self._ids(results)
        self.assertIn("vetbatt01", ids)
        self.assertNotIn("rookiebat01", ids)
        self.assertNotIn("benchbat01", ids)
        self.assertNotIn("rookiepit01", ids)

    def test_active_bypass_includes_rookies_above_pa_threshold(self):
        results = players_by_war(
            min_war=5.0, roles={"B", "P"},
            current_year=2026, active_min_pa=50, active_min_bfp=50,
        )
        ids = self._ids(results)
        self.assertIn("vetbatt01", ids)         # WAR path
        self.assertIn("rookiebat01", ids)       # active-PA bypass
        self.assertIn("rookiepit01", ids)       # active-BFP bypass
        self.assertNotIn("benchbat01", ids)     # below PA threshold

    def test_active_bypass_assigns_correct_roles(self):
        results = players_by_war(
            min_war=5.0, roles={"B", "P"}, current_year=2026,
        )
        roles_by_id = {p.bbref_id: roles for p, roles in results}
        self.assertEqual(roles_by_id["rookiebat01"], {"B"})
        self.assertEqual(roles_by_id["rookiepit01"], {"P"})

    def test_active_bypass_respects_roles_filter(self):
        results = players_by_war(
            min_war=5.0, roles={"B"}, current_year=2026,
        )
        ids = self._ids(results)
        self.assertIn("rookiebat01", ids)
        self.assertNotIn("rookiepit01", ids)    # filtered by roles={'B'}


class TestWeeklyRefresh(TestCase):
    def setUp(self):
        self.player = _make_player("troutmi01", 1001)
        BattingSeason.objects.create(
            player=self.player, year=2026, stint=1, team="LAA", war=6.0, plate_appearances=600,
        )
        self.savant = FakeSavant(
            _make_pitch_df(
                [
                    {
                        "batter": np.float64(1001),
                        "pitcher": np.float64(9001),
                        "plate_x": 0.0,
                        "plate_z": 2.0,
                        "description": "swinging_strike",
                        "game_date": day,
                        "game_year": day.year,
                    }
                    for day in pd.date_range("2026-09-02", "2026-09-21").date
                ]
            )
        )

    def _run_weekly_refresh(self, monday: date) -> None:
        argv = ["ingest_statcast_zones.py", "--season", str(monday.year), "--min-war", "5.0"]
        with (
            patch("sys.argv", argv),
            patch("pipeline.ingest_statcast_zones.date", _frozen_date(monday)),
            patch("pipeline.ingest_statcast_zones.statcast", self.savant.statcast),
        ):
            main()

    def _whiff_buckets(self) -> list[dict]:
        r = self.client.get(
            reverse("player-pitch-zone", kwargs={"pk": "troutmi01"}), {"role": "B", "outcome": "whiffs"}
        )
        return r.json()["buckets"]

    def test_overlapping_weekly_windows_count_each_pitch_once(self):
        self._run_weekly_refresh(date(2026, 9, 14))
        self._run_weekly_refresh(date(2026, 9, 21))
        self._run_weekly_refresh(date(2026, 9, 21))

        self.assertEqual(self._whiff_buckets(), [{"plate_x": 0.1, "plate_z": 1.9625, "count": 20, "total": 20}])

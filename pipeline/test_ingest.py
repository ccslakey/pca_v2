"""
Tests for pipeline/ingest_bref_history.py.

Run from project root:
    python -m pytest pipeline/test_ingest.py -v
"""

from __future__ import annotations

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

# Ensure project root is on sys.path so Django apps are importable when
# running this file directly (pytest-django handles DJANGO_SETTINGS_MODULE
# via conftest.py, but direct invocation needs it set explicitly).
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pca_backend.settings')

import requests
from django.test import TestCase

from players.models import Player
from stats.models import BattingSeason, PitchingSeason, IngestionLog
from pipeline.ingest_bref_history import (
    ip_to_outs,
    to_int,
    to_float,
    parse_name,
    league_urls,
    extract_table,
    upsert_player,
    fetch_with_retry,
    ingest_batting_page,
    ingest_pitching_page,
    already_ingested,
    log_success,
    log_error,
)


# ---------------------------------------------------------------------------
# HTML fixture builders
# ---------------------------------------------------------------------------

def _batting_html(rows: list[dict], in_comment: bool = False) -> bytes:
    """Build minimal BRef-style batting table HTML bytes."""
    tr_parts: list[str] = []
    for r in rows:
        cells = [
            f'<th data-stat="name_display" data-append-csv="{r["bbref_id"]}">'
            f'{r.get("name", "Test Player")}</th>',
            f'<td data-stat="team_name_abbr">{r.get("team", "TST")}</td>',
        ]
        for stat, val in r.get('stats', {}).items():
            cells.append(f'<td data-stat="{stat}">{val}</td>')
        tr_parts.append(f'<tr>{"".join(cells)}</tr>')

    table = (
        f'<table id="players_standard_batting">'
        f'<tbody>{"".join(tr_parts)}</tbody>'
        f'</table>'
    )
    body = f'<!--{table}-->' if in_comment else table
    return f'<html><body>{body}</body></html>'.encode()


def _pitching_html(rows: list[dict], in_comment: bool = False) -> bytes:
    """Build minimal BRef-style pitching table HTML bytes."""
    tr_parts: list[str] = []
    for r in rows:
        cells = [
            f'<th data-stat="name_display" data-append-csv="{r["bbref_id"]}">'
            f'{r.get("name", "Test Pitcher")}</th>',
            f'<td data-stat="team_name_abbr">{r.get("team", "TST")}</td>',
        ]
        for stat, val in r.get('stats', {}).items():
            cells.append(f'<td data-stat="{stat}">{val}</td>')
        tr_parts.append(f'<tr>{"".join(cells)}</tr>')

    table = (
        f'<table id="players_standard_pitching">'
        f'<tbody>{"".join(tr_parts)}</tbody>'
        f'</table>'
    )
    body = f'<!--{table}-->' if in_comment else table
    return f'<html><body>{body}</body></html>'.encode()


def _mock_response(content: bytes) -> MagicMock:
    r = MagicMock()
    r.content = content
    return r


EMPTY_CHADWICK: dict = {}

CHADWICK_WITH_RUTH: dict = {
    'ruthba01': {'mlbam_id': 1234, 'fangraphs_id': 5678, 'retro_id': 'ruth001'},
}


# ---------------------------------------------------------------------------
# Pure function tests — no DB, no network
# ---------------------------------------------------------------------------

class TestIpToOuts(unittest.TestCase):

    def test_whole_innings(self) -> None:
        self.assertEqual(ip_to_outs('9'), 27)
        self.assertEqual(ip_to_outs('0'), 0)
        self.assertEqual(ip_to_outs('1'), 3)

    def test_partial_innings(self) -> None:
        self.assertEqual(ip_to_outs('6.1'), 19)
        self.assertEqual(ip_to_outs('6.2'), 20)
        self.assertEqual(ip_to_outs('0.1'), 1)
        self.assertEqual(ip_to_outs('0.2'), 2)

    def test_numeric_input(self) -> None:
        self.assertEqual(ip_to_outs(9), 27)
        self.assertEqual(ip_to_outs(6.1), 19)

    def test_empty_and_sentinel_values(self) -> None:
        self.assertIsNone(ip_to_outs(''))
        self.assertIsNone(ip_to_outs('--'))
        self.assertIsNone(ip_to_outs(None))


class TestToInt(unittest.TestCase):

    def test_integer_strings(self) -> None:
        self.assertEqual(to_int('5'), 5)
        self.assertEqual(to_int('0'), 0)
        self.assertEqual(to_int('  42  '), 42)

    def test_float_string_truncates(self) -> None:
        self.assertEqual(to_int('5.0'), 5)
        self.assertEqual(to_int('12.9'), 12)

    def test_sentinel_values(self) -> None:
        self.assertIsNone(to_int(''))
        self.assertIsNone(to_int('--'))
        self.assertIsNone(to_int('NA'))
        self.assertIsNone(to_int(None))


class TestToFloat(unittest.TestCase):

    def test_float_strings(self) -> None:
        self.assertAlmostEqual(to_float('.356'), 0.356, places=3)
        self.assertAlmostEqual(to_float('3.14'), 3.14, places=2)
        self.assertAlmostEqual(to_float('0.0'), 0.0)

    def test_sentinel_values(self) -> None:
        self.assertIsNone(to_float(''))
        self.assertIsNone(to_float('--'))
        self.assertIsNone(to_float('NA'))
        self.assertIsNone(to_float(None))


class TestParseName(unittest.TestCase):

    def test_firstname_lastname(self) -> None:
        self.assertEqual(parse_name('Babe Ruth'), ('Babe', 'Ruth'))
        self.assertEqual(parse_name('Juan Pierre'), ('Juan', 'Pierre'))

    def test_multiword_first_name(self) -> None:
        self.assertEqual(parse_name('Joe Nathan Smith'), ('Joe Nathan', 'Smith'))

    def test_comma_format(self) -> None:
        self.assertEqual(parse_name('Ruth, Babe'), ('Babe', 'Ruth'))
        self.assertEqual(parse_name('Ohtani, Shohei'), ('Shohei', 'Ohtani'))

    def test_strips_hof_and_active_markers(self) -> None:
        self.assertEqual(parse_name('Babe Ruth*'), ('Babe', 'Ruth'))
        self.assertEqual(parse_name('Ruth, Babe*'), ('Babe', 'Ruth'))
        self.assertEqual(parse_name('Player, Active#'), ('Active', 'Player'))

    def test_single_word_name(self) -> None:
        first, last = parse_name('Satchel')
        self.assertEqual(first, 'Satchel')
        self.assertEqual(last, '')


class TestLeagueUrls(unittest.TestCase):

    def _urls(self, stat_type: str, start: int, end: int) -> list[tuple[int, str, str]]:
        return list(league_urls(stat_type, start, end))

    def test_modern_year_yields_mlb_only(self) -> None:
        results = self._urls('batting', 2024, 2024)
        self.assertEqual(len(results), 1)
        year, league, url = results[0]
        self.assertEqual(year, 2024)
        self.assertEqual(league, 'MLB')
        self.assertIn('/MLB/2024-standard-batting.shtml', url)

    def test_1901_yields_mlb_only(self) -> None:
        leagues = {r[1] for r in self._urls('batting', 1901, 1901)}
        self.assertEqual(leagues, {'MLB'})

    def test_1900_yields_nl_not_mlb(self) -> None:
        leagues = {r[1] for r in self._urls('batting', 1900, 1900)}
        self.assertIn('NL', leagues)
        self.assertNotIn('MLB', leagues)

    def test_1884_yields_nl_aa_ua(self) -> None:
        leagues = {r[1] for r in self._urls('batting', 1884, 1884)}
        self.assertIn('NL', leagues)
        self.assertIn('AA', leagues)
        self.assertIn('UA', leagues)

    def test_1890_yields_nl_aa_pl(self) -> None:
        leagues = {r[1] for r in self._urls('batting', 1890, 1890)}
        self.assertIn('NL', leagues)
        self.assertIn('AA', leagues)
        self.assertIn('PL', leagues)

    def test_1871_yields_na_only(self) -> None:
        leagues = {r[1] for r in self._urls('pitching', 1871, 1871)}
        self.assertEqual(leagues, {'NA'})

    def test_stat_type_in_url(self) -> None:
        _, _, url = self._urls('pitching', 2020, 2020)[0]
        self.assertIn('pitching', url)

    def test_empty_range_yields_nothing(self) -> None:
        self.assertEqual(self._urls('batting', 2024, 2023), [])


class TestExtractTable(unittest.TestCase):

    def test_visible_table(self) -> None:
        html = _batting_html([
            {'bbref_id': 'ruthba01', 'name': 'Babe Ruth', 'team': 'NYY',
             'stats': {'b_hr': '60', 'b_games': '154'}},
        ])
        df = extract_table(html, 'players_standard_batting')
        self.assertEqual(len(df), 1)
        self.assertEqual(df.iloc[0]['bbref_id'], 'ruthba01')
        self.assertEqual(df.iloc[0]['b_hr'], '60')

    def test_comment_embedded_table(self) -> None:
        html = _batting_html([
            {'bbref_id': 'bondsba01', 'name': 'Barry Bonds', 'team': 'SFG',
             'stats': {'b_hr': '73'}},
        ], in_comment=True)
        df = extract_table(html, 'players_standard_batting')
        self.assertEqual(len(df), 1)
        self.assertEqual(df.iloc[0]['bbref_id'], 'bondsba01')

    def test_missing_table_returns_empty_dataframe(self) -> None:
        html = b'<html><body><p>No table here</p></body></html>'
        df = extract_table(html, 'players_standard_batting')
        self.assertTrue(df.empty)

    def test_multiple_rows_preserved_in_order(self) -> None:
        html = _batting_html([
            {'bbref_id': 'ruthba01', 'team': 'NYY'},
            {'bbref_id': 'gehriglo01', 'team': 'NYY'},
            {'bbref_id': 'dimagjo01', 'team': 'NYY'},
        ])
        df = extract_table(html, 'players_standard_batting')
        self.assertEqual(len(df), 3)
        self.assertListEqual(list(df['bbref_id']), ['ruthba01', 'gehriglo01', 'dimagjo01'])

    def test_team_name_abbr_column_present(self) -> None:
        html = _batting_html([{'bbref_id': 'ruthba01', 'team': 'NYY'}])
        df = extract_table(html, 'players_standard_batting')
        self.assertIn('team_name_abbr', df.columns)
        self.assertEqual(df.iloc[0]['team_name_abbr'], 'NYY')

    def test_wrong_table_id_returns_empty(self) -> None:
        html = _batting_html([{'bbref_id': 'ruthba01'}])
        df = extract_table(html, 'players_standard_pitching')
        self.assertTrue(df.empty)


# ---------------------------------------------------------------------------
# Network / retry tests — no DB
# ---------------------------------------------------------------------------

class TestFetchWithRetry(unittest.TestCase):

    def test_success_on_first_attempt(self) -> None:
        mock_session = MagicMock()
        expected = MagicMock()
        mock_session.get.return_value = expected

        result = fetch_with_retry(mock_session, 'http://example.com')

        self.assertIs(result, expected)
        mock_session.get.assert_called_once_with('http://example.com')

    def test_retries_on_connection_error(self) -> None:
        mock_session = MagicMock()
        success = MagicMock()
        mock_session.get.side_effect = [
            requests.exceptions.ConnectionError('reset'),
            success,
        ]

        with patch('time.sleep'):
            result = fetch_with_retry(mock_session, 'http://example.com', retries=3, backoff=1)

        self.assertIs(result, success)
        self.assertEqual(mock_session.get.call_count, 2)

    def test_retries_on_timeout(self) -> None:
        mock_session = MagicMock()
        success = MagicMock()
        mock_session.get.side_effect = [
            requests.exceptions.Timeout(),
            requests.exceptions.Timeout(),
            success,
        ]

        with patch('time.sleep') as mock_sleep:
            result = fetch_with_retry(mock_session, 'http://example.com', retries=3, backoff=10)

        self.assertIs(result, success)
        # backoff * attempt: 10*1=10s, 10*2=20s
        mock_sleep.assert_any_call(10)
        mock_sleep.assert_any_call(20)

    def test_raises_after_all_retries_exhausted(self) -> None:
        mock_session = MagicMock()
        mock_session.get.side_effect = requests.exceptions.ConnectionError('reset')

        with patch('time.sleep'):
            with self.assertRaises(requests.exceptions.ConnectionError):
                fetch_with_retry(mock_session, 'http://example.com', retries=3, backoff=1)

        self.assertEqual(mock_session.get.call_count, 3)


# ---------------------------------------------------------------------------
# DB tests — use Django TestCase for transaction isolation
# ---------------------------------------------------------------------------

class TestUpsertPlayer(TestCase):

    def test_creates_new_player(self) -> None:
        player = upsert_player('ruthba01', 'Babe Ruth', CHADWICK_WITH_RUTH, dry_run=False)
        self.assertIsNotNone(player)
        self.assertEqual(player.first_name, 'Babe')
        self.assertEqual(player.last_name, 'Ruth')
        self.assertEqual(player.mlbam_id, 1234)
        self.assertEqual(player.fangraphs_id, 5678)
        self.assertEqual(player.retro_id, 'ruth001')
        self.assertTrue(Player.objects.filter(bbref_id='ruthba01').exists())

    def test_updates_existing_player(self) -> None:
        Player.objects.create(bbref_id='ruthba01', first_name='Old', last_name='Name')
        player = upsert_player('ruthba01', 'Babe Ruth', EMPTY_CHADWICK, dry_run=False)
        self.assertEqual(player.first_name, 'Babe')
        self.assertEqual(Player.objects.filter(bbref_id='ruthba01').count(), 1)

    def test_dry_run_does_not_persist(self) -> None:
        player = upsert_player('ruthba01', 'Babe Ruth', EMPTY_CHADWICK, dry_run=True)
        self.assertIsNotNone(player)
        self.assertFalse(Player.objects.filter(bbref_id='ruthba01').exists())

    def test_empty_bbref_id_returns_none(self) -> None:
        result = upsert_player('', 'Nobody', EMPTY_CHADWICK, dry_run=False)
        self.assertIsNone(result)

    def test_no_chadwick_entry_leaves_ids_null(self) -> None:
        player = upsert_player('unknownpl01', 'Unknown Player', EMPTY_CHADWICK, dry_run=False)
        self.assertIsNone(player.mlbam_id)
        self.assertIsNone(player.fangraphs_id)
        self.assertIsNone(player.retro_id)


class TestIngestionLog(TestCase):

    def test_already_ingested_false_when_no_log(self) -> None:
        self.assertFalse(already_ingested('bref_batting_MLB_1927'))

    def test_already_ingested_false_for_error_log(self) -> None:
        IngestionLog.objects.create(
            source='bref_batting_MLB_1927', rows_loaded=0,
            status='error', error_msg='oops',
        )
        self.assertFalse(already_ingested('bref_batting_MLB_1927'))

    def test_already_ingested_true_for_success_log(self) -> None:
        IngestionLog.objects.create(
            source='bref_batting_MLB_1927', rows_loaded=500, status='success',
        )
        self.assertTrue(already_ingested('bref_batting_MLB_1927'))

    def test_log_success_creates_record(self) -> None:
        log_success('bref_batting_MLB_1927', 500)
        log = IngestionLog.objects.get(source='bref_batting_MLB_1927')
        self.assertEqual(log.status, 'success')
        self.assertEqual(log.rows_loaded, 500)

    def test_log_error_stores_message(self) -> None:
        log_error('bref_batting_MLB_1927', ValueError('something broke'))
        log = IngestionLog.objects.get(source='bref_batting_MLB_1927')
        self.assertEqual(log.status, 'error')
        self.assertIn('something broke', log.error_msg)


class TestIngestBattingPage(TestCase):

    @patch('pipeline.ingest_bref_history.fetch_with_retry')
    def test_creates_batting_season_with_correct_fields(self, mock_fetch: MagicMock) -> None:
        html = _batting_html([{
            'bbref_id': 'ruthba01', 'name': 'Babe Ruth', 'team': 'NYY',
            'stats': {
                'b_games': '154', 'b_pa': '600', 'b_ab': '536',
                'b_hr': '60', 'b_rbi': '164',
                'b_batting_avg': '.356', 'b_war': '12.4',
            },
        }])
        mock_fetch.return_value = _mock_response(html)

        rows = ingest_batting_page(
            MagicMock(), 1927, 'MLB', 'http://example.com',
            EMPTY_CHADWICK, dry_run=False, verbose=False,
        )

        self.assertEqual(rows, 1)
        season = BattingSeason.objects.get(player_id='ruthba01', year=1927, stint=1)
        self.assertEqual(season.team, 'NYY')
        self.assertEqual(season.games, 154)
        self.assertEqual(season.home_runs, 60)
        self.assertEqual(season.rbi, 164)
        self.assertAlmostEqual(season.batting_avg, 0.356, places=3)
        self.assertAlmostEqual(season.war, 12.4, places=1)

    @patch('pipeline.ingest_bref_history.fetch_with_retry')
    def test_filters_multi_team_total_rows(self, mock_fetch: MagicMock) -> None:
        html = _batting_html([
            {'bbref_id': 'tradedpl01', 'name': 'Traded Player', 'team': 'NYY',
             'stats': {'b_hr': '20'}},
            {'bbref_id': 'tradedpl01', 'name': 'Traded Player', 'team': 'BOS',
             'stats': {'b_hr': '10'}},
            {'bbref_id': 'tradedpl01', 'name': 'Traded Player', 'team': '2TM',
             'stats': {'b_hr': '30'}},
        ])
        mock_fetch.return_value = _mock_response(html)

        rows = ingest_batting_page(
            MagicMock(), 2000, 'MLB', 'http://example.com',
            EMPTY_CHADWICK, dry_run=False, verbose=False,
        )

        self.assertEqual(rows, 2)
        self.assertFalse(
            BattingSeason.objects.filter(player_id='tradedpl01', team='2TM').exists()
        )

    @patch('pipeline.ingest_bref_history.fetch_with_retry')
    def test_assigns_sequential_stints_for_traded_player(self, mock_fetch: MagicMock) -> None:
        html = _batting_html([
            {'bbref_id': 'tradedpl01', 'name': 'Traded Player', 'team': 'NYY',
             'stats': {'b_hr': '20'}},
            {'bbref_id': 'tradedpl01', 'name': 'Traded Player', 'team': 'BOS',
             'stats': {'b_hr': '10'}},
        ])
        mock_fetch.return_value = _mock_response(html)

        ingest_batting_page(
            MagicMock(), 2000, 'MLB', 'http://example.com',
            EMPTY_CHADWICK, dry_run=False, verbose=False,
        )

        stints = list(
            BattingSeason.objects
            .filter(player_id='tradedpl01', year=2000)
            .order_by('stint')
            .values_list('stint', 'team')
        )
        self.assertEqual(stints, [(1, 'NYY'), (2, 'BOS')])

    @patch('pipeline.ingest_bref_history.fetch_with_retry')
    def test_absent_stats_stored_as_null(self, mock_fetch: MagicMock) -> None:
        # ibb and sacrifice_flies were not tracked in early seasons
        html = _batting_html([{
            'bbref_id': 'ansonca01', 'name': 'Cap Anson', 'team': 'CHN',
            'stats': {'b_games': '82', 'b_hr': '7'},
            # b_ibb and b_sf deliberately absent
        }])
        mock_fetch.return_value = _mock_response(html)

        ingest_batting_page(
            MagicMock(), 1884, 'NL', 'http://example.com',
            EMPTY_CHADWICK, dry_run=False, verbose=False,
        )

        season = BattingSeason.objects.get(player_id='ansonca01', year=1884)
        self.assertIsNone(season.ibb)
        self.assertIsNone(season.sacrifice_flies)

    @patch('pipeline.ingest_bref_history.fetch_with_retry')
    def test_dry_run_does_not_write_to_db(self, mock_fetch: MagicMock) -> None:
        html = _batting_html([{
            'bbref_id': 'ruthba01', 'name': 'Babe Ruth', 'team': 'NYY',
            'stats': {'b_hr': '60'},
        }])
        mock_fetch.return_value = _mock_response(html)

        rows = ingest_batting_page(
            MagicMock(), 1927, 'MLB', 'http://example.com',
            EMPTY_CHADWICK, dry_run=True, verbose=False,
        )

        self.assertEqual(rows, 1)
        self.assertFalse(BattingSeason.objects.filter(year=1927).exists())

    @patch('pipeline.ingest_bref_history.fetch_with_retry')
    def test_empty_table_returns_zero(self, mock_fetch: MagicMock) -> None:
        mock_fetch.return_value = _mock_response(b'<html><body></body></html>')

        rows = ingest_batting_page(
            MagicMock(), 2024, 'MLB', 'http://example.com',
            EMPTY_CHADWICK, dry_run=False, verbose=False,
        )

        self.assertEqual(rows, 0)
        self.assertFalse(BattingSeason.objects.filter(year=2024).exists())

    @patch('pipeline.ingest_bref_history.fetch_with_retry')
    def test_chadwick_cross_ref_applied_to_player(self, mock_fetch: MagicMock) -> None:
        html = _batting_html([{
            'bbref_id': 'ruthba01', 'name': 'Babe Ruth', 'team': 'NYY',
            'stats': {'b_hr': '60'},
        }])
        mock_fetch.return_value = _mock_response(html)

        ingest_batting_page(
            MagicMock(), 1927, 'MLB', 'http://example.com',
            CHADWICK_WITH_RUTH, dry_run=False, verbose=False,
        )

        player = Player.objects.get(bbref_id='ruthba01')
        self.assertEqual(player.mlbam_id, 1234)
        self.assertEqual(player.fangraphs_id, 5678)
        self.assertEqual(player.retro_id, 'ruth001')


class TestIngestPitchingPage(TestCase):

    @patch('pipeline.ingest_bref_history.fetch_with_retry')
    def test_creates_pitching_season_with_correct_fields(self, mock_fetch: MagicMock) -> None:
        html = _pitching_html([{
            'bbref_id': 'youngcy01', 'name': 'Cy Young', 'team': 'BOS',
            'stats': {
                'p_w': '33', 'p_l': '10', 'p_g': '43',
                'p_ip': '341.1', 'p_so': '149',
                'p_earned_run_avg': '1.97', 'p_war': '12.1',
            },
        }])
        mock_fetch.return_value = _mock_response(html)

        rows = ingest_pitching_page(
            MagicMock(), 1901, 'MLB', 'http://example.com',
            EMPTY_CHADWICK, dry_run=False, verbose=False,
        )

        self.assertEqual(rows, 1)
        season = PitchingSeason.objects.get(player_id='youngcy01', year=1901, stint=1)
        self.assertEqual(season.wins, 33)
        self.assertEqual(season.losses, 10)
        self.assertEqual(season.strikeouts, 149)
        self.assertEqual(season.ip_outs, 1024)  # 341*3 + 1
        self.assertAlmostEqual(season.era, 1.97, places=2)
        self.assertAlmostEqual(season.war, 12.1, places=1)

    @patch('pipeline.ingest_bref_history.fetch_with_retry')
    def test_filters_multi_team_total_rows(self, mock_fetch: MagicMock) -> None:
        html = _pitching_html([
            {'bbref_id': 'tradedpi01', 'team': 'NYY', 'stats': {'p_w': '10'}},
            {'bbref_id': 'tradedpi01', 'team': 'BOS', 'stats': {'p_w': '5'}},
            {'bbref_id': 'tradedpi01', 'team': '3TM', 'stats': {'p_w': '15'}},
        ])
        mock_fetch.return_value = _mock_response(html)

        rows = ingest_pitching_page(
            MagicMock(), 2000, 'MLB', 'http://example.com',
            EMPTY_CHADWICK, dry_run=False, verbose=False,
        )

        self.assertEqual(rows, 2)
        self.assertFalse(
            PitchingSeason.objects.filter(player_id='tradedpi01', team='3TM').exists()
        )

    @patch('pipeline.ingest_bref_history.fetch_with_retry')
    def test_dry_run_does_not_write_to_db(self, mock_fetch: MagicMock) -> None:
        html = _pitching_html([{
            'bbref_id': 'youngcy01', 'name': 'Cy Young', 'team': 'BOS',
            'stats': {'p_w': '33'},
        }])
        mock_fetch.return_value = _mock_response(html)

        rows = ingest_pitching_page(
            MagicMock(), 1901, 'MLB', 'http://example.com',
            EMPTY_CHADWICK, dry_run=True, verbose=False,
        )

        self.assertEqual(rows, 1)
        self.assertFalse(PitchingSeason.objects.filter(player_id='youngcy01').exists())

    @patch('pipeline.ingest_bref_history.fetch_with_retry')
    def test_ip_to_outs_applied_correctly(self, mock_fetch: MagicMock) -> None:
        cases = [
            ('9', 27),    # 9 complete innings
            ('6.1', 19),  # 6 innings + 1 out
            ('0.2', 2),   # 2 outs in 1 appearance
        ]
        for ip_str, expected_outs in cases:
            with self.subTest(ip=ip_str):
                bbref_id = f'pitcher{ip_str.replace(".", "")}'
                html = _pitching_html([{
                    'bbref_id': bbref_id, 'team': 'TST',
                    'stats': {'p_ip': ip_str},
                }])
                mock_fetch.return_value = _mock_response(html)
                ingest_pitching_page(
                    MagicMock(), 2000, 'MLB', 'http://example.com',
                    EMPTY_CHADWICK, dry_run=False, verbose=False,
                )
                season = PitchingSeason.objects.get(player_id=bbref_id, year=2000)
                self.assertEqual(season.ip_outs, expected_outs)


if __name__ == '__main__':
    unittest.main()

"""
Tests for pipeline/ingest_bref_awards.py — the All-Star and World Series scrapers.

Run from project root:
    python -m pytest pipeline/test_ingest_bref_awards.py -v
"""

from __future__ import annotations

import os
import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pca_backend.settings')

from bs4 import BeautifulSoup
from django.test import SimpleTestCase, TestCase

from pipeline.ingest_bref_awards import (
    bbref_from_href,
    scrape_allstar,
    scrape_asg_game,
    scrape_world_series,
)
from players.models import Player
from stats.models import IngestionLog, PlayerAward


def _asg_page(nl_roster, al_roster, nl_box=()):
    """An All-Star game page: roster section and box scores, both inside HTML
    comments as BRef serves them."""
    def box(box_id, label, ids):
        rows = "".join(f'<tr><td><a href="/players/{i[0]}/{i}.shtml">{i}</a></td><td>P</td></tr>' for i in ids)
        return (f'<div id="{box_id}" class="data_grid_box"><table>'
                f'<caption>{label} All-Stars</caption>'
                f'<tr><td><a href="/managers/mgr{box_id}.shtml">Manager</a></td></tr>{rows}</table></div>')
    lineups = (f'<div class="data_grid" id="div_lineups"><div class="data_grid_group">'
               f'{box("lineups_1", "NL", nl_roster)}{box("lineups_2", "AL", al_roster)}</div></div>')
    box_rows = "".join(f'<tr><th data-append-csv="{i}">{i}</th></tr>' for i in nl_box)
    boxscore = f'<table id="NLAllStarsbatting"><tbody>{box_rows}</tbody></table>'
    return BeautifulSoup(f"<html><body><!-- {lineups} --><!-- {boxscore} --></body></html>", "lxml")


class TestBbrefFromHref(SimpleTestCase):
    def test_ids_with_punctuation(self):
        self.assertEqual(bbref_from_href("/players/r/ruthba01.shtml"), "ruthba01")
        self.assertEqual(bbref_from_href("/players/s/sabatc.01.shtml"), "sabatc.01")
        self.assertEqual(bbref_from_href("/players/o/o'neipa01.shtml"), "o'neipa01")
        self.assertIsNone(bbref_from_href("/managers/girarjo01.shtml"))


class TestScrapeAsgGame(SimpleTestCase):
    def _calls(self, soup, known):
        with patch("pipeline.ingest_bref_awards.upsert_award", return_value=True) as up:
            n = scrape_asg_game(soup, 2010, known, dry_run=False, verbose=False)
        return n, sorted((c.args[0], c.kwargs["league"]) for c in up.call_args_list)

    def test_roster_includes_selections_who_did_not_play(self):
        # riverma01 is on the AL roster but absent from every box score.
        soup = _asg_page(nl_roster=["wrighda03"], al_roster=["riverma01", "sabatc.01"], nl_box=["wrighda03"])
        n, calls = self._calls(soup, {"wrighda03", "riverma01", "sabatc.01"})
        self.assertEqual(n, 3)
        self.assertEqual(calls, [("riverma01", "AL"), ("sabatc.01", "AL"), ("wrighda03", "NL")])

    def test_box_score_backstops_roster(self):
        soup = _asg_page(nl_roster=[], al_roster=[], nl_box=["wrighda03"])
        n, calls = self._calls(soup, {"wrighda03"})
        self.assertEqual(calls, [("wrighda03", "NL")])


class TestScrapeAllstarKeys(TestCase):
    def test_two_games_in_one_year_are_both_scraped(self):
        Player.objects.create(bbref_id="aaronha01", first_name="Henry", last_name="Aaron")
        games = [
            (1962, "https://www.baseball-reference.com/allstar/1962-allstar-game-1.shtml"),
            (1962, "https://www.baseball-reference.com/allstar/1962-allstar-game-2.shtml"),
        ]
        page = MagicMock(content=str(_asg_page(nl_roster=["aaronha01"], al_roster=[])).encode())
        with patch("pipeline.ingest_bref_awards.parse_asg_index", return_value=games), \
             patch("pipeline.ingest_bref_awards.fetch_with_retry", return_value=page) as fetch:
            scrape_allstar(MagicMock(), {"aaronha01"})
        self.assertEqual(fetch.call_count, 2)
        self.assertTrue(IngestionLog.objects.filter(source="bref_awards_asg_1962-allstar-game-2").exists())
        self.assertEqual(PlayerAward.objects.filter(player_id="aaronha01", kind="asg", year=1962).count(), 1)


def _team_page(ids):
    rows = "".join(f'<tr><td><a href="/players/{i[0]}/{i}.shtml">{i}</a></td></tr>' for i in ids)
    return MagicMock(content=f'<table id="players_standard_batting">{rows}</table>'.encode())


class TestScrapeWorldSeries(TestCase):
    def setUp(self):
        for pid in ("ruthba01", "fostebi99"):
            Player.objects.create(bbref_id=pid, first_name="X", last_name=pid)
        self.known = {"ruthba01", "fostebi99"}
        # 1927 had an MLB and a Negro League World Series; CAG sorts before NYY.
        self.winners = [
            (1927, "https://www.baseball-reference.com/teams/CAG/1927.shtml"),
            (1927, "https://www.baseball-reference.com/teams/NYY/1927.shtml"),
        ]
        self.pages = {self.winners[0][1]: _team_page(["fostebi99"]), self.winners[1][1]: _team_page(["ruthba01"])}

    def _run(self, force=False):
        with patch("pipeline.ingest_bref_awards.parse_ws_winners", return_value=self.winners), \
             patch("pipeline.ingest_bref_awards.fetch_with_retry", side_effect=lambda s, url: self.pages[url]):
            scrape_world_series(MagicMock(), self.known, force=force)

    def test_both_winners_in_one_year_are_credited(self):
        self._run()
        self.assertEqual(
            set(PlayerAward.objects.filter(kind="ws", year=1927).values_list("player_id", flat=True)),
            {"ruthba01", "fostebi99"},
        )

    def test_rerun_does_not_duplicate_null_league_rows(self):
        self._run()
        self._run(force=True)
        self.assertEqual(PlayerAward.objects.filter(kind="ws", year=1927).count(), 2)

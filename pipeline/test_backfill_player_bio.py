from __future__ import annotations

import tempfile
from datetime import date
from pathlib import Path

from django.test import TestCase

from pipeline import backfill_player_bio
from players.models import Player

HEADER = "playerID,birthYear,birthMonth,birthDay,birthCountry,bats,throws,debut,finalGame,bbrefID"


class LahmanKeyingTests(TestCase):
    def _run(self, *rows: str) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            csv = Path(tmp) / "People.csv"
            csv.write_text("\n".join([HEADER, *rows]) + "\n")
            backfill_player_bio.run(people_csv=str(csv), dry_run=False, overwrite=False, verbose=False)

    def _bio(self, bbref_id: str) -> tuple:
        p = Player.objects.get(bbref_id=bbref_id)
        return (p.birth_date, p.birth_country, p.bats, p.throws, p.debut, p.final_game)

    def test_row_lands_on_player_matching_bbref_id_not_player_id(self):
        Player.objects.create(bbref_id="callaji01", first_name="John", last_name="Callahan")
        Player.objects.create(bbref_id="callaji02", first_name="Jim", last_name="Callahan")

        self._run(
            "callajo02,1874,10,3,USA,,,1898-09-03,1898-09-04,callaji01",
            "callaji01,1881,1,12,USA,R,R,1902-05-25,1902-05-25,callaji02",
        )

        self.assertEqual(
            self._bio("callaji01"),
            (date(1874, 10, 3), "USA", None, None, date(1898, 9, 3), date(1898, 9, 4)),
        )
        self.assertEqual(
            self._bio("callaji02"),
            (date(1881, 1, 12), "USA", "R", "R", date(1902, 5, 25), date(1902, 5, 25)),
        )

    def test_row_without_bbref_id_is_skipped(self):
        Player.objects.create(bbref_id="frazege99", first_name="George", last_name="Frazier")

        self._run(
            "frazge99,1861,1,7,USA,,,,,frazege99",
            "frazege99,1861,1,7,,,,,,",
        )

        self.assertEqual(self._bio("frazege99"), (date(1861, 1, 7), "USA", None, None, None, None))

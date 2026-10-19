from __future__ import annotations

from django.test import TestCase

from pipeline import backfill_player_names
from players.models import Player


class ResplitTests(TestCase):
    def _name(self, bbref_id: str) -> tuple[str, str]:
        p = Player.objects.get(bbref_id=bbref_id)
        return (p.first_name, p.last_name)

    def test_resplits_rows_stored_by_the_old_last_space_split(self):
        Player.objects.create(bbref_id="griffke02", first_name="Ken Griffey", last_name="Jr.")
        Player.objects.create(bbref_id="larusto01", first_name="Tony La", last_name="Russa")
        Player.objects.create(bbref_id="yellomo01", first_name="Moses Yellow", last_name="Horse")
        Player.objects.create(bbref_id="carrocl01", first_name="Carroll", last_name="")
        Player.objects.create(bbref_id="troutmi01", first_name="Mike", last_name="Trout")

        updated = backfill_player_names.run(
            last_names={
                "griffke02": "Griffey",
                "larusto01": "LaRussa",
                "yellomo01": "Yellow Horse",
                "carrocl01": "Carroll",
                "troutmi01": "Trout",
            },
            dry_run=False,
        )

        self.assertEqual(updated, 4)
        self.assertEqual(self._name("griffke02"), ("Ken", "Griffey Jr."))
        self.assertEqual(self._name("larusto01"), ("Tony", "La Russa"))
        self.assertEqual(self._name("yellomo01"), ("Moses", "Yellow Horse"))
        self.assertEqual(self._name("carrocl01"), ("", "Carroll"))
        self.assertEqual(self._name("troutmi01"), ("Mike", "Trout"))

    def test_second_run_changes_nothing(self):
        Player.objects.create(bbref_id="griffke02", first_name="Ken Griffey", last_name="Jr.")
        last_names = {"griffke02": "Griffey"}

        backfill_player_names.run(last_names=last_names, dry_run=False)

        self.assertEqual(backfill_player_names.run(last_names=last_names, dry_run=False), 0)

    def test_dry_run_writes_nothing(self):
        Player.objects.create(bbref_id="griffke02", first_name="Ken Griffey", last_name="Jr.")

        updated = backfill_player_names.run(last_names={"griffke02": "Griffey"}, dry_run=True)

        self.assertEqual(updated, 1)
        self.assertEqual(self._name("griffke02"), ("Ken Griffey", "Jr."))

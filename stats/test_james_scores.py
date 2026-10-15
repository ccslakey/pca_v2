from django.test import TestCase

from players.models import Player
from stats.management.commands.compute_james_scores import _aggregate_batting, _aggregate_pitching
from stats.models import BattingSeason, PitchingSeason


class TradedBetweenLeaguesTests(TestCase):
    def setUp(self):
        self.player = Player.objects.create(bbref_id='traded01', first_name='Traded', last_name='Player')

    def test_batting_season_uses_stint_one_league(self):
        for stint, team, league in [(2, 'LAN', 'NL'), (1, 'NYA', 'AL')]:
            BattingSeason.objects.create(
                player=self.player, year=2020, stint=stint, team=team, league=league,
                plate_appearances=100, at_bats=90, hits=30,
            )
        result = _aggregate_batting()
        self.assertEqual(list(result), [(2020, 'AL')])
        self.assertEqual(result[(2020, 'AL')][self.player.pk]['h'], 60)

    def test_pitching_season_uses_stint_one_league(self):
        for stint, team, league in [(2, 'LAN', 'NL'), (1, 'NYA', 'AL')]:
            PitchingSeason.objects.create(
                player=self.player, year=2020, stint=stint, team=team, league=league,
                ip_outs=90, strikeouts=20,
            )
        result = _aggregate_pitching()
        self.assertEqual(list(result), [(2020, 'AL')])
        self.assertEqual(result[(2020, 'AL')][self.player.pk]['so'], 40)

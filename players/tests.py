from __future__ import annotations

from django.urls import reverse
from rest_framework.test import APITestCase

from players.models import Player
from stats.models import BattingSeason, PitchingSeason, PlayerAward, StatcastZoneBucket


def make_player(bbref_id: str, first: str = 'Test', last: str = 'Player', **kwargs) -> Player:
    return Player.objects.create(
        bbref_id=bbref_id,
        first_name=first,
        last_name=last,
        mlb_played_first=kwargs.get('first_year', 2000),
        mlb_played_last=kwargs.get('last_year', 2010),
        bats=kwargs.get('bats', 'R'),
        throws=kwargs.get('throws', 'R'),
    )


def add_batting(player: Player, year: int, war: float, **kwargs) -> BattingSeason:
    return BattingSeason.objects.create(
        player=player,
        year=year,
        stint=kwargs.get('stint', 1),
        team=kwargs.get('team', 'NYA'),
        league='AL',
        war=war,
        home_runs=kwargs.get('hr', 10),
        batting_avg=kwargs.get('avg', 0.280),
        ops=kwargs.get('ops', 0.820),
    )


def add_pitching(player: Player, year: int, war: float, **kwargs) -> PitchingSeason:
    return PitchingSeason.objects.create(
        player=player,
        year=year,
        stint=kwargs.get('stint', 1),
        team=kwargs.get('team', 'NYA'),
        league='AL',
        war=war,
        era=kwargs.get('era', 3.50),
        strikeouts=kwargs.get('so', 180),
        ip_outs=kwargs.get('ip_outs', 600),
    )


class TestPlayerList(APITestCase):
    def setUp(self):
        self.ruth = make_player('ruthba01', 'Babe', 'Ruth')
        self.gehrig = make_player('gehrilo01', 'Lou', 'Gehrig')
        self.url = reverse('player-list')

    def test_returns_all_players(self):
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['count'], 2)

    def test_search_by_last_name(self):
        r = self.client.get(self.url, {'search': 'Ruth'})
        self.assertEqual(r.data['count'], 1)
        self.assertEqual(r.data['results'][0]['bbref_id'], 'ruthba01')

    def test_search_by_bbref_id(self):
        r = self.client.get(self.url, {'search': 'gehrilo01'})
        self.assertEqual(r.data['count'], 1)

    def test_list_uses_summary_serializer(self):
        r = self.client.get(self.url)
        result = r.data['results'][0]
        self.assertIn('bbref_id', result)
        self.assertIn('first_name', result)
        self.assertNotIn('birth_year', result)

    def test_filter_by_bats(self):
        make_player('leftyXX01', bats='L')
        r = self.client.get(self.url, {'bats': 'R'})
        for p in r.data['results']:
            self.assertEqual(p['bats'], 'R')


class TestPlayerDetail(APITestCase):
    def setUp(self):
        self.player = make_player('ruthba01', 'Babe', 'Ruth', bats='L')
        self.url = reverse('player-detail', kwargs={'pk': 'ruthba01'})

    def test_returns_200(self):
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['bbref_id'], 'ruthba01')

    def test_uses_detail_serializer(self):
        r = self.client.get(self.url)
        self.assertIn('bats', r.data)
        self.assertIn('throws', r.data)

    def test_404_for_unknown(self):
        r = self.client.get(reverse('player-detail', kwargs={'pk': 'nobody00'}))
        self.assertEqual(r.status_code, 404)


class TestBattingAction(APITestCase):
    def setUp(self):
        self.player = make_player('ruthba01', 'Babe', 'Ruth')
        add_batting(self.player, 2000, war=7.2, team='NYA')
        add_batting(self.player, 2001, war=5.1, team='NYA')
        self.url = reverse('player-batting', kwargs={'pk': 'ruthba01'})

    def test_returns_seasons_ordered_by_year(self):
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 200)
        years = [s['year'] for s in r.data]
        self.assertEqual(years, sorted(years))

    def test_includes_war(self):
        r = self.client.get(self.url)
        self.assertIn('war', r.data[0])

    def test_empty_for_pitcher_with_no_batting(self):
        pitcher = make_player('pitcherXX01')
        add_pitching(pitcher, 2005, war=4.0)
        r = self.client.get(reverse('player-batting', kwargs={'pk': 'pitcherXX01'}))
        self.assertEqual(r.data, [])

    def test_multi_stint_both_returned(self):
        add_batting(self.player, 2002, war=2.0, team='BOS', stint=1)
        add_batting(self.player, 2002, war=1.5, team='CHN', stint=2)
        r = self.client.get(self.url)
        year_2002 = [s for s in r.data if s['year'] == 2002]
        self.assertEqual(len(year_2002), 2)


class TestPitchingAction(APITestCase):
    def setUp(self):
        self.player = make_player('koufasa01', 'Sandy', 'Koufax')
        add_pitching(self.player, 2000, war=8.0)
        add_pitching(self.player, 2001, war=6.5)
        self.url = reverse('player-pitching', kwargs={'pk': 'koufasa01'})

    def test_returns_seasons(self):
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data), 2)

    def test_includes_era(self):
        r = self.client.get(self.url)
        self.assertIn('era', r.data[0])

    def test_empty_for_batter(self):
        batter = make_player('batterXX01')
        add_batting(batter, 2005, war=5.0)
        r = self.client.get(reverse('player-pitching', kwargs={'pk': 'batterXX01'}))
        self.assertEqual(r.data, [])


class TestSimilarAction(APITestCase):
    def setUp(self):
        self.ruth = make_player('ruthba01', 'Babe', 'Ruth')
        add_batting(self.ruth, 2000, war=10.0)

        # High WAR batter — should rank first
        self.gehrig = make_player('gehrilo01', 'Lou', 'Gehrig')
        add_batting(self.gehrig, 2000, war=9.5)

        # Mid WAR batter
        self.dimag = make_player('dimagjo01', 'Joe', 'DiMaggio')
        add_batting(self.dimag, 2000, war=7.0)

        # Low WAR — should be excluded (<1.0)
        self.scrub = make_player('scrubXX01', 'No', 'Name')
        add_batting(self.scrub, 2000, war=0.5)

        # Pitcher — should rank lower due to position penalty
        self.ford = make_player('fordwh01', 'Whitey', 'Ford')
        add_pitching(self.ford, 2000, war=9.0)

        self.url = reverse('player-similar', kwargs={'pk': 'ruthba01'})

    def test_returns_200(self):
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 200)

    def test_excludes_self(self):
        r = self.client.get(self.url)
        ids = [p['bbref_id'] for p in r.data]
        self.assertNotIn('ruthba01', ids)

    def test_returns_at_most_four(self):
        for i in range(5):
            p = make_player(f'extra{i:02d}01', war_val=8.0)
            add_batting(p, 2000, war=8.0)
        r = self.client.get(self.url)
        self.assertLessEqual(len(r.data), 4)

    def test_excludes_low_war_players(self):
        r = self.client.get(self.url)
        ids = [p['bbref_id'] for p in r.data]
        self.assertNotIn('scrubXX01', ids)

    def test_batters_rank_above_pitchers(self):
        r = self.client.get(self.url)
        ids = [p['bbref_id'] for p in r.data]
        # gehrig and dimaggio (batters) should appear before ford (pitcher)
        batter_positions = [i for i, x in enumerate(ids) if x in ('gehrilo01', 'dimagjo01')]
        pitcher_positions = [i for i, x in enumerate(ids) if x == 'fordwh01']
        if batter_positions and pitcher_positions:
            self.assertLess(min(batter_positions), max(pitcher_positions))

    def test_response_fields(self):
        r = self.client.get(self.url)
        self.assertTrue(len(r.data) > 0)
        p = r.data[0]
        for field in ('bbref_id', 'first_name', 'last_name', 'career_war', 'is_pitcher'):
            self.assertIn(field, p)

    def test_404_for_unknown_player(self):
        r = self.client.get(reverse('player-similar', kwargs={'pk': 'nobody00'}))
        self.assertEqual(r.status_code, 404)

    def test_pitcher_similarity(self):
        r = self.client.get(reverse('player-similar', kwargs={'pk': 'fordwh01'}))
        ids = [p['bbref_id'] for p in r.data]
        # ford (pitcher) should not appear in his own results
        self.assertNotIn('fordwh01', ids)


class TestAwardsAction(APITestCase):
    def setUp(self):
        self.player = make_player('ruthba01', 'Babe', 'Ruth')
        PlayerAward.objects.create(player=self.player, year=1923, kind='mvp')
        PlayerAward.objects.create(player=self.player, year=1927, kind='ws', league='AL')
        PlayerAward.objects.create(player=self.player, year=1933, kind='asg', league='AL')

    def test_returns_200(self):
        r = self.client.get(reverse('player-awards', kwargs={'pk': 'ruthba01'}))
        self.assertEqual(r.status_code, 200)

    def test_returns_all_awards(self):
        r = self.client.get(reverse('player-awards', kwargs={'pk': 'ruthba01'}))
        self.assertEqual(len(r.data), 3)

    def test_ordered_by_year_descending(self):
        r = self.client.get(reverse('player-awards', kwargs={'pk': 'ruthba01'}))
        years = [a['year'] for a in r.data]
        self.assertEqual(years, sorted(years, reverse=True))

    def test_response_fields(self):
        r = self.client.get(reverse('player-awards', kwargs={'pk': 'ruthba01'}))
        a = r.data[0]
        for field in ('id', 'year', 'kind', 'league', 'notes'):
            self.assertIn(field, a)

    def test_league_and_notes_preserved(self):
        r = self.client.get(reverse('player-awards', kwargs={'pk': 'ruthba01'}))
        ws = next(a for a in r.data if a['kind'] == 'ws')
        self.assertEqual(ws['league'], 'AL')

    def test_empty_for_player_with_no_awards(self):
        make_player('nobody00', 'No', 'Awards')
        r = self.client.get(reverse('player-awards', kwargs={'pk': 'nobody00'}))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data, [])

    def test_404_for_unknown_player(self):
        r = self.client.get(reverse('player-awards', kwargs={'pk': 'ghost000'}))
        self.assertEqual(r.status_code, 404)


class TestPitchZoneAction(APITestCase):
    def setUp(self):
        self.player = make_player('troutmi01', 'Mike', 'Trout')
        add_batting(self.player, 2023, 8.0)
        for px, pz, count, total in [(-0.5, 2.5, 10, 40), (0.3, 3.1, 5, 20), (0.8, 1.8, 2, 15)]:
            StatcastZoneBucket.objects.create(
                player=self.player, role='B', outcome='contact',
                plate_x=px, plate_z=pz, count=count, total=total,
            )
        StatcastZoneBucket.objects.create(
            player=self.player, role='B', outcome='whiffs',
            plate_x=0.5, plate_z=3.0, count=8, total=12,
        )

    def test_returns_200(self):
        r = self.client.get(reverse('player-pitch-zone', kwargs={'pk': 'troutmi01'}))
        self.assertEqual(r.status_code, 200)

    def test_default_role_and_outcome(self):
        r = self.client.get(reverse('player-pitch-zone', kwargs={'pk': 'troutmi01'}))
        self.assertEqual(r.data['role'], 'B')
        self.assertEqual(r.data['outcome'], 'contact')

    def test_bucket_count_matches_outcome(self):
        r = self.client.get(reverse('player-pitch-zone', kwargs={'pk': 'troutmi01'}),
                            {'role': 'B', 'outcome': 'contact'})
        self.assertEqual(len(r.data['buckets']), 3)

    def test_outcome_filter(self):
        r = self.client.get(reverse('player-pitch-zone', kwargs={'pk': 'troutmi01'}),
                            {'role': 'B', 'outcome': 'whiffs'})
        self.assertEqual(len(r.data['buckets']), 1)

    def test_bucket_fields(self):
        r = self.client.get(reverse('player-pitch-zone', kwargs={'pk': 'troutmi01'}))
        b = r.data['buckets'][0]
        for field in ('plate_x', 'plate_z', 'count', 'total'):
            self.assertIn(field, b)

    def test_empty_for_no_data(self):
        make_player('nobody00', 'No', 'Data')
        r = self.client.get(reverse('player-pitch-zone', kwargs={'pk': 'nobody00'}))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['buckets'], [])

    def test_invalid_outcome_returns_400(self):
        r = self.client.get(reverse('player-pitch-zone', kwargs={'pk': 'troutmi01'}),
                            {'role': 'B', 'outcome': 'bogus'})
        self.assertEqual(r.status_code, 400)

    def test_invalid_role_returns_400(self):
        r = self.client.get(reverse('player-pitch-zone', kwargs={'pk': 'troutmi01'}),
                            {'role': 'X', 'outcome': 'contact'})
        self.assertEqual(r.status_code, 400)

    def test_404_for_unknown_player(self):
        r = self.client.get(reverse('player-pitch-zone', kwargs={'pk': 'ghost000'}))
        self.assertEqual(r.status_code, 404)

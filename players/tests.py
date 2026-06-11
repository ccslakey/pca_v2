from __future__ import annotations

import datetime

from django.core.cache import cache
from django.core.management import call_command
from django.urls import reverse
from rest_framework.test import APITestCase

from players.models import Player
from players.views import _build_aging_curve, _build_leaderboard_rows
from stats.models import (
    BattingSeason,
    FieldingPositionToken,
    FieldingSeason,
    PitchingSeason,
    PlayerAward,
    StatcastZoneBucket,
)


def make_player(bbref_id: str, first: str = 'Test', last: str = 'Player', **kwargs) -> Player:
    return Player.objects.create(
        bbref_id=bbref_id,
        first_name=first,
        last_name=last,
        debut=kwargs.get('debut', None),
        final_game=kwargs.get('final_game', None),
        bats=kwargs.get('bats', 'R'),
        throws=kwargs.get('throws', 'R'),
        primary_position=kwargs.get('primary_position', None),
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
        self.assertIn('primary_position', result)
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
        self.assertIn('primary_position', r.data)

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


class TestFieldingAction(APITestCase):
    def setUp(self):
        self.player = make_player('troutmi01', 'Mike', 'Trout', primary_position='CF')
        self.season = FieldingSeason.objects.create(
            player=self.player,
            year=2019,
            stint=1,
            team='LAA',
            league='AL',
            age=27,
            games=134,
            games_started=132,
            innings_outs=3500,
            chances=300,
            putouts=292,
            assists=5,
            errors=3,
            fielding_pct=.990,
            positions_raw='*8/79',
        )
        FieldingPositionToken.objects.create(
            fielding_season=self.season,
            rank=1,
            position='CF',
            is_primary_marker=True,
        )
        FieldingPositionToken.objects.create(
            fielding_season=self.season,
            rank=2,
            position='LF',
            is_minor_marker=True,
        )

    def test_returns_200(self):
        r = self.client.get(reverse('player-fielding', kwargs={'pk': 'troutmi01'}))
        self.assertEqual(r.status_code, 200)

    def test_includes_standard_fielding_fields_and_tokens(self):
        r = self.client.get(reverse('player-fielding', kwargs={'pk': 'troutmi01'}))
        row = r.data[0]
        self.assertEqual(row['positions_raw'], '*8/79')
        self.assertIn('fielding_pct', row)
        self.assertEqual(row['position_tokens'][0]['position'], 'CF')

    def test_empty_for_player_with_no_fielding(self):
        make_player('nobody00', 'No', 'Fielding')
        r = self.client.get(reverse('player-fielding', kwargs={'pk': 'nobody00'}))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data, [])


class TestSimilarAction(APITestCase):
    def setUp(self):
        cache.clear()
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

    def test_response_shape(self):
        r = self.client.get(self.url)
        self.assertIn('batters', r.data)
        self.assertIn('pitchers', r.data)

    def test_excludes_self(self):
        r = self.client.get(self.url)
        ids = [p['bbref_id'] for p in r.data['batters']]
        self.assertNotIn('ruthba01', ids)

    def test_returns_at_most_four(self):
        for i in range(5):
            p = make_player(f'extra{i:02d}01', war_val=8.0)
            add_batting(p, 2000, war=8.0)
        r = self.client.get(self.url)
        self.assertLessEqual(len(r.data['batters']), 4)

    def test_excludes_low_war_players(self):
        r = self.client.get(self.url)
        ids = [p['bbref_id'] for p in r.data['batters']]
        self.assertNotIn('scrubXX01', ids)

    def test_batters_not_in_pitcher_list(self):
        r = self.client.get(self.url)
        # ruth is a batter — pitchers list should be empty
        self.assertEqual(r.data['pitchers'], [])
        # gehrig and dimaggio should appear in batters list
        ids = [p['bbref_id'] for p in r.data['batters']]
        self.assertTrue(any(x in ids for x in ('gehrilo01', 'dimagjo01')))

    def test_response_fields(self):
        r = self.client.get(self.url)
        self.assertTrue(len(r.data['batters']) > 0)
        p = r.data['batters'][0]
        for field in ('bbref_id', 'first_name', 'last_name', 'career_war', 'is_pitcher', 'similarity'):
            self.assertIn(field, p)

    def test_similarity_descending(self):
        for i in range(5):
            pl = make_player(f'extra{i:02d}01', war_val=8.0)
            add_batting(pl, 2000, war=float(8 - i))
        r = self.client.get(self.url)
        sims = [p['similarity'] for p in r.data['batters']]
        self.assertEqual(sims, sorted(sims, reverse=True))

    def test_404_for_unknown_player(self):
        r = self.client.get(reverse('player-similar', kwargs={'pk': 'nobody00'}))
        self.assertEqual(r.status_code, 404)

    def test_pitcher_similarity(self):
        r = self.client.get(reverse('player-similar', kwargs={'pk': 'fordwh01'}))
        ids = [p['bbref_id'] for p in r.data['pitchers']]
        self.assertNotIn('fordwh01', ids)
        # ford is a pitcher — batters list should be empty
        self.assertEqual(r.data['batters'], [])

    def test_two_way_player(self):
        ohtani = make_player('ohtansh01', 'Shohei', 'Ohtani')
        add_batting(ohtani, 2022, war=5.0)
        add_pitching(ohtani, 2022, war=4.0)
        r = self.client.get(reverse('player-similar', kwargs={'pk': 'ohtansh01'}))
        self.assertEqual(r.status_code, 200)
        self.assertGreater(len(r.data['batters']), 0)
        self.assertGreater(len(r.data['pitchers']), 0)


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


class TestLeaderboardPositions(APITestCase):
    def setUp(self):
        cache.clear()
        self.shortstop = make_player('shortst01', 'Short', 'Stop', primary_position='SS')
        add_batting(self.shortstop, 2000, war=5.0)
        self.center = make_player('center01', 'Center', 'Field', primary_position='CF')
        add_batting(self.center, 2000, war=4.0)
        self.pitcher = make_player('pitchr01', 'Pure', 'Pitcher', primary_position='P')
        add_pitching(self.pitcher, 2000, war=6.0)

    def test_leaderboard_includes_primary_position(self):
        r = self.client.get(reverse('player-leaderboard'))
        self.assertEqual(r.status_code, 200)
        row = next(p for p in r.data['results'] if p['bbref_id'] == 'shortst01')
        self.assertEqual(row['primary_position'], 'SS')

    def test_exact_position_filter(self):
        r = self.client.get(reverse('player-leaderboard'), {'pos': 'SS'})
        ids = {p['bbref_id'] for p in r.data['results']}
        self.assertEqual(ids, {'shortst01'})

    def test_pitcher_and_batter_filters_remain_compatible(self):
        p = self.client.get(reverse('player-leaderboard'), {'pos': 'P'})
        self.assertEqual({row['bbref_id'] for row in p.data['results']}, {'pitchr01'})
        b = self.client.get(reverse('player-leaderboard'), {'pos': 'B'})
        b_ids = {row['bbref_id'] for row in b.data['results']}
        self.assertIn('shortst01', b_ids)
        self.assertNotIn('pitchr01', b_ids)


class TestComputePrimaryPositions(APITestCase):
    def test_uses_decoded_fielding_games(self):
        player = make_player('multi01', 'Multi', 'Position')
        cf = FieldingSeason.objects.create(player=player, year=2000, stint=1, team='LAA', games=100)
        ss = FieldingSeason.objects.create(player=player, year=2001, stint=1, team='LAA', games=140)
        FieldingPositionToken.objects.create(fielding_season=cf, rank=1, position='CF')
        FieldingPositionToken.objects.create(fielding_season=ss, rank=1, position='SS')
        call_command('compute_primary_positions')
        player.refresh_from_db()
        self.assertEqual(player.primary_position, 'SS')

    def test_pitcher_fallback(self):
        player = make_player('pitchonly01', 'Pitch', 'Only')
        add_pitching(player, 2000, war=3.0)
        call_command('compute_primary_positions')
        player.refresh_from_db()
        self.assertEqual(player.primary_position, 'P')


class TestAgingCurve(APITestCase):
    def setUp(self):
        cache.clear()
        # Player born 1980 → age 30 in the 2010 season
        self.p = make_player('agecurve01', birth_date=datetime.date(1980, 1, 1))

    def _make_player(self, bbref_id, birth_year):
        return Player.objects.get_or_create(
            bbref_id=bbref_id,
            defaults=dict(
                first_name='Test', last_name='Player',
                birth_date=datetime.date(birth_year, 1, 1),
            ),
        )[0]

    def test_batting_curve_aggregates_by_age(self):
        p30 = self._make_player('bat30a01', 1980)
        p31 = self._make_player('bat31a01', 1979)
        BattingSeason.objects.create(player=p30, year=2010, stint=1, team='NYA', league='AL',
                                     plate_appearances=150, war=4.0)
        BattingSeason.objects.create(player=p31, year=2010, stint=1, team='NYA', league='AL',
                                     plate_appearances=150, war=6.0)
        result = _build_aging_curve('B')
        by_age = {pt['age']: pt for pt in result}
        self.assertIn(30, by_age)
        self.assertAlmostEqual(by_age[30]['war'], 4.0)
        self.assertIn(31, by_age)
        self.assertAlmostEqual(by_age[31]['war'], 6.0)

    def test_batting_curve_excludes_below_pa_threshold(self):
        p = self._make_player('batlow01', 1980)
        BattingSeason.objects.create(player=p, year=2010, stint=1, team='NYA', league='AL',
                                     plate_appearances=50, war=10.0)
        result = _build_aging_curve('B')
        by_age = {pt['age']: pt for pt in result}
        self.assertNotIn(30, by_age)

    def test_batting_curve_excludes_players_without_birth_date(self):
        p = make_player('nobirth01')  # birth_date=None by default
        BattingSeason.objects.create(player=p, year=2010, stint=1, team='NYA', league='AL',
                                     plate_appearances=150, war=5.0)
        result = _build_aging_curve('B')
        # Should not raise and should not include this player
        self.assertIsInstance(result, list)

    def test_pitching_curve_uses_ip_threshold(self):
        p = self._make_player('pitcage01', 1980)
        # ip_outs=150 meets the ≥150 threshold
        PitchingSeason.objects.create(player=p, year=2010, stint=1, team='NYA', league='AL',
                                      ip_outs=150, war=5.0, era=3.0, era_plus=120, strikeouts=180)
        result = _build_aging_curve('P')
        by_age = {pt['age']: pt for pt in result}
        self.assertIn(30, by_age)
        self.assertAlmostEqual(by_age[30]['war'], 5.0)

    def test_pitching_curve_excludes_below_ip_threshold(self):
        p = self._make_player('pitclow01', 1980)
        PitchingSeason.objects.create(player=p, year=2010, stint=1, team='NYA', league='AL',
                                      ip_outs=30, war=1.0, era=3.0, era_plus=110, strikeouts=40)
        result = _build_aging_curve('P')
        by_age = {pt['age']: pt for pt in result}
        self.assertNotIn(30, by_age)

    def test_returns_list(self):
        result = _build_aging_curve('B')
        self.assertIsInstance(result, list)

    def test_pitching_role_returns_list(self):
        result = _build_aging_curve('P')
        self.assertIsInstance(result, list)


class TestLeaderboardRows(APITestCase):
    def setUp(self):
        cache.clear()

    def test_includes_players_with_positive_war(self):
        p = make_player('lead01', 'Lead', 'One')
        add_batting(p, 2010, war=5.0, hr=20)
        rows = _build_leaderboard_rows()
        ids = {r['bbref_id'] for r in rows}
        self.assertIn('lead01', ids)

    def test_excludes_players_with_zero_or_negative_war(self):
        p = make_player('zerowa01', 'Zero', 'War')
        add_batting(p, 2010, war=0.0)
        rows = _build_leaderboard_rows()
        ids = {r['bbref_id'] for r in rows}
        self.assertNotIn('zerowa01', ids)

    def test_career_war_sums_batting_and_pitching(self):
        p = make_player('twoway01', 'Two', 'Way')
        add_batting(p, 2010, war=3.0)
        add_pitching(p, 2010, war=4.0)
        rows = _build_leaderboard_rows()
        row = next(r for r in rows if r['bbref_id'] == 'twoway01')
        self.assertAlmostEqual(row['career_war'], 7.0)

    def test_second_call_returns_identical_rows(self):
        add_batting(make_player('cache01', 'Cache', 'One'), 2010, war=3.0)
        first = _build_leaderboard_rows()
        second = _build_leaderboard_rows()
        self.assertEqual(
            {r['bbref_id'] for r in first},
            {r['bbref_id'] for r in second},
        )

    def test_is_pitcher_true_when_pitching_war_exceeds_batting(self):
        p = make_player('ispitch01', 'Is', 'Pitcher')
        add_batting(p, 2010, war=1.0)
        add_pitching(p, 2010, war=6.0)
        rows = _build_leaderboard_rows()
        row = next(r for r in rows if r['bbref_id'] == 'ispitch01')
        self.assertTrue(row['is_pitcher'])


# ---------------------------------------------------------------------------
# Grounded narrative (LLM summary feature)
# ---------------------------------------------------------------------------

from unittest.mock import patch  # noqa: E402

from django.test import SimpleTestCase, override_settings  # noqa: E402

from players import narrative  # noqa: E402
from players.narrative import (  # noqa: E402
    allowed_numbers,
    build_facts,
    generate_narrative,
    labeled_facts,
    render_template,
    verify_claims,
    verify_numbers,
)


class TestVerifyNumbers(SimpleTestCase):
    """The anti-hallucination check: every emitted number must trace to data."""

    def test_clean_text_passes(self):
        allowed = {714.0, 162.1, 1927.0, 0.342}
        self.assertEqual(
            verify_numbers("714 HR and 162.1 WAR in 1927, hitting .342", allowed), []
        )

    def test_flags_invented_number(self):
        self.assertEqual(verify_numbers("He hit 800 home runs", {714.0}), ["800"])

    def test_comma_grouping_normalized(self):
        self.assertEqual(verify_numbers("racked up 1,500 hits", {1500.0}), [])

    def test_legitimate_rounding_accepted(self):
        # Model rounds a .342 average to .34 — still grounded.
        self.assertEqual(verify_numbers("a .34 hitter", {0.342}), [])

    def test_wrong_rounding_flagged(self):
        self.assertEqual(verify_numbers("a .35 hitter", {0.342}), [".35"])

    def test_league_average_baseline_is_safe(self):
        # 100 is the OPS+/ERA+ league-average constant, allowed without a fact.
        self.assertEqual(verify_numbers("an OPS+ above the 100 baseline", set()), [])

    def test_integer_rounding_of_war(self):
        # 162.7 WAR may be cited as "163" — acceptable rounding to whole number.
        self.assertEqual(verify_numbers("163 career WAR", {162.7}), [])

    def test_flat_verifier_cross_stat_collision_is_a_known_limitation(self):
        """The flat verifier checks *provenance* (is the figure real for the
        player?) not *assignment* (does it belong to this claim?). A player with
        714 HR and 162.1 WAR has both in the set, so the fabrication "162 home
        runs" passes because 162 round-matches the WAR value. This documents the
        flat path's limitation; the typed path (verify_claims) closes it — see
        TestVerifyClaims.test_cross_stat_collision_is_rejected."""
        allowed = {714.0, 162.1}  # career HR and career WAR — both legitimate
        self.assertEqual(verify_numbers("he hit 162 home runs", allowed), [])


class TestVerifyClaims(SimpleTestCase):
    """Typed verification (Route A): each number is checked against its *named*
    stat, not a flat union — so a real-but-wrong-stat number is rejected."""

    # Player with 714 HR and 162.1 career WAR; season line 1927: 60 HR.
    LABELED = {
        "career_hr": {714.0},
        "career_war": {162.1},
        "season_hr": {60.0},
        ("season_hr", 1927): {60.0},
        "year": {1927.0},
    }

    def test_correctly_bound_number_passes(self):
        text = "He hit 714 home runs and compiled 162.1 WAR."
        bindings = [
            {"value": 714, "stat": "career_hr"},
            {"value": 162.1, "stat": "career_war"},
        ]
        self.assertEqual(verify_claims(text, bindings, self.LABELED), [])

    def test_cross_stat_collision_is_rejected(self):
        # The hole the flat verifier waves through: 162 is real (it's the WAR),
        # but bound to home runs it does not match career_hr's value → rejected.
        text = "He hit 162 home runs."
        bindings = [{"value": 162, "stat": "career_hr"}]
        problems = verify_claims(text, bindings, self.LABELED)
        self.assertEqual(len(problems), 1)
        self.assertIn("career_hr", problems[0])

    def test_undeclared_number_is_rejected(self):
        # Every number must be declared; an unbound figure can't be grounded.
        problems = verify_claims("He hit 73 home runs.", [], self.LABELED)
        self.assertEqual(problems, ["73: no binding declares this number"])

    def test_year_scoped_binding_enforces_the_season(self):
        # 60 HR is real for 1927; claiming it for 1928 (no data) is rejected.
        text = "He hit 60 home runs in 1928."
        ok = [{"value": 60, "stat": "season_hr", "year": 1927}, {"value": 1928, "stat": "year"}]
        # 1928 itself isn't an active year here, so it's flagged regardless;
        # focus on the season binding: bind 60 to the wrong season.
        wrong = [{"value": 60, "stat": "season_hr", "year": 1928}, {"value": 1928, "stat": "year"}]
        self.assertTrue(any("season_hr for 1928" in p for p in verify_claims(text, wrong, self.LABELED)))
        # Bound to the right season, the 60 passes (1928 still flagged separately).
        problems = verify_claims(text, ok, self.LABELED)
        self.assertFalse(any("season_hr" in p for p in problems))

    def test_mislabeled_binding_is_caught_by_phrase_check(self):
        # Layer 2: 162 is a real value (the WAR), and the model *declares* it as
        # career_war — so the value check (b) passes. But the prose says "home
        # runs", which the binding's stat contradicts → rejected.
        text = "He hit 162 home runs."
        bindings = [{"value": 162, "stat": "career_war"}]
        problems = verify_claims(text, bindings, self.LABELED)
        self.assertEqual(len(problems), 1)
        self.assertIn("reads as", problems[0])
        self.assertIn("career_war", problems[0])

    def test_honest_binding_with_matching_prose_passes(self):
        # Same number, but the prose and the binding agree → fine.
        labeled = {"career_war": {162.1}}
        text = "He compiled 162.1 WAR."
        self.assertEqual(verify_claims(text, [{"value": 162.1, "stat": "career_war"}], labeled), [])

    def test_number_with_no_nearby_keyword_is_not_flagged(self):
        # Conservative: no stat word near the number → can't adjudicate → pass.
        labeled = {"seasons_played": {22.0}}
        text = "He played 22 long years."
        self.assertEqual(verify_claims(text, [{"value": 22, "stat": "seasons_played"}], labeled), [])

    def test_phrase_check_does_not_read_across_an_adjacent_number(self):
        # 714 next to "home runs", 162.1 next to "WAR": each binds correctly and
        # the window for one number must not borrow the other's keyword.
        labeled = {"career_hr": {714.0}, "career_war": {162.1}}
        text = "He hit 714 home runs and compiled 162.1 WAR."
        bindings = [{"value": 714, "stat": "career_hr"}, {"value": 162.1, "stat": "career_war"}]
        self.assertEqual(verify_claims(text, bindings, labeled), [])

    def test_rounding_band_carries_through_both_checks(self):
        # ".34" written for a .342 average: declared 0.342, checked at 2 places.
        labeled = {"career_avg": {0.342}}
        text = "a .34 hitter"
        self.assertEqual(verify_claims(text, [{"value": 0.342, "stat": "career_avg"}], labeled), [])

    def test_labeled_facts_separates_stats(self):
        facts = {
            "career_war_total": 162.1,
            "bio": {"debut_year": 1914, "final_year": 1935, "seasons_played": 22},
            "batting": {"career_war": 162.1, "career_hr": 714, "career_hits": 2873,
                        "career_avg": 0.342, "career_ops_plus": 206, "peak_war": 14.1, "peak_year": 1923},
            "batting_log": [{"year": 1927, "hr": 60, "war": 12.4, "avg": 0.356, "ops": 1.258, "ops_plus": 225}],
        }
        labeled = labeled_facts(facts)
        self.assertEqual(labeled["career_hr"], {714.0})
        self.assertEqual(labeled["career_war"], {162.1})
        self.assertEqual(labeled[("season_hr", 1927)], {60.0})
        self.assertIn(1927.0, labeled["year"])
        # 714 lives only under career_hr — it is NOT a valid career_war value.
        self.assertNotIn(714.0, labeled["career_war"])


class TestNarrativeFacts(APITestCase):
    def setUp(self):
        cache.clear()
        self.player = make_player(
            "ruthba01", "Babe", "Ruth",
            primary_position="RF",
            debut=datetime.date(1914, 5, 6),
            final_game=datetime.date(1935, 5, 30),
        )
        self.player.birth_date = datetime.date(1895, 2, 6)
        self.player.save()
        add_batting(self.player, 1920, war=11.5, hr=54, avg=0.376, ops=1.382)
        add_batting(self.player, 1921, war=12.9, hr=59, avg=0.378, ops=1.359)
        PlayerAward.objects.create(player=self.player, year=1923, kind="mvp", league="AL")

    def test_facts_include_career_aggregates(self):
        facts = build_facts(self.player)
        self.assertEqual(facts["bio"]["name"], "Babe Ruth")
        self.assertEqual(facts["batting"]["career_hr"], 113)
        self.assertAlmostEqual(facts["career_war_total"], 24.4)
        self.assertEqual(facts["batting"]["peak_year"], 1921)
        self.assertEqual(facts["awards"]["mvp"]["count"], 1)

    def test_allowed_numbers_include_active_years(self):
        facts = build_facts(self.player)
        allowed = allowed_numbers(facts)
        self.assertIn(1925.0, allowed)  # mid-career year, safe to mention

    def test_template_is_fully_grounded(self):
        # The fallback can never emit a number it didn't get from the data.
        facts = build_facts(self.player)
        text = render_template(facts)
        self.assertEqual(verify_numbers(text, allowed_numbers(facts)), [])
        self.assertIn("Babe Ruth", text)


class TestGenerateNarrative(APITestCase):
    def setUp(self):
        cache.clear()
        self.player = make_player(
            "ruthba01", "Babe", "Ruth", primary_position="RF",
            debut=datetime.date(1914, 5, 6), final_game=datetime.date(1935, 5, 30),
        )
        add_batting(self.player, 1920, war=11.5, hr=54, avg=0.376, ops=1.382)

    @override_settings(LLM_ENABLED=False)
    def test_no_key_uses_template(self):
        # No key → deterministic template, no SDK, no network.
        result = generate_narrative(self.player)
        self.assertEqual(result["source"], "template")
        self.assertTrue(result["verified"])
        self.assertIsNone(result["model"])

    @override_settings(LLM_ENABLED=True, NARRATIVE_USE_TOOLS=False, NARRATIVE_MODEL="claude-haiku-4-5-20251001")
    def test_clean_llm_output_is_served(self):
        with patch.object(narrative.llm, "complete_text", return_value="Babe Ruth was a dominant slugger."):
            result = generate_narrative(self.player)
        self.assertEqual(result["source"], "llm")
        self.assertEqual(result["model"], "claude-haiku-4-5-20251001")

    @override_settings(LLM_ENABLED=True, NARRATIVE_USE_TOOLS=False)
    def test_hallucinated_number_falls_back_to_template(self):
        # 999 HR is not in the data; after a failed repair we serve the template.
        with patch.object(narrative.llm, "complete_text", return_value="He hit 999 home runs.") as m:
            result = generate_narrative(self.player)
        self.assertEqual(result["source"], "template")
        self.assertIn("999", result["flagged"])
        self.assertEqual(m.call_count, 2)  # initial draft + one repair attempt

    @override_settings(LLM_ENABLED=True, NARRATIVE_USE_TOOLS=False)
    def test_api_error_falls_back_to_template(self):
        with patch.object(narrative.llm, "complete_text", side_effect=RuntimeError("boom")):
            result = generate_narrative(self.player)
        self.assertEqual(result["source"], "template")
        self.assertTrue(result["verified"])


@override_settings(LLM_ENABLED=False)  # template path → deterministic, no network
class TestNarrativeEndpoint(APITestCase):
    def setUp(self):
        cache.clear()
        self.player = make_player(
            "ruthba01", "Babe", "Ruth", primary_position="RF",
            debut=datetime.date(1914, 5, 6), final_game=datetime.date(1935, 5, 30),
        )
        add_batting(self.player, 1920, war=11.5, hr=54, avg=0.376, ops=1.382)
        self.url = reverse("player-narrative", kwargs={"pk": "ruthba01"})

    def test_returns_200_with_expected_shape(self):
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 200)
        for key in ("text", "source", "verified", "model", "generated_at"):
            self.assertIn(key, r.data)

    def test_404_for_unknown_player(self):
        r = self.client.get(reverse("player-narrative", kwargs={"pk": "nobody00"}))
        self.assertEqual(r.status_code, 404)


# ---------------------------------------------------------------------------
# Tool-calling agent (step 2)
# ---------------------------------------------------------------------------

from players import narrative_tools  # noqa: E402


class _Block:
    """Stand-in for an Anthropic content block (text or tool_use)."""

    def __init__(self, type, text=None, name=None, input=None, id=None):
        self.type = type
        self.text = text
        self.name = name
        self.input = input
        self.id = id


class _Resp:
    def __init__(self, content):
        self.content = content


class TestNarrativeTools(APITestCase):
    def setUp(self):
        cache.clear()
        self.player = make_player(
            "ruthba01", "Babe", "Ruth", primary_position="RF",
            debut=datetime.date(1914, 5, 6), final_game=datetime.date(1935, 5, 30),
        )
        add_batting(self.player, 1920, war=11.5, hr=54, avg=0.376, ops=1.382)
        PlayerAward.objects.create(player=self.player, year=1923, kind="mvp", league="AL")

    def test_get_career_totals_shape(self):
        out = narrative_tools.run_tool("get_career_totals", {"player_id": "ruthba01"}, {})
        self.assertEqual(out["bio"]["name"], "Babe Ruth")
        self.assertEqual(out["batting"]["career_hr"], 54)

    def test_get_awards(self):
        out = narrative_tools.run_tool("get_awards", {"player_id": "ruthba01"}, {})
        self.assertEqual(out["awards"]["mvp"]["count"], 1)

    def test_unknown_player_returns_error(self):
        out = narrative_tools.run_tool("get_career_totals", {"player_id": "nobody00"}, {})
        self.assertIn("error", out)

    def test_unknown_tool_returns_error(self):
        out = narrative_tools.run_tool("get_nonsense", {"player_id": "ruthba01"}, {})
        self.assertIn("error", out)

    def test_facts_cache_resolves_once(self):
        cache_dict = {}
        narrative_tools.run_tool("get_career_totals", {"player_id": "ruthba01"}, cache_dict)
        narrative_tools.run_tool("get_awards", {"player_id": "ruthba01"}, cache_dict)
        self.assertEqual(list(cache_dict.keys()), ["ruthba01"])


class TestAgenticNarrative(APITestCase):
    def setUp(self):
        cache.clear()
        self.player = make_player(
            "ruthba01", "Babe", "Ruth", primary_position="RF",
            debut=datetime.date(1914, 5, 6), final_game=datetime.date(1935, 5, 30),
        )
        add_batting(self.player, 1920, war=11.5, hr=54, avg=0.376, ops=1.382)

    @override_settings(LLM_ENABLED=True, NARRATIVE_USE_TOOLS=True, NARRATIVE_MODEL="claude-haiku-4-5-20251001")
    def test_agent_gathers_facts_then_writes(self):
        # Turn 1: model asks for career totals. Turn 2: writes using a returned number.
        responses = [
            _Resp([_Block("tool_use", name="get_career_totals", input={"player_id": "ruthba01"}, id="t1")]),
            _Resp([_Block("text", text="Babe Ruth compiled 11.5 WAR with 54 home runs.")]),
        ]
        with patch.object(narrative.llm, "complete", side_effect=responses) as m:
            result = generate_narrative(self.player)
        self.assertEqual(result["source"], "llm")
        self.assertEqual(result["model"], "claude-haiku-4-5-20251001")
        self.assertEqual(m.call_count, 2)

    @override_settings(LLM_ENABLED=True, NARRATIVE_USE_TOOLS=True)
    def test_citing_unretrieved_stat_is_flagged(self):
        # Model writes a number without ever calling a tool — nothing is grounded.
        # Draft fails, repair (1) fails too → deterministic fallback with the flag.
        bad = _Resp([_Block("text", text="He hit 73 home runs in 2001.")])
        with patch.object(narrative.llm, "complete", side_effect=[bad, bad]) as m:
            result = generate_narrative(self.player)
        self.assertEqual(result["source"], "template")
        self.assertIn("73", result["flagged"])
        self.assertEqual(result["trace"]["repairs"], 1)
        self.assertEqual(m.call_count, 2)  # draft + one repair

    @override_settings(LLM_ENABLED=True, NARRATIVE_USE_TOOLS=True)
    def test_repair_recovers_after_flagged_draft(self):
        # Draft cites an unretrieved number; after the flag is fed back, the model
        # revises to a grounded sentence and the LLM output is served.
        responses = [
            _Resp([_Block("tool_use", name="get_career_totals", input={"player_id": "ruthba01"}, id="t1")]),
            _Resp([_Block("text", text="He hit 73 home runs.")]),          # unsupported → flagged
            _Resp([_Block("text", text="He compiled 11.5 WAR with 54 home runs.")]),  # grounded
        ]
        with patch.object(narrative.llm, "complete", side_effect=responses):
            result = generate_narrative(self.player)
        self.assertEqual(result["source"], "llm")
        self.assertEqual(result["trace"]["repairs"], 1)

    @override_settings(LLM_ENABLED=True, NARRATIVE_USE_TOOLS=True)
    def test_trace_records_tool_calls(self):
        responses = [
            _Resp([_Block("tool_use", name="get_career_totals", input={"player_id": "ruthba01"}, id="t1")]),
            _Resp([_Block("text", text="Babe Ruth compiled 11.5 WAR.")]),
        ]
        with patch.object(narrative.llm, "complete", side_effect=responses):
            result = generate_narrative(self.player)
        trace = result["trace"]
        self.assertEqual(trace["mode"], "agentic")
        self.assertEqual([t["name"] for t in trace["tool_calls"]], ["get_career_totals"])
        self.assertEqual(trace["model_calls"], 2)
        self.assertEqual(trace["verification"], "passed")

    @override_settings(LLM_ENABLED=True, NARRATIVE_USE_TOOLS=True)
    def test_model_call_budget_exhausts_to_template(self):
        # Agent loops forever asking for tools, never writes prose → hits the
        # model-call cap and falls back deterministically.
        loop = _Resp([_Block("tool_use", name="get_career_totals", input={"player_id": "ruthba01"}, id="t1")])
        with patch.object(narrative.llm, "complete", return_value=loop) as m:
            result = generate_narrative(self.player)
        self.assertEqual(result["source"], "template")
        self.assertEqual(m.call_count, 8)  # _MAX_MODEL_CALLS


@override_settings(LLM_ENABLED=True, NARRATIVE_USE_TOOLS=True, NARRATIVE_TYPED_VERIFY=True,
                   NARRATIVE_MODEL="claude-haiku-4-5-20251001")
class TestAgenticTypedNarrative(APITestCase):
    """Route A: submission via submit_summary with a typed binding per number."""

    def setUp(self):
        cache.clear()
        self.player = make_player(
            "ruthba01", "Babe", "Ruth", primary_position="RF",
            debut=datetime.date(1914, 5, 6), final_game=datetime.date(1935, 5, 30),
        )
        add_batting(self.player, 1920, war=11.5, hr=54, avg=0.376, ops=1.382)

    def _totals(self):
        return _Block("tool_use", name="get_career_totals", input={"player_id": "ruthba01"}, id="t1")

    def test_correctly_bound_submission_is_served(self):
        responses = [
            _Resp([self._totals()]),
            _Resp([_Block("tool_use", name="submit_summary", id="s1", input={
                "text": "Babe Ruth hit 54 home runs and compiled 11.5 WAR.",
                "bindings": [
                    {"value": 54, "stat": "career_hr"},
                    {"value": 11.5, "stat": "career_war"},
                ],
            })]),
        ]
        with patch.object(narrative.llm, "complete", side_effect=responses):
            result = generate_narrative(self.player)
        self.assertEqual(result["source"], "llm")
        self.assertEqual(result["trace"]["mode"], "agentic_typed")
        self.assertEqual(result["trace"]["verification"], "passed")

    def test_cross_stat_misbinding_is_rejected_then_falls_back(self):
        # "54 home runs" is fine, but 11.5 bound to career_hr (it's the WAR) is a
        # cross-stat collision: rejected. One repair, also wrong → template.
        bad = _Resp([_Block("tool_use", name="submit_summary", id="s1", input={
            "text": "He hit 11.5 home runs.",
            "bindings": [{"value": 11.5, "stat": "career_hr"}],
        })])
        responses = [_Resp([self._totals()]), bad, bad]
        with patch.object(narrative.llm, "complete", side_effect=responses):
            result = generate_narrative(self.player)
        self.assertEqual(result["source"], "template")
        self.assertEqual(result["trace"]["repairs"], 1)
        self.assertTrue(any("career_hr" in p for p in result["flagged"]))

    def test_repair_recovers_after_rejected_submission(self):
        responses = [
            _Resp([self._totals()]),
            _Resp([_Block("tool_use", name="submit_summary", id="s1", input={
                "text": "He hit 73 home runs.",  # undeclared/ungrounded
                "bindings": [{"value": 73, "stat": "career_hr"}],
            })]),
            _Resp([_Block("tool_use", name="submit_summary", id="s2", input={
                "text": "He hit 54 home runs.",
                "bindings": [{"value": 54, "stat": "career_hr"}],
            })]),
        ]
        with patch.object(narrative.llm, "complete", side_effect=responses):
            result = generate_narrative(self.player)
        self.assertEqual(result["source"], "llm")
        self.assertEqual(result["trace"]["repairs"], 1)


# ---------------------------------------------------------------------------
# Methodology RAG (step 3)
# ---------------------------------------------------------------------------

from players import rag  # noqa: E402
from players.management.commands.index_methodology import _chunk, _title_of  # noqa: E402
from players.models import MethodologyChunk  # noqa: E402


def _unit_vec(i: int, dim: int = 1024) -> list[float]:
    v = [0.0] * dim
    v[i] = 1.0
    return v


class TestChunking(SimpleTestCase):
    def test_title_from_h1(self):
        self.assertEqual(_title_of("# WAR: Source\n\nbody", "war"), "WAR: Source")

    def test_title_fallback_to_slug(self):
        self.assertEqual(_title_of("no heading", "era-adjusted-metrics"), "Era Adjusted Metrics")

    def test_short_doc_single_chunk(self):
        self.assertEqual(len(_chunk("one short paragraph")), 1)

    def test_long_doc_splits(self):
        para = " ".join(["word"] * 80)
        self.assertGreater(len(_chunk("\n\n".join([para, para, para]))), 1)


class TestStringNumberGrounding(SimpleTestCase):
    def test_numbers_in_retrieved_text_are_allowed(self):
        # Numbers quoted from methodology docs must verify, since they're real.
        allowed: set[float] = set()
        narrative._accumulate_allowed(
            {"results": [{"content": "An OPS+ of 100 is league average; a weight of 2.0 applies."}]},
            allowed,
        )
        self.assertIn(100.0, allowed)
        self.assertIn(2.0, allowed)


@override_settings(RAG_ENABLED=True)
class TestMethodologySearch(APITestCase):
    def setUp(self):
        cache.clear()
        MethodologyChunk.objects.create(
            slug="war", title="WAR", chunk_index=0,
            content="WAR measures total value.", embedding=_unit_vec(0),
        )
        MethodologyChunk.objects.create(
            slug="similarity", title="Similarity", chunk_index=0,
            content="k-NN weighted distance.", embedding=_unit_vec(5),
        )

    def test_returns_nearest_first(self):
        with patch.object(rag.embeddings, "embed_query", return_value=_unit_vec(0)):
            results = rag.search_methodology("what is war", k=2)
        self.assertEqual(results[0]["slug"], "war")
        self.assertEqual(len(results), 2)
        self.assertAlmostEqual(results[0]["score"], 1.0, places=3)

    def test_disabled_returns_empty(self):
        with override_settings(RAG_ENABLED=False):
            self.assertEqual(rag.search_methodology("x"), [])

    def test_empty_corpus_returns_empty(self):
        MethodologyChunk.objects.all().delete()
        with patch.object(rag.embeddings, "embed_query", return_value=_unit_vec(0)):
            self.assertEqual(rag.search_methodology("x"), [])

    def test_embed_error_returns_empty(self):
        with patch.object(rag.embeddings, "embed_query", side_effect=RuntimeError("boom")):
            self.assertEqual(rag.search_methodology("x"), [])

    def test_results_cached_per_query(self):
        # A repeated query is served from cache — no second embed (free-tier safe).
        with patch.object(rag.embeddings, "embed_query", return_value=_unit_vec(0)) as m:
            rag.search_methodology("what is war", k=2)
            rag.search_methodology("what is war", k=2)
        self.assertEqual(m.call_count, 1)


class TestMethodologySearchTool(APITestCase):
    @override_settings(RAG_ENABLED=True)
    def test_tool_returns_results_shape(self):
        MethodologyChunk.objects.create(
            slug="war", title="WAR", chunk_index=0,
            content="WAR measures total value.", embedding=_unit_vec(0),
        )
        with patch.object(rag.embeddings, "embed_query", return_value=_unit_vec(0)):
            out = narrative_tools.run_tool("search_methodology", {"query": "war"}, {})
        self.assertIn("results", out)
        self.assertEqual(out["results"][0]["slug"], "war")


class TestMethodologyEndpoint(APITestCase):
    def test_endpoint_returns_shape(self):
        # RAG disabled by default in tests → empty results but a valid 200 shape.
        r = self.client.get(reverse("player-methodology-search"), {"q": "ops+"})
        self.assertEqual(r.status_code, 200)
        self.assertIn("results", r.data)
        self.assertEqual(r.data["query"], "ops+")


# ---------------------------------------------------------------------------
# Narrative persistence (durable cache) + pre-generation command
# ---------------------------------------------------------------------------

from io import StringIO  # noqa: E402

from django.core.management.base import CommandError  # noqa: E402

from players.models import PlayerNarrative  # noqa: E402


def _fake_result(text="Babe Ruth was great.", source="llm"):
    return {
        "text": text, "source": source, "model": "claude-haiku-4-5-20251001",
        "flagged": [], "trace": {"mode": "agentic", "tool_calls": []}, "generated_at": "t",
    }


class TestNarrativePersistence(APITestCase):
    def setUp(self):
        cache.clear()
        self.player = make_player(
            "ruthba01", "Babe", "Ruth", primary_position="RF",
            debut=datetime.date(1914, 5, 6), final_game=datetime.date(1935, 5, 30),
        )
        add_batting(self.player, 1920, war=11.5, hr=54)

    def test_miss_generates_and_persists(self):
        with patch.object(narrative, "generate_narrative", return_value=_fake_result()) as m:
            result = narrative.get_or_generate(self.player, "2026-05-31")
        self.assertEqual(m.call_count, 1)
        self.assertEqual(result["text"], "Babe Ruth was great.")
        self.assertTrue(
            PlayerNarrative.objects.filter(player=self.player, data_version="2026-05-31").exists()
        )

    def test_hit_does_not_regenerate(self):
        with patch.object(narrative, "generate_narrative", return_value=_fake_result()) as m:
            narrative.get_or_generate(self.player, "2026-05-31")
            narrative.get_or_generate(self.player, "2026-05-31")
        self.assertEqual(m.call_count, 1)  # second served from the DB

    def test_new_data_version_regenerates(self):
        with patch.object(narrative, "generate_narrative", return_value=_fake_result()) as m:
            narrative.get_or_generate(self.player, "2026-05-31")
            narrative.get_or_generate(self.player, "2026-06-01")
        self.assertEqual(m.call_count, 2)
        rows = PlayerNarrative.objects.filter(player=self.player)
        self.assertEqual(rows.count(), 1)  # one row, overwritten in place
        self.assertEqual(rows.get().data_version, "2026-06-01")

    def test_force_regenerates_on_hit(self):
        with patch.object(narrative, "generate_narrative", return_value=_fake_result()) as m:
            narrative.get_or_generate(self.player, "v")
            narrative.get_or_generate(self.player, "v", force=True)
        self.assertEqual(m.call_count, 2)

    def test_as_dict_shape(self):
        n = PlayerNarrative.objects.create(player=self.player, text="t", source="template")
        d = n.as_dict()
        self.assertTrue(d["verified"])
        for key in ("text", "source", "model", "flagged", "trace", "generated_at"):
            self.assertIn(key, d)


class TestNarrativeEndpointPersists(APITestCase):
    def setUp(self):
        cache.clear()
        self.player = make_player(
            "ruthba01", "Babe", "Ruth", primary_position="RF",
            debut=datetime.date(1914, 5, 6), final_game=datetime.date(1935, 5, 30),
        )
        add_batting(self.player, 1920, war=11.5, hr=54)
        self.url = reverse("player-narrative", kwargs={"pk": "ruthba01"})

    def test_second_request_served_from_db(self):
        with patch.object(narrative, "generate_narrative", return_value=_fake_result()) as m:
            r1 = self.client.get(self.url)
            r2 = self.client.get(self.url)
        self.assertEqual(r1.status_code, 200)
        self.assertEqual(r2.data["text"], "Babe Ruth was great.")
        self.assertEqual(m.call_count, 1)  # persisted after the first request


class TestPregenerateCommand(APITestCase):
    def setUp(self):
        cache.clear()
        self.player = make_player("ruthba01", "Babe", "Ruth")
        add_batting(self.player, 1920, war=11.5, hr=54)

    def test_requires_bounding_argument(self):
        with self.assertRaises(CommandError):
            call_command("pregenerate_narratives")

    def test_generates_for_given_ids(self):
        with patch.object(narrative, "generate_narrative", return_value=_fake_result()):
            call_command("pregenerate_narratives", "--bbref-ids", "ruthba01", stdout=StringIO())
        self.assertTrue(PlayerNarrative.objects.filter(player_id="ruthba01").exists())

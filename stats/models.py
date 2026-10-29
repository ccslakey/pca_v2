from django.db import models

from players.models import Player


class BattingSeason(models.Model):
    player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='batting_seasons')
    year   = models.SmallIntegerField(db_index=True)
    stint  = models.SmallIntegerField(default=1)
    team   = models.CharField(max_length=4)
    league = models.CharField(max_length=3, null=True)

    games            = models.SmallIntegerField(null=True)
    plate_appearances = models.IntegerField(null=True)
    at_bats          = models.IntegerField(null=True)
    runs             = models.SmallIntegerField(null=True)
    hits             = models.SmallIntegerField(null=True)
    doubles          = models.SmallIntegerField(null=True)
    triples          = models.SmallIntegerField(null=True)
    home_runs        = models.SmallIntegerField(null=True)
    rbi              = models.SmallIntegerField(null=True)
    stolen_bases     = models.SmallIntegerField(null=True)
    caught_stealing  = models.SmallIntegerField(null=True)
    walks            = models.SmallIntegerField(null=True)
    strikeouts       = models.SmallIntegerField(null=True)
    ibb              = models.SmallIntegerField(null=True)
    hbp              = models.SmallIntegerField(null=True)
    sacrifice_hits   = models.SmallIntegerField(null=True)
    sacrifice_flies  = models.SmallIntegerField(null=True)
    gidp             = models.SmallIntegerField(null=True)
    total_bases      = models.SmallIntegerField(null=True)

    batting_avg  = models.FloatField(null=True)
    on_base_pct  = models.FloatField(null=True)
    slugging_pct = models.FloatField(null=True)
    ops          = models.FloatField(null=True)
    ops_plus     = models.SmallIntegerField(null=True)
    war          = models.FloatField(null=True)

    class Meta:
        unique_together = ('player', 'year', 'stint', 'team')
        indexes = [
            models.Index(fields=['year']),
            models.Index(fields=['player', 'year']),
        ]

    def __str__(self):
        return f"{self.player_id} {self.year} {self.team} stint={self.stint}"


class PitchingSeason(models.Model):
    player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='pitching_seasons')
    year   = models.SmallIntegerField(db_index=True)
    stint  = models.SmallIntegerField(default=1)
    team   = models.CharField(max_length=4)
    league = models.CharField(max_length=3, null=True)

    wins            = models.SmallIntegerField(null=True)
    losses          = models.SmallIntegerField(null=True)
    games           = models.SmallIntegerField(null=True)
    games_started   = models.SmallIntegerField(null=True)
    complete_games  = models.SmallIntegerField(null=True)
    sho             = models.SmallIntegerField(null=True)
    saves           = models.SmallIntegerField(null=True)
    games_finished  = models.SmallIntegerField(null=True)
    ip_outs         = models.IntegerField(null=True)
    hits_allowed    = models.SmallIntegerField(null=True)
    runs_allowed    = models.SmallIntegerField(null=True)
    earned_runs     = models.SmallIntegerField(null=True)
    home_runs       = models.SmallIntegerField(null=True)
    walks           = models.SmallIntegerField(null=True)
    ibb             = models.SmallIntegerField(null=True)
    strikeouts      = models.SmallIntegerField(null=True)
    hbp             = models.SmallIntegerField(null=True)
    wild_pitches    = models.SmallIntegerField(null=True)
    balks           = models.SmallIntegerField(null=True)
    bfp             = models.IntegerField(null=True)
    sacrifice_flies = models.SmallIntegerField(null=True)
    gidp            = models.SmallIntegerField(null=True)

    era                  = models.FloatField(null=True)
    era_plus             = models.SmallIntegerField(null=True)
    fip                  = models.FloatField(null=True)
    whip                 = models.FloatField(null=True)
    hits_per_nine        = models.FloatField(null=True)
    home_runs_per_nine   = models.FloatField(null=True)
    walks_per_nine       = models.FloatField(null=True)
    strikeouts_per_nine  = models.FloatField(null=True)
    strikeouts_per_walk  = models.FloatField(null=True)
    war                  = models.FloatField(null=True)

    class Meta:
        unique_together = ('player', 'year', 'stint', 'team')
        indexes = [
            models.Index(fields=['year']),
            models.Index(fields=['player', 'year']),
        ]

    def __str__(self):
        return f"{self.player_id} {self.year} {self.team} stint={self.stint}"


class FieldingSeason(models.Model):
    player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='fielding_seasons')
    year   = models.SmallIntegerField(db_index=True)
    stint  = models.SmallIntegerField(default=1)
    team   = models.CharField(max_length=4)
    league = models.CharField(max_length=3, null=True)
    age    = models.SmallIntegerField(null=True)

    games          = models.SmallIntegerField(null=True)
    games_started  = models.SmallIntegerField(null=True)
    complete_games = models.SmallIntegerField(null=True)
    innings_outs   = models.IntegerField(null=True)
    chances        = models.SmallIntegerField(null=True)
    putouts        = models.SmallIntegerField(null=True)
    assists        = models.SmallIntegerField(null=True)
    errors         = models.SmallIntegerField(null=True)
    double_plays   = models.SmallIntegerField(null=True)
    fielding_pct   = models.FloatField(null=True)
    rtot           = models.SmallIntegerField(null=True)
    rtot_per_year  = models.SmallIntegerField(null=True)
    rdrs           = models.SmallIntegerField(null=True)
    rdrs_per_year  = models.SmallIntegerField(null=True)
    range_factor_per_nine        = models.FloatField(null=True)
    league_range_factor_per_nine = models.FloatField(null=True)
    range_factor_per_game        = models.FloatField(null=True)
    league_range_factor_per_game = models.FloatField(null=True)
    passed_balls       = models.SmallIntegerField(null=True)
    wild_pitches       = models.SmallIntegerField(null=True)
    stolen_bases       = models.SmallIntegerField(null=True)
    caught_stealing    = models.SmallIntegerField(null=True)
    caught_stealing_pct = models.FloatField(null=True)
    pickoffs           = models.SmallIntegerField(null=True)
    positions_raw      = models.CharField(max_length=30, null=True, blank=True)

    class Meta:
        unique_together = ('player', 'year', 'stint', 'team')
        indexes = [
            models.Index(fields=['year']),
            models.Index(fields=['player', 'year']),
            models.Index(fields=['positions_raw']),
        ]

    def __str__(self):
        return f"{self.player_id} {self.year} {self.team} fielding stint={self.stint}"


class FieldingPositionToken(models.Model):
    fielding_season = models.ForeignKey(
        FieldingSeason,
        on_delete=models.CASCADE,
        related_name='position_tokens',
    )
    rank = models.SmallIntegerField()
    position = models.CharField(max_length=5)
    is_primary_marker = models.BooleanField(default=False)
    is_minor_marker = models.BooleanField(default=False)
    is_career_major_marker = models.BooleanField(default=False)
    is_career_minor_marker = models.BooleanField(default=False)
    reported_games = models.SmallIntegerField(null=True)

    class Meta:
        unique_together = ('fielding_season', 'rank')
        indexes = [
            models.Index(fields=['position']),
            models.Index(fields=['fielding_season', 'position']),
        ]
        ordering = ['rank']

    def __str__(self):
        return f"{self.fielding_season_id} {self.rank}:{self.position}"


class PlayerAward(models.Model):
    class Kind(models.TextChoices):
        MVP       = 'mvp',       'Most Valuable Player'
        CY        = 'cy',        'Cy Young Award'
        ROTY      = 'roty',      'Rookie of the Year'
        GG        = 'gg',        'Gold Glove'
        SS        = 'ss',        'Silver Slugger'
        TC_B      = 'tc_b',      'Triple Crown (Batting)'
        TC_P      = 'tc_p',      'Triple Crown (Pitching)'
        HOF       = 'hof',       'Hall of Fame'
        POSTMVP   = 'postmvp',   'Postseason MVP'
        BAT_TITLE = 'bat_title', 'Batting Title'
        ERA_TITLE = 'era_title', 'ERA Title'
        ALL_MLB   = 'all_mlb',   'All-MLB Team'
        WS        = 'ws',        'World Series Champion'
        ASG       = 'asg',       'All-Star Game'

    player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='awards')
    year   = models.SmallIntegerField()
    kind   = models.CharField(max_length=12, choices=Kind.choices)
    league = models.CharField(max_length=3, null=True, blank=True)  # AL/NL or 1st/2nd for All-MLB
    notes  = models.CharField(max_length=50, null=True, blank=True) # position (GG/SS/All-MLB), WS/ALCS/NLCS (postmvp)

    class Meta:
        unique_together = [('player', 'year', 'kind', 'league')]
        indexes = [models.Index(fields=['player', 'year'])]

    def __str__(self):
        return f"{self.player_id} {self.year} {self.kind}"


# The pitch zone heatmap's grid: GRID x GRID cells over these plate coordinates, in feet.
# frontend/src/components/profile/charts/PitchZone.tsx draws the same one.
ZONE_X_MIN, ZONE_X_MAX = -2.0, 2.0
ZONE_Z_MIN, ZONE_Z_MAX = 0.5, 5.0
ZONE_GRID = 20


def zone_cell_center(cell_x: int, cell_z: int) -> tuple[float, float]:
    """A cell's centre in plate coordinates (feet), as the heatmap places it."""
    x = ZONE_X_MIN + (cell_x + 0.5) * (ZONE_X_MAX - ZONE_X_MIN) / ZONE_GRID
    z = ZONE_Z_MAX - (cell_z + 0.5) * (ZONE_Z_MAX - ZONE_Z_MIN) / ZONE_GRID
    return round(x, 4), round(z, 4)


class StatcastZoneCell(models.Model):
    """
    Statcast pitches by heatmap cell, for the pitch zone heatmap: for one
    player, role and season, every pitch whose plate location falls in the
    cell, and how many of those were contact, hits and whiffs. A cell with
    pitches but none of an outcome stores 0 for it, so every rate has its
    true denominator. cell_x counts from ZONE_X_MIN and cell_z from
    ZONE_Z_MAX (the top), as the heatmap draws them. A pitch outside the
    grid lands in a cell outside 0..ZONE_GRID-1: the heatmap leaves it out,
    and totals keep it.
    """

    class Role(models.TextChoices):
        BATTER  = 'B', 'Batter'
        PITCHER = 'P', 'Pitcher'

    player  = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='zone_cells')
    role    = models.CharField(max_length=1, choices=Role.choices)
    season  = models.PositiveSmallIntegerField()
    cell_x  = models.SmallIntegerField()
    cell_z  = models.SmallIntegerField()
    pitches = models.IntegerField()  # every pitch in the cell
    contact = models.IntegerField()  # put in play
    hits    = models.IntegerField()  # singles, doubles, triples and home runs
    whiffs  = models.IntegerField()  # swinging strikes

    class Meta:
        unique_together = ('player', 'role', 'season', 'cell_x', 'cell_z')

    def __str__(self):
        return f"{self.player_id} {self.role} {self.season} ({self.cell_x}, {self.cell_z})"

class IngestionLog(models.Model):
    source       = models.CharField(max_length=50)   # e.g. 'bref_batting_MLB_2023'
    rows_loaded  = models.IntegerField(default=0)
    completed_at = models.DateTimeField(auto_now_add=True)
    status       = models.CharField(max_length=10)   # 'success', 'error'
    error_msg    = models.TextField(blank=True)

    def __str__(self):
        return f"{self.source} ({self.status}) @ {self.completed_at:%Y-%m-%d %H:%M}"


class JamesScore(models.Model):
    player = models.OneToOneField(Player, on_delete=models.CASCADE, related_name='james_score')

    black_ink_bat   = models.SmallIntegerField(default=0)
    gray_ink_bat    = models.SmallIntegerField(default=0)
    hof_monitor_bat = models.SmallIntegerField(default=0)

    black_ink_pit   = models.SmallIntegerField(default=0)
    gray_ink_pit    = models.SmallIntegerField(default=0)
    hof_monitor_pit = models.SmallIntegerField(default=0)

    last_computed = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.player_id} HOFM bat={self.hof_monitor_bat} pit={self.hof_monitor_pit}"

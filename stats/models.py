from django.db import models
from players.models import Player


class BattingSeason(models.Model):
    """
    Season-level batting stats scraped from BRef standard batting pages.
    One row per player / year / team stint.

    Columns available on BRef vary by era — pre-1950s stats like SF, IBB,
    GIDP may be null even when the player record itself exists.

    Acronym rule: 3+ letter acronyms kept (rbi, ibb, hbp, gidp, ops, war).
    1–2 letter abbreviations use full names.
    """
    player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='batting_seasons')
    year   = models.SmallIntegerField(db_index=True)
    stint  = models.SmallIntegerField(default=1)
    team   = models.CharField(max_length=4)
    league = models.CharField(max_length=3, null=True)

    # Counting stats
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
    ibb              = models.SmallIntegerField(null=True)   # tracked ~1955+
    hbp              = models.SmallIntegerField(null=True)
    sacrifice_hits   = models.SmallIntegerField(null=True)
    sacrifice_flies  = models.SmallIntegerField(null=True)   # tracked ~1954+
    gidp             = models.SmallIntegerField(null=True)
    total_bases      = models.SmallIntegerField(null=True)

    # Rate / advanced stats (BRef computes and includes on the standard page)
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
    """
    Season-level pitching stats scraped from BRef standard pitching pages.
    One row per player / year / team stint.

    ip_outs stores innings pitched as total outs recorded (IP × 3, with
    fractional innings converted: "6.1" → 19, "6.2" → 20).

    Acronym rule: 3+ letter acronyms kept (era, ibb, hbp, sho, bfp, gidp, fip, war).
    sacrifice_hits against omitted — not present on BRef standard pitching page.
    """
    player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='pitching_seasons')
    year   = models.SmallIntegerField(db_index=True)
    stint  = models.SmallIntegerField(default=1)
    team   = models.CharField(max_length=4)
    league = models.CharField(max_length=3, null=True)

    # Counting stats
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

    # Rate / advanced stats (BRef includes on the standard page)
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


class PlayerAward(models.Model):
    """
    One row per award instance. Career milestones like HOF use the induction
    year; All-Star career totals are stored on the Player model instead.
    """

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


class IngestionLog(models.Model):
    """Tracks completed ingestion runs to allow safe re-runs."""
    source       = models.CharField(max_length=50)   # e.g. 'bref_batting_MLB_2023'
    rows_loaded  = models.IntegerField(default=0)
    completed_at = models.DateTimeField(auto_now_add=True)
    status       = models.CharField(max_length=10)   # 'success', 'error'
    error_msg    = models.TextField(blank=True)

    def __str__(self):
        return f"{self.source} ({self.status}) @ {self.completed_at:%Y-%m-%d %H:%M}"

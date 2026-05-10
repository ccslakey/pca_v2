from django.db import models


class Player(models.Model):
    """
    One row per MLB player, keyed by their Baseball Reference player ID
    (e.g. "ruthba01"). This ID is also Lahman's playerID and is embedded
    directly in BRef pages via data-append-csv attributes.

    mlbam_id is populated from the Chadwick register cross-reference and
    is required to join with Statcast data (2015+).
    """
    bbref_id = models.CharField(max_length=20, primary_key=True)

    mlbam_id     = models.IntegerField(null=True, unique=True, db_index=True)
    fangraphs_id = models.IntegerField(null=True, db_index=True)
    retro_id     = models.CharField(max_length=20, null=True)

    first_name = models.CharField(max_length=100)
    last_name  = models.CharField(max_length=100)

    birth_year    = models.SmallIntegerField(null=True)
    birth_country = models.CharField(max_length=100, null=True)
    bats          = models.CharField(max_length=1, null=True)   # R, L, B
    throws        = models.CharField(max_length=1, null=True)   # R, L
    debut         = models.DateField(null=True)
    final_game    = models.DateField(null=True)

    mlb_played_first = models.SmallIntegerField(null=True)
    mlb_played_last  = models.SmallIntegerField(null=True)

    # All-Star career totals (per-year selections not available without per-game scraping)
    asg_games = models.SmallIntegerField(null=True)
    asg_first = models.SmallIntegerField(null=True)
    asg_last  = models.SmallIntegerField(null=True)

    class Meta:
        indexes = [
            models.Index(fields=['last_name', 'first_name']),
            models.Index(fields=['mlb_played_first', 'mlb_played_last']),
        ]

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.bbref_id})"

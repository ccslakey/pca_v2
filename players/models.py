from django.db import models
from pgvector.django import VectorField


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

    birth_date    = models.DateField(null=True)
    birth_country = models.CharField(max_length=100, null=True)
    bats          = models.CharField(max_length=1, null=True)   # R, L, B
    throws        = models.CharField(max_length=1, null=True)   # R, L
    debut         = models.DateField(null=True)
    final_game    = models.DateField(null=True)
    primary_position = models.CharField(max_length=3, null=True, db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=['last_name', 'first_name']),
            models.Index(fields=['debut', 'final_game']),
        ]

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.bbref_id})"


class MethodologyChunk(models.Model):
    """
    A chunk of the methodology documentation (frontend/src/methodology/*.md),
    embedded for semantic retrieval. Populated by `manage.py index_methodology`
    and queried by the narrative agent's `search_methodology` tool so it can
    explain a metric in the project's own words.

    At this corpus size (~10 docs) exact KNN over the vectors is instant, so no
    ANN (HNSW/IVFFlat) index is defined — that would only earn its keep past
    tens of thousands of rows.
    """
    slug        = models.CharField(max_length=50, db_index=True)  # article slug, e.g. "war"
    title       = models.CharField(max_length=120)
    chunk_index = models.SmallIntegerField()
    content     = models.TextField()
    embedding   = VectorField(dimensions=1024)

    class Meta:
        unique_together = ('slug', 'chunk_index')
        indexes = [models.Index(fields=['slug'])]

    def __str__(self):
        return f"{self.slug}#{self.chunk_index} ({self.title})"


class PlayerNarrative(models.Model):
    """
    A persisted, grounded career summary for one player. Durable cache for the
    LLM agent's output: generation is several model round-trips, so we store the
    result and serve it instantly on repeat views.

    `data_version` is the latest successful ingest date at generation time — when
    data refreshes it changes, so a stored narrative for an older version is
    treated as a miss and regenerated. One row per player (latest version wins).
    """
    player       = models.OneToOneField(Player, on_delete=models.CASCADE, related_name='narrative')
    text         = models.TextField()
    source       = models.CharField(max_length=12)            # "llm" | "template"
    model        = models.CharField(max_length=60, null=True, blank=True)
    flagged      = models.JSONField(default=list)             # numbers the verifier rejected
    trace        = models.JSONField(default=dict)             # agent run trace
    data_version = models.CharField(max_length=20, null=True, blank=True)
    generated_at = models.DateTimeField(auto_now=True)

    def as_dict(self) -> dict:
        return {
            "text": self.text,
            "source": self.source,
            "verified": True,
            "model": self.model,
            "flagged": self.flagged,
            "trace": self.trace,
            "generated_at": self.generated_at.isoformat(),
        }

    def __str__(self):
        return f"narrative({self.player_id}, {self.source})"

from rest_framework import serializers

from stats.models import JamesScore

from .models import Player
from .percentiles import war_percentile


class PlayerListSerializer(serializers.ModelSerializer[Player]):
    """Compact serializer for search results and autocomplete."""

    class Meta:
        model = Player
        fields = [
            "bbref_id",
            "first_name",
            "last_name",
            "debut",
            "final_game",
            "bats",
            "throws",
            "primary_position",
        ]


class JamesScoreSerializer(serializers.ModelSerializer[JamesScore]):
    class Meta:
        model = JamesScore
        fields = [
            "black_ink_bat", "gray_ink_bat", "hof_monitor_bat",
            "black_ink_pit", "gray_ink_pit", "hof_monitor_pit",
        ]


class PlayerDetailSerializer(serializers.ModelSerializer[Player]):
    """Full player profile including all bio fields."""

    james_score = JamesScoreSerializer(read_only=True)
    war_percentile = serializers.SerializerMethodField()

    def get_war_percentile(self, obj: Player) -> dict | None:
        return war_percentile(obj.bbref_id, obj.primary_position)

    class Meta:
        model = Player
        fields = [
            "bbref_id",
            "mlbam_id",
            "fangraphs_id",
            "retro_id",
            "first_name",
            "last_name",
            "birth_date",
            "birth_country",
            "bats",
            "throws",
            "debut",
            "final_game",
            "primary_position",
            "james_score",
            "war_percentile",
        ]

from rest_framework import serializers

from .models import Player
from stats.models import JamesScore


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

    class Meta:
        model = Player
        fields = "__all__"

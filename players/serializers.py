from rest_framework import serializers

from .models import Player


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


class PlayerDetailSerializer(serializers.ModelSerializer[Player]):
    """Full player profile including all bio fields."""

    class Meta:
        model = Player
        fields = "__all__"

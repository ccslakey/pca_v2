from rest_framework import serializers

from .models import (
    BattingSeason,
    FieldingPositionToken,
    FieldingSeason,
    PitchingSeason,
    PlayerAward,
    StatcastZoneBucket,
)


class BattingSeasonSerializer(serializers.ModelSerializer[BattingSeason]):
    class Meta:
        model = BattingSeason
        fields = '__all__'


class PitchingSeasonSerializer(serializers.ModelSerializer[PitchingSeason]):
    class Meta:
        model = PitchingSeason
        fields = '__all__'


class FieldingPositionTokenSerializer(serializers.ModelSerializer[FieldingPositionToken]):
    class Meta:
        model = FieldingPositionToken
        fields = [
            'rank',
            'position',
            'is_primary_marker',
            'is_minor_marker',
            'is_career_major_marker',
            'is_career_minor_marker',
            'reported_games',
        ]


class FieldingSeasonSerializer(serializers.ModelSerializer[FieldingSeason]):
    position_tokens = FieldingPositionTokenSerializer(many=True, read_only=True)

    class Meta:
        model = FieldingSeason
        fields = '__all__'


class PlayerAwardSerializer(serializers.ModelSerializer[PlayerAward]):
    class Meta:
        model = PlayerAward
        fields = ['id', 'year', 'kind', 'league', 'notes']


class StatcastZoneBucketSerializer(serializers.ModelSerializer[StatcastZoneBucket]):
    class Meta:
        model = StatcastZoneBucket
        fields = ['plate_x', 'plate_z', 'count', 'total']

from rest_framework import serializers
from .models import BattingSeason, PitchingSeason, PlayerAward, StatcastZoneBucket


class BattingSeasonSerializer(serializers.ModelSerializer[BattingSeason]):
    class Meta:
        model = BattingSeason
        fields = '__all__'


class PitchingSeasonSerializer(serializers.ModelSerializer[PitchingSeason]):
    class Meta:
        model = PitchingSeason
        fields = '__all__'


class PlayerAwardSerializer(serializers.ModelSerializer[PlayerAward]):
    class Meta:
        model = PlayerAward
        fields = ['id', 'year', 'kind', 'league', 'notes']

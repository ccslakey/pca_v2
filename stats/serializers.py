from rest_framework import serializers
from .models import BattingSeason, PitchingSeason


class BattingSeasonSerializer(serializers.ModelSerializer[BattingSeason]):
    class Meta:
        model = BattingSeason
        fields = '__all__'


class PitchingSeasonSerializer(serializers.ModelSerializer[PitchingSeason]):
    class Meta:
        model = PitchingSeason
        fields = '__all__'

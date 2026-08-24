from rest_framework import serializers

from .models import ActivityEntry, NutritionEntry, WeightEntry


class WeightEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = WeightEntry
        fields = ["id", "date", "weight_kg", "body_fat_pct", "notes", "created_at"]

    def validate_weight_kg(self, value):
        if not (30 <= value <= 300):
            raise serializers.ValidationError("Peso fuera de rango razonable")
        return value


class ActivityEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = ActivityEntry
        fields = [
            "id",
            "date",
            "activity_type",
            "title",
            "duration_min",
            "distance_km",
            "avg_hr",
            "max_hr",
            "avg_speed_kmh",
            "elevation_m",
            "calories",
            "perceived_effort",
            "plan_day",
            "notes",
            "created_at",
        ]

    def validate(self, attrs):
        for field in ("avg_hr", "max_hr"):
            v = attrs.get(field)
            if v is not None and not (30 <= v <= 250):
                raise serializers.ValidationError({field: "Pulsaciones fuera de rango"})
        effort = attrs.get("perceived_effort")
        if effort is not None and not (1 <= effort <= 10):
            raise serializers.ValidationError({"perceived_effort": "RPE debe ser 1-10"})
        return attrs


class NutritionEntrySerializer(serializers.ModelSerializer):
    adherence = serializers.FloatField(read_only=True)

    class Meta:
        model = NutritionEntry
        fields = [
            "id",
            "date",
            "meals",
            "calories_estimate",
            "water_l",
            "notes",
            "adherence",
            "created_at",
        ]

    def validate_meals(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("meals must be a list")
        for meal in value:
            if not isinstance(meal, dict) or "name" not in meal or "status" not in meal:
                raise serializers.ValidationError("Each meal needs name and status")
            if meal["status"] not in ("full", "partial", "skipped"):
                raise serializers.ValidationError("status must be full|partial|skipped")
        return value

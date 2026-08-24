from datetime import date, timedelta

from rest_framework import serializers

from .models import Goal


class GoalSerializer(serializers.ModelSerializer):
    has_plan = serializers.SerializerMethodField()

    class Meta:
        model = Goal
        fields = [
            "id",
            "target_weight_kg",
            "target_date",
            "motivation",
            "status",
            "admin_message",
            "suggested_target_weight_kg",
            "suggested_target_date",
            "reviewed_at",
            "start_weight_kg",
            "start_date",
            "created_at",
            "has_plan",
        ]
        read_only_fields = [
            "status",
            "admin_message",
            "suggested_target_weight_kg",
            "suggested_target_date",
            "reviewed_at",
            "start_weight_kg",
            "start_date",
            "created_at",
        ]

    def get_has_plan(self, goal):
        return hasattr(goal, "plan")

    def validate_target_date(self, value):
        if value <= date.today() + timedelta(days=6):
            raise serializers.ValidationError("La fecha objetivo debe estar al menos a una semana")
        return value

    def validate_target_weight_kg(self, value):
        if not (30 <= value <= 300):
            raise serializers.ValidationError("Peso objetivo fuera de rango razonable")
        return value

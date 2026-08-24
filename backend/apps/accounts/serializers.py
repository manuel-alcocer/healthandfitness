from rest_framework import serializers

from .models import Profile, User


class ProfileSerializer(serializers.ModelSerializer):
    age = serializers.IntegerField(read_only=True)
    bmi = serializers.FloatField(read_only=True)

    class Meta:
        model = Profile
        exclude = ["user"]
        read_only_fields = ["created_at", "updated_at"]

    def validate_preferred_activities(self, value):
        allowed = {"walk", "run", "swim", "bike", "gym", "hike", "other"}
        if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
            raise serializers.ValidationError("Must be a list of activity slugs")
        bad = set(value) - allowed
        if bad:
            raise serializers.ValidationError(f"Unknown activities: {sorted(bad)}")
        return value


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email", "first_name", "last_name", "avatar_url", "is_staff"]
        read_only_fields = fields

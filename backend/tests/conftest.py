from datetime import date, timedelta

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import Profile, User
from apps.goals.models import Goal


@pytest.fixture
def user(db):
    return User.objects.create_user(username="ana@example.com", email="ana@example.com")


@pytest.fixture
def profile(user):
    return Profile.objects.create(
        user=user,
        sex="F",
        birth_date=date(1990, 5, 1),
        height_cm=165,
        initial_weight_kg="78.50",
        activity_level="light",
        training_days_per_week=4,
        preferred_activities=["walk", "gym"],
    )


@pytest.fixture
def api(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def admin_api(settings):
    settings.ADMIN_API_TOKEN = "test-admin-token"
    client = APIClient()
    client.credentials(HTTP_X_ADMIN_TOKEN="test-admin-token")
    return client


@pytest.fixture
def pending_goal(user, profile):
    return Goal.objects.create(
        user=user,
        target_weight_kg="70.00",
        target_date=date.today() + timedelta(weeks=16),
        start_weight_kg=profile.initial_weight_kg,
    )


def make_plan_data(start=None, weeks=16, start_weight=78.5, end_weight=70.0):
    start = start or date.today()
    targets = []
    for week in range(weeks + 1):
        frac = week / weeks
        targets.append(
            {
                "week": week,
                "date": (start + timedelta(weeks=week)).isoformat(),
                "weight_kg": round(start_weight + (end_weight - start_weight) * frac, 1),
            }
        )
    return {
        "summary": "Plan de prueba",
        "daily_calories": 1800,
        "macros": {"protein_g": 120, "carbs_g": 180, "fat_g": 55},
        "nutrition": {
            "guidelines": ["Bebe 2L de agua"],
            "meals": [
                {"name": "Desayuno", "time": "08:00", "options": ["Avena con fruta"]},
                {"name": "Comida", "time": "14:00", "options": ["Pollo con arroz"]},
                {"name": "Cena", "time": "21:00", "options": ["Pescado con verdura"]},
            ],
        },
        "exercise": {
            "guidelines": ["Calienta antes de cada sesión"],
            "weekly_schedule": [
                {"day": 1, "type": "walk", "title": "Caminata",
                 "target": {"distance_km": 5, "duration_min": 60}},
                {"day": 3, "type": "gym", "title": "Fuerza",
                 "target": {"duration_min": 45}},
                {"day": 5, "type": "walk", "title": "Caminata",
                 "target": {"distance_km": 5, "duration_min": 60}},
                {"day": 7, "type": "rest", "title": "Descanso"},
            ],
        },
        "weekly_weight_targets": targets,
    }

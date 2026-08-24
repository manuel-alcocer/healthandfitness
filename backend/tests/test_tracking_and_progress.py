from datetime import date

import pytest

from apps.goals.models import Goal
from apps.plans.models import Plan
from apps.tracking.progress import expected_weight_at

from .conftest import make_plan_data

pytestmark = pytest.mark.django_db


@pytest.fixture
def active_goal(pending_goal):
    pending_goal.status = Goal.Status.ACTIVE
    pending_goal.save()
    Plan.objects.create(
        goal=pending_goal, data=make_plan_data(start=date.today()), start_date=date.today()
    )
    return pending_goal


def test_weight_upsert_by_date(api):
    resp = api.post(
        "/api/tracking/weights", {"date": "2026-08-20", "weight_kg": "78.0"}, format="json"
    )
    assert resp.status_code == 201
    resp = api.post(
        "/api/tracking/weights", {"date": "2026-08-20", "weight_kg": "77.6"}, format="json"
    )
    assert resp.status_code == 200
    resp = api.get("/api/tracking/weights")
    assert resp.data["count"] == 1
    assert float(resp.data["results"][0]["weight_kg"]) == 77.6


def test_activity_validation(api):
    resp = api.post(
        "/api/tracking/activities",
        {"date": "2026-08-20", "activity_type": "run", "duration_min": 40, "avg_hr": 500},
        format="json",
    )
    assert resp.status_code == 400
    resp = api.post(
        "/api/tracking/activities",
        {
            "date": "2026-08-20",
            "activity_type": "run",
            "duration_min": 40,
            "distance_km": "6.2",
            "avg_hr": 148,
            "max_hr": 171,
            "avg_speed_kmh": "9.3",
        },
        format="json",
    )
    assert resp.status_code == 201


def test_nutrition_upsert_and_adherence(api):
    meals = [
        {"name": "Desayuno", "status": "full"},
        {"name": "Comida", "status": "partial"},
        {"name": "Cena", "status": "skipped"},
    ]
    resp = api.post(
        "/api/tracking/nutrition", {"date": "2026-08-20", "meals": meals}, format="json"
    )
    assert resp.status_code == 201
    assert resp.data["adherence"] == 0.5


def test_expected_weight_interpolation():
    targets = [
        {"week": 0, "date": "2026-01-05", "weight_kg": 90.0},
        {"week": 2, "date": "2026-01-19", "weight_kg": 88.0},
    ]
    assert expected_weight_at(targets, date(2026, 1, 5)) == 90.0
    assert expected_weight_at(targets, date(2026, 1, 12)) == 89.0
    assert expected_weight_at(targets, date(2026, 2, 1)) == 88.0


def test_progress_no_goal(api):
    resp = api.get("/api/progress")
    assert resp.status_code == 200
    assert resp.data["state"] == "no_active_goal"


def test_progress_on_track(api, active_goal, user):
    today = date.today()
    api.post(
        "/api/tracking/weights",
        {"date": today.isoformat(), "weight_kg": "78.40"},
        format="json",
    )
    api.post(
        "/api/tracking/activities",
        {"date": today.isoformat(), "activity_type": "walk", "duration_min": 60,
         "distance_km": "5.0"},
        format="json",
    )
    resp = api.get("/api/progress")
    assert resp.status_code == 200
    data = resp.data
    assert data["state"] == "active"
    assert data["weight"]["status"] == "on_track"
    assert data["exercise_week"]["sessions_planned"] == 3
    assert data["exercise_week"]["sessions_done"] == 1
    assert data["verdict"]["status"] in ("on_track", "at_risk")
    assert data["streak_days"] >= 1
    assert len(data["weekly_exercise"]) == 12


def test_progress_behind(api, active_goal):
    today = date.today()
    # 3 kg above the expected curve -> clearly behind on a loss goal.
    api.post(
        "/api/tracking/weights",
        {"date": today.isoformat(), "weight_kg": "81.50"},
        format="json",
    )
    resp = api.get("/api/progress")
    assert resp.data["weight"]["status"] == "behind"
    assert "por encima" in resp.data["verdict"]["message"]


def test_users_cannot_see_others_entries(api, user):
    from apps.accounts.models import User
    from apps.tracking.models import WeightEntry

    other = User.objects.create_user(username="otro@example.com", email="otro@example.com")
    WeightEntry.objects.create(user=other, date="2026-08-19", weight_kg="99.0")
    resp = api.get("/api/tracking/weights")
    assert resp.data["count"] == 0

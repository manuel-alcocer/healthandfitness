from datetime import date, timedelta
from unittest import mock

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import User

pytestmark = pytest.mark.django_db

GOOGLE_IDINFO = {
    "sub": "google-sub-123",
    "email": "Nuevo@Example.com",
    "email_verified": True,
    "given_name": "Nuevo",
    "family_name": "Usuario",
    "picture": "https://example.com/pic.jpg",
}


def test_google_login_creates_user(settings):
    settings.GOOGLE_CLIENT_ID = "client-id"
    client = APIClient()
    with mock.patch(
        "apps.accounts.views.google_id_token.verify_oauth2_token", return_value=GOOGLE_IDINFO
    ):
        resp = client.post("/api/auth/google", {"credential": "fake"}, format="json")
    assert resp.status_code == 200
    assert resp.data["created"] is True
    assert "access" in resp.data and "refresh" in resp.data
    user = User.objects.get(email="nuevo@example.com")
    assert user.google_sub == "google-sub-123"


def test_google_login_rejects_bad_token(settings):
    settings.GOOGLE_CLIENT_ID = "client-id"
    client = APIClient()
    with mock.patch(
        "apps.accounts.views.google_id_token.verify_oauth2_token", side_effect=ValueError
    ):
        resp = client.post("/api/auth/google", {"credential": "bad"}, format="json")
    assert resp.status_code == 401


def test_google_login_unconfigured_returns_503():
    resp = APIClient().post("/api/auth/google", {"credential": "x"}, format="json")
    assert resp.status_code == 503


def test_me_reflects_onboarding_state(api):
    resp = api.get("/api/auth/me")
    assert resp.status_code == 200
    assert resp.data["profile"] is None
    assert resp.data["goal"] is None


def test_profile_create_then_goal(api):
    resp = api.put(
        "/api/auth/profile",
        {
            "sex": "M",
            "birth_date": "1978-03-10",
            "height_cm": 178,
            "initial_weight_kg": "92.00",
            "activity_level": "moderate",
            "training_days_per_week": 4,
            "preferred_activities": ["run", "gym"],
        },
        format="json",
    )
    assert resp.status_code == 201, resp.data
    assert resp.data["age"] >= 47
    assert resp.data["bmi"] > 0

    resp = api.post(
        "/api/goal",
        {"target_weight_kg": "85.00", "target_date": (date.today() + timedelta(weeks=12)).isoformat()},
        format="json",
    )
    assert resp.status_code == 201, resp.data
    assert resp.data["status"] == "pending"
    assert float(resp.data["start_weight_kg"]) == 92.0

    # A second goal while one is pending is rejected.
    resp = api.post(
        "/api/goal",
        {"target_weight_kg": "80.00", "target_date": (date.today() + timedelta(weeks=20)).isoformat()},
        format="json",
    )
    assert resp.status_code == 409


def test_goal_requires_profile(api):
    resp = api.post(
        "/api/goal",
        {"target_weight_kg": "85.00", "target_date": (date.today() + timedelta(weeks=12)).isoformat()},
        format="json",
    )
    assert resp.status_code == 400


def test_goal_rejects_next_week_deadline(api, profile):
    resp = api.post(
        "/api/goal",
        {"target_weight_kg": "70.00", "target_date": (date.today() + timedelta(days=3)).isoformat()},
        format="json",
    )
    assert resp.status_code == 400

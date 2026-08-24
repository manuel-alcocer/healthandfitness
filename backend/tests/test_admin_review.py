from datetime import date, timedelta

import pytest

from apps.goals.models import Goal
from apps.plans.models import Plan

from .conftest import make_plan_data

pytestmark = pytest.mark.django_db


def test_admin_api_requires_token(pending_goal):
    from rest_framework.test import APIClient

    resp = APIClient().get("/api/admin/users")
    assert resp.status_code == 403


def test_pending_listing(admin_api, pending_goal):
    resp = admin_api.get("/api/admin/users?status=pending")
    assert resp.status_code == 200
    assert resp.data["count"] == 1
    entry = resp.data["results"][0]
    assert entry["goal"]["status"] == "pending"
    assert entry["has_profile"] is True


def test_bundle_includes_derived_metrics(admin_api, pending_goal, user):
    resp = admin_api.get(f"/api/admin/users/{user.id}/bundle")
    assert resp.status_code == 200
    assert resp.data["derived"]["bmr_kcal"] > 1000
    assert resp.data["derived"]["tdee_kcal"] > resp.data["derived"]["bmr_kcal"]


def test_submit_realistic_plan_activates_goal(admin_api, pending_goal, user, api):
    resp = admin_api.post(
        f"/api/admin/users/{user.id}/plan",
        {"feasibility": "realistic", "message": "¡A por ello!", "plan": make_plan_data()},
        format="json",
    )
    assert resp.status_code == 200, resp.data
    goal = Goal.objects.get(pk=pending_goal.pk)
    assert goal.status == Goal.Status.ACTIVE
    assert Plan.objects.filter(goal=goal).exists()

    # The user can now fetch the plan.
    resp = api.get("/api/plan")
    assert resp.status_code == 200
    assert resp.data["data"]["daily_calories"] == 1800


def test_submit_unrealistic_plan_and_accept(admin_api, pending_goal, user, api):
    suggested_date = (date.today() + timedelta(weeks=30)).isoformat()
    resp = admin_api.post(
        f"/api/admin/users/{user.id}/plan",
        {
            "feasibility": "unrealistic",
            "message": "Perder 8 kg en 4 semanas no es sano; te propongo 30 semanas.",
            "plan": make_plan_data(weeks=30),
            "suggested_goal": {"target_weight_kg": "72.00", "target_date": suggested_date},
        },
        format="json",
    )
    assert resp.status_code == 200, resp.data
    goal = Goal.objects.get(pk=pending_goal.pk)
    assert goal.status == Goal.Status.SUGGESTED

    # Plan is hidden until the suggestion is accepted.
    assert api.get("/api/plan").status_code == 404

    resp = api.post("/api/goal/accept-suggestion")
    assert resp.status_code == 200
    goal.refresh_from_db()
    assert goal.status == Goal.Status.ACTIVE
    assert float(goal.target_weight_kg) == 72.0
    assert api.get("/api/plan").status_code == 200


def test_submit_invalid_plan_rejected(admin_api, pending_goal, user):
    bad = make_plan_data()
    del bad["weekly_weight_targets"]
    resp = admin_api.post(
        f"/api/admin/users/{user.id}/plan",
        {"feasibility": "realistic", "message": "x", "plan": bad},
        format="json",
    )
    assert resp.status_code == 400


def test_unrealistic_requires_suggestion(admin_api, pending_goal, user):
    resp = admin_api.post(
        f"/api/admin/users/{user.id}/plan",
        {"feasibility": "unrealistic", "message": "x", "plan": make_plan_data()},
        format="json",
    )
    assert resp.status_code == 400


def test_resubmit_after_suggestion(admin_api, pending_goal, user, api):
    admin_api.post(
        f"/api/admin/users/{user.id}/plan",
        {
            "feasibility": "unrealistic",
            "message": "Demasiado agresivo",
            "plan": make_plan_data(weeks=30),
            "suggested_goal": {
                "target_weight_kg": "72.00",
                "target_date": (date.today() + timedelta(weeks=30)).isoformat(),
            },
        },
        format="json",
    )
    # Instead of accepting, the user submits a softer goal -> a fresh pending goal.
    resp = api.post(
        "/api/goal",
        {"target_weight_kg": "73.00",
         "target_date": (date.today() + timedelta(weeks=26)).isoformat()},
        format="json",
    )
    assert resp.status_code == 201
    assert Goal.objects.filter(user=user, status=Goal.Status.CANCELLED).count() == 1
    assert Goal.objects.filter(user=user, status=Goal.Status.PENDING).count() == 1

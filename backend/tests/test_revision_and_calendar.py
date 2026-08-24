from datetime import date, timedelta

import pytest

from apps.goals.models import Goal
from apps.plans.models import Plan
from apps.tracking.calendar import compute_calendar

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


# --- Plan revision requests -------------------------------------------------


def test_request_revision_requires_active_goal(api, pending_goal):
    resp = api.post("/api/goal/request-revision", {"note": "quiero nadar"}, format="json")
    assert resp.status_code == 409


def test_request_revision_flow(api, admin_api, active_goal, user):
    resp = api.post(
        "/api/goal/request-revision",
        {"note": "Me he apuntado a natación, prefiero nadar en vez de caminar"},
        format="json",
    )
    assert resp.status_code == 200
    assert resp.data["revision_requested"] is True

    # The user shows up in the admin pending queue.
    listing = admin_api.get("/api/admin/users?status=pending")
    assert listing.data["count"] == 1
    assert listing.data["results"][0]["goal"]["revision_requested"] is True

    # The current plan is still visible meanwhile.
    assert api.get("/api/plan").status_code == 200

    # Submitting an updated plan clears the flag and keeps the goal active.
    resp = admin_api.post(
        f"/api/admin/users/{user.id}/plan",
        {"feasibility": "realistic", "message": "Plan actualizado con natación",
         "plan": make_plan_data()},
        format="json",
    )
    assert resp.status_code == 200, resp.data
    goal = Goal.objects.get(pk=active_goal.pk)
    assert goal.status == Goal.Status.ACTIVE
    assert goal.revision_requested is False
    assert admin_api.get("/api/admin/users?status=pending").data["count"] == 0


def test_coach_can_update_active_plan_anytime(admin_api, active_goal, user):
    resp = admin_api.post(
        f"/api/admin/users/{user.id}/plan",
        {"feasibility": "realistic", "message": "Más variedad de comidas",
         "plan": make_plan_data()},
        format="json",
    )
    assert resp.status_code == 200
    goal = Goal.objects.get(pk=active_goal.pk)
    assert goal.status == Goal.Status.ACTIVE


def test_submit_plan_rejected_for_terminal_goal(admin_api, active_goal, user):
    active_goal.status = Goal.Status.CANCELLED
    active_goal.save()
    resp = admin_api.post(
        f"/api/admin/users/{user.id}/plan",
        {"feasibility": "realistic", "message": "x", "plan": make_plan_data()},
        format="json",
    )
    assert resp.status_code == 409


# --- Meal option selection --------------------------------------------------


def test_nutrition_meal_with_option(api):
    meals = [{"name": "Comida", "status": "full", "option": "Lentejas con verduras"}]
    resp = api.post(
        "/api/tracking/nutrition", {"date": "2026-08-20", "meals": meals}, format="json"
    )
    assert resp.status_code == 201
    assert resp.data["meals"][0]["option"] == "Lentejas con verduras"


def test_nutrition_meal_bad_option_type(api):
    meals = [{"name": "Comida", "status": "full", "option": 5}]
    resp = api.post(
        "/api/tracking/nutrition", {"date": "2026-08-20", "meals": meals}, format="json"
    )
    assert resp.status_code == 400


# --- Compliance calendar ----------------------------------------------------


def full_meals(status="full"):
    return [
        {"name": "Desayuno", "status": status},
        {"name": "Comida", "status": status},
        {"name": "Cena", "status": status},
    ]


def test_calendar_levels(api, active_goal, user):
    # Fixed anchor: Wednesday 2026-09-23; Mondays 21/14 Sep are in the past
    # relative to it and inside the same month. The test plan schedules
    # walk(5km) on Monday, gym on Wednesday, walk on Friday, rest on Sunday.
    today = date(2026, 9, 23)
    monday = date(2026, 9, 21)
    plan = Plan.objects.get(goal=active_goal)
    plan.start_date = monday - timedelta(days=21)
    plan.save()

    # Monday: everything done and target met -> medal
    api.post("/api/tracking/nutrition", {"date": monday.isoformat(), "meals": full_meals()},
             format="json")
    api.post(
        "/api/tracking/activities",
        {"date": monday.isoformat(), "activity_type": "walk", "duration_min": 60,
         "distance_km": "5.0"},
        format="json",
    )

    data = compute_calendar(user, monday.year, monday.month, today=today)
    by_date = {d["date"]: d for d in data["days"]}
    assert by_date[monday.isoformat()]["level"] == "medal"
    assert data["medals"] >= 1

    # A tracked past Monday with nothing logged -> red
    prev_monday = monday - timedelta(weeks=1)
    assert by_date[prev_monday.isoformat()]["level"] == "red"

    # Future days / untracked days -> none
    future = monday + timedelta(days=40)
    if future.month == monday.month:
        assert by_date[future.isoformat()]["level"] == "none"


def test_calendar_partial_levels(api, active_goal, user):
    today = date(2026, 9, 23)
    monday = date(2026, 9, 21)
    plan = Plan.objects.get(goal=active_goal)
    plan.start_date = monday - timedelta(days=21)
    plan.save()

    # Monday: full meals but only 60% of the walk -> (1 + 0.6)/2 = 0.8 -> green
    api.post("/api/tracking/nutrition", {"date": monday.isoformat(), "meals": full_meals()},
             format="json")
    api.post(
        "/api/tracking/activities",
        {"date": monday.isoformat(), "activity_type": "walk", "duration_min": 35,
         "distance_km": "3.0"},
        format="json",
    )
    data = compute_calendar(user, monday.year, monday.month, today=today)
    by_date = {d["date"]: d for d in data["days"]}
    assert by_date[monday.isoformat()]["level"] == "green"

    # Previous Monday: only partial meals, no exercise -> (0.5 + 0)/2 -> red
    prev = monday - timedelta(weeks=1)
    api.post("/api/tracking/nutrition",
             {"date": prev.isoformat(), "meals": full_meals("partial")}, format="json")
    data = compute_calendar(user, prev.year, prev.month, today=today)
    by_date = {d["date"]: d for d in data["days"]}
    assert by_date[prev.isoformat()]["level"] == "red"

    # Two Mondays back: full meals, no exercise -> (1 + 0)/2 = 0.5 -> yellow
    prev2 = monday - timedelta(weeks=2)
    api.post("/api/tracking/nutrition",
             {"date": prev2.isoformat(), "meals": full_meals()}, format="json")
    data = compute_calendar(user, prev2.year, prev2.month, today=today)
    by_date = {d["date"]: d for d in data["days"]}
    assert by_date[prev2.isoformat()]["level"] == "yellow"


def test_calendar_rest_day_full_meals_is_medal(api, active_goal, user):
    today = date(2026, 9, 23)
    plan = Plan.objects.get(goal=active_goal)
    sunday = date(2026, 9, 20)  # rest day in the test plan
    plan.start_date = sunday - timedelta(days=14)
    plan.save()
    api.post("/api/tracking/nutrition", {"date": sunday.isoformat(), "meals": full_meals()},
             format="json")
    data = compute_calendar(user, sunday.year, sunday.month, today=today)
    by_date = {d["date"]: d for d in data["days"]}
    assert by_date[sunday.isoformat()]["level"] == "medal"


def test_calendar_endpoint(api, active_goal):
    resp = api.get("/api/calendar?month=2026-08")
    assert resp.status_code == 200
    assert resp.data["month"] == 8
    assert len(resp.data["days"]) == 31
    resp = api.get("/api/calendar?month=nonsense")
    assert resp.status_code == 200  # falls back to current month


# --- Weekly menu schema -----------------------------------------------------


def test_plan_accepts_weekly_menu(admin_api, pending_goal, user):
    plan = make_plan_data()
    daily_meals = plan["nutrition"].pop("meals")
    plan["nutrition"]["weekly_menu"] = [
        {"day": d, "meals": daily_meals} for d in range(1, 8)
    ]
    resp = admin_api.post(
        f"/api/admin/users/{user.id}/plan",
        {"feasibility": "realistic", "message": "menu semanal", "plan": plan},
        format="json",
    )
    assert resp.status_code == 200, resp.data


def test_plan_rejects_incomplete_weekly_menu(admin_api, pending_goal, user):
    plan = make_plan_data()
    daily_meals = plan["nutrition"].pop("meals")
    plan["nutrition"]["weekly_menu"] = [
        {"day": d, "meals": daily_meals} for d in range(1, 6)  # only 5 days
    ]
    resp = admin_api.post(
        f"/api/admin/users/{user.id}/plan",
        {"feasibility": "realistic", "message": "x", "plan": plan},
        format="json",
    )
    assert resp.status_code == 400

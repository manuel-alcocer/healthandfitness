from datetime import date, timedelta

import pytest

from apps.plans.models import Plan, WeeklyFeedback

from .conftest import make_plan_data

pytestmark = pytest.mark.django_db


def submit_plan(admin_api, user, **kwargs):
    resp = admin_api.post(
        f"/api/admin/users/{user.id}/plan",
        {"feasibility": "realistic", "message": "¡Vamos!", "plan": make_plan_data(**kwargs)},
        format="json",
    )
    assert resp.status_code == 200, resp.data
    return Plan.objects.get(goal__user=user)


def next_weekday(start: date, iso_weekday: int) -> date:
    day = start
    while day.isoweekday() != iso_weekday:
        day += timedelta(days=1)
    return day


# --- Materialization ------------------------------------------------------


def test_submit_plan_materializes_independent_days(admin_api, pending_goal, user):
    plan = submit_plan(admin_api, user, weeks=4)
    days = list(plan.days.all())
    # One day per date, from start to the last weight-target date.
    assert len(days) == 4 * 7 + 1
    assert days[0].date == plan.start_date

    # Each day carries a copy of its template weekday.
    monday = next_weekday(plan.start_date, 1)
    monday_day = plan.days.get(date=monday)
    assert monday_day.session["type"] == "walk"
    assert "day" not in monday_day.session
    assert [m["name"] for m in monday_day.meals] == ["Desayuno", "Comida", "Cena"]

    # A weekday without a schedule entry becomes rest.
    tuesday_day = plan.days.get(date=next_weekday(plan.start_date, 2))
    assert tuesday_day.session["type"] == "rest"


def test_editing_one_day_does_not_touch_other_weeks(admin_api, pending_goal, user):
    """The regression the redesign is about: days are NOT a weekly cycle."""
    plan = submit_plan(admin_api, user, weeks=4)
    monday1 = next_weekday(plan.start_date, 1)
    monday2 = monday1 + timedelta(weeks=1)

    resp = admin_api.patch(
        f"/api/admin/users/{user.id}/plan/days/{monday1.isoformat()}",
        {
            "session": {"type": "swim", "title": "Piscina", "target": {"duration_min": 30}},
            "meals": [{"name": "Desayuno", "options": ["Tortilla francesa"]}],
        },
        format="json",
    )
    assert resp.status_code == 200, resp.data

    edited = plan.days.get(date=monday1)
    untouched = plan.days.get(date=monday2)
    assert edited.session["type"] == "swim"
    assert edited.meals[0]["options"] == ["Tortilla francesa"]
    # Same template weekday, one week later: completely unaffected.
    assert untouched.session["type"] == "walk"
    assert untouched.meals[0]["options"] == ["Avena con fruta"]


def test_day_patch_validation(admin_api, pending_goal, user):
    plan = submit_plan(admin_api, user)
    day = plan.start_date.isoformat()
    url = f"/api/admin/users/{user.id}/plan/days/{day}"
    assert admin_api.patch(url, {}, format="json").status_code == 400
    assert (
        admin_api.patch(url, {"session": {"type": "yoga"}}, format="json").status_code == 400
    )
    assert admin_api.patch(url, {"meals": []}, format="json").status_code == 400


def test_resubmission_keeps_past_days(admin_api, pending_goal, user):
    plan = submit_plan(admin_api, user, weeks=4)
    # Pretend the plan started a week ago so there are past days.
    plan.start_date = date.today() - timedelta(days=7)
    plan.save()
    from apps.plans.materialize import materialize_days

    materialize_days(plan)
    past = plan.days.get(date=date.today() - timedelta(days=3))
    past.session = {"type": "hike", "title": "Ruta especial"}
    past.save()

    # Resubmitting (e.g. a revision) regenerates today and the future only,
    # and keeps the original start_date so calendar history stays tracked.
    submit_plan(admin_api, user, weeks=4)
    plan.refresh_from_db()
    assert plan.start_date == date.today() - timedelta(days=7)
    assert plan.days.get(date=date.today() - timedelta(days=3)).session["type"] == "hike"
    assert plan.days.filter(date__gte=date.today()).exists()


# --- User-facing day endpoints --------------------------------------------


def test_plan_days_endpoint_returns_materialized_days(admin_api, pending_goal, user, api):
    plan = submit_plan(admin_api, user, weeks=4)
    start = plan.start_date.isoformat()
    end = (plan.start_date + timedelta(days=6)).isoformat()
    resp = api.get(f"/api/plan/days?from={start}&to={end}")
    assert resp.status_code == 200
    assert resp.data["count"] == 7
    assert all(d["source"] == "day" for d in resp.data["results"])

    # Outside the materialized range the weekly template answers (legacy
    # behavior), flagged as such.
    far = (plan.start_date + timedelta(weeks=52)).isoformat()
    resp = api.get(f"/api/plan/days?from={far}")
    assert resp.status_code == 200
    assert resp.data["results"][0]["source"] == "template"


def test_plan_days_endpoint_requires_plan_and_valid_range(api, user):
    assert api.get("/api/plan/days?from=2026-01-01").status_code == 404


def test_plan_days_range_validation(admin_api, pending_goal, user, api):
    submit_plan(admin_api, user)
    assert api.get("/api/plan/days").status_code == 400
    assert api.get("/api/plan/days?from=2026-01-01&to=2026-03-15").status_code == 400


def test_calendar_uses_the_edited_day_not_the_template(admin_api, pending_goal, user, api):
    plan = submit_plan(admin_api, user, weeks=4)
    # Move "today" onto a template walk day and turn it into rest.
    plan.start_date = date.today() - timedelta(days=8)
    plan.save()
    from apps.plans.materialize import materialize_days

    materialize_days(plan)
    monday = next_weekday(plan.start_date, 1)
    day = plan.days.get(date=monday)
    day.session = {"type": "rest", "title": "Descanso"}
    day.save()

    resp = api.get(f"/api/calendar?month={monday.strftime('%Y-%m')}")
    assert resp.status_code == 200
    info = next(d for d in resp.data["days"] if d["date"] == monday.isoformat())
    # A rest day has no planned session, so nothing is "planned" for it even
    # though the weekly template says walk.
    assert info["planned"] is None


# --- Weekly feedback ------------------------------------------------------


def monday_of_last_week() -> date:
    today = date.today()
    return today - timedelta(days=today.weekday(), weeks=1)


def test_feedback_publish_and_list(admin_api, user, api):
    week = monday_of_last_week()
    payload = {
        "week_start": week.isoformat(),
        "summary": "Gran semana: 6 días de actividad y menú clavado.",
        "stats": {"distance_km": 42.0, "nutrition_adherence": 1.0},
        "adjustments": ["Caminata del domingo reducida a 6,5 km"],
    }
    resp = admin_api.put(f"/api/admin/users/{user.id}/feedback", payload, format="json")
    assert resp.status_code == 200, resp.data
    assert resp.data["created"] is True

    # Idempotent upsert per week.
    payload["summary"] = "Gran semana (editado)."
    resp = admin_api.put(f"/api/admin/users/{user.id}/feedback", payload, format="json")
    assert resp.data["created"] is False
    assert WeeklyFeedback.objects.filter(user=user).count() == 1

    resp = api.get("/api/feedback")
    assert resp.status_code == 200
    assert resp.data["count"] == 1
    entry = resp.data["results"][0]
    assert entry["week_start"] == week.isoformat()
    assert entry["summary"].startswith("Gran semana")
    assert entry["stats"]["distance_km"] == 42.0
    assert entry["adjustments"] == ["Caminata del domingo reducida a 6,5 km"]


def test_feedback_validation(admin_api, user):
    url = f"/api/admin/users/{user.id}/feedback"
    not_monday = (monday_of_last_week() + timedelta(days=2)).isoformat()
    assert (
        admin_api.put(url, {"week_start": not_monday, "summary": "x"}, format="json").status_code
        == 400
    )
    assert (
        admin_api.put(
            url, {"week_start": monday_of_last_week().isoformat()}, format="json"
        ).status_code
        == 400
    )


def test_feedback_requires_auth(user):
    from rest_framework.test import APIClient

    assert APIClient().get("/api/feedback").status_code == 401

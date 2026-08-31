"""Progress and compliance engine.

Compares the user's logged data against the plan document (expected weekly
weight curve + weekly exercise schedule + meals) and produces everything the
dashboard needs: chart series, weekly compliance and an on-track verdict.
"""

from datetime import date, timedelta
from decimal import Decimal

from apps.goals.models import Goal
from apps.plans.models import Plan, PlanDay

from .models import ActivityEntry, NutritionEntry, WeightEntry

# The weight trend is judged against the expected curve with this tolerance.
ON_TRACK_TOLERANCE_KG = 0.6


def _parse_date(value: str) -> date:
    return date.fromisoformat(value)


def expected_weight_at(targets: list[dict], on: date) -> float | None:
    """Linear interpolation over the plan's weekly weight targets."""
    if not targets:
        return None
    points = sorted(
        ((_parse_date(t["date"]), float(t["weight_kg"])) for t in targets), key=lambda p: p[0]
    )
    if on <= points[0][0]:
        return points[0][1]
    if on >= points[-1][0]:
        return points[-1][1]
    for (d0, w0), (d1, w1) in zip(points, points[1:], strict=False):
        if d0 <= on <= d1:
            span = (d1 - d0).days or 1
            frac = (on - d0).days / span
            return round(w0 + (w1 - w0) * frac, 2)
    return points[-1][1]


def smoothed_current_weight(user, today: date) -> float | None:
    """Mean of the weigh-ins in the last 7 days; falls back to the latest one."""
    recent = list(
        WeightEntry.objects.filter(user=user, date__gt=today - timedelta(days=7), date__lte=today)
    )
    if recent:
        return round(sum(float(e.weight_kg) for e in recent) / len(recent), 2)
    latest = WeightEntry.objects.filter(user=user, date__lte=today).order_by("-date").first()
    return float(latest.weight_kg) if latest else None


def _week_bounds(today: date) -> tuple[date, date]:
    monday = today - timedelta(days=today.weekday())
    return monday, monday + timedelta(days=6)


def _streak(user, today: date) -> int:
    """Consecutive days ending today (or yesterday) with at least one log."""
    logged_dates = set()
    for model in (WeightEntry, ActivityEntry, NutritionEntry):
        logged_dates.update(
            model.objects.filter(
                user=user, date__gte=today - timedelta(days=120), date__lte=today
            ).values_list("date", flat=True)
        )
    streak = 0
    day = today if today in logged_dates else today - timedelta(days=1)
    while day in logged_dates:
        streak += 1
        day -= timedelta(days=1)
    return streak


def compute_progress(user, today: date | None = None) -> dict:
    today = today or date.today()
    goal = (
        Goal.objects.filter(user=user, status=Goal.Status.ACTIVE).order_by("-created_at").first()
    )
    if not goal:
        return {"state": "no_active_goal"}
    plan = Plan.objects.filter(goal=goal).first()

    weights = list(
        WeightEntry.objects.filter(user=user, date__gte=goal.start_date).order_by("date")
    )
    weight_series = [
        {"date": e.date.isoformat(), "weight_kg": float(e.weight_kg)} for e in weights
    ]

    result: dict = {
        "state": "active",
        "goal": {
            "start_weight_kg": float(goal.start_weight_kg),
            "target_weight_kg": float(goal.target_weight_kg),
            "start_date": goal.start_date.isoformat(),
            "target_date": goal.target_date.isoformat(),
        },
        "weight_series": weight_series,
        "streak_days": _streak(user, today),
    }

    plan_data = plan.data if plan else {}
    targets = plan_data.get("weekly_weight_targets", [])
    result["expected_series"] = [
        {"date": t["date"], "weight_kg": float(t["weight_kg"])} for t in targets
    ]

    # --- Weight verdict ---------------------------------------------------
    current = smoothed_current_weight(user, today)
    expected = expected_weight_at(targets, today)
    losing = float(goal.target_weight_kg) < float(goal.start_weight_kg)
    if current is None:
        weight_status = "no_data"
        delta = None
    elif expected is None:
        weight_status = "no_plan"
        delta = None
    else:
        delta = round(current - expected, 2)
        # For a loss goal, being below the curve is good; for a gain goal the
        # sign flips.
        signed = delta if losing else -delta
        if signed <= ON_TRACK_TOLERANCE_KG:
            weight_status = "ahead" if signed < -ON_TRACK_TOLERANCE_KG else "on_track"
        else:
            weight_status = "behind"
    result["weight"] = {
        "current_kg": current,
        "expected_today_kg": expected,
        "delta_kg": delta,
        "status": weight_status,
        "lost_kg": (
            round(float(goal.start_weight_kg) - current, 2) if current is not None else None
        ),
        "to_go_kg": (
            round(current - float(goal.target_weight_kg), 2) if current is not None else None
        ),
    }

    # --- This week's exercise compliance ---------------------------------
    monday, sunday = _week_bounds(today)
    # This week's own materialized days when the plan has them; the weekly
    # template is only the legacy fallback.
    week_days = (
        list(PlanDay.objects.filter(plan=plan, date__gte=monday, date__lte=sunday))
        if plan
        else []
    )
    if week_days:
        planned_sessions = [d.session for d in week_days if d.session.get("type") != "rest"]
    else:
        schedule = (plan_data.get("exercise") or {}).get("weekly_schedule", [])
        planned_sessions = [s for s in schedule if s.get("type") != "rest"]
    planned_distance = sum(
        float((s.get("target") or {}).get("distance_km") or 0) for s in planned_sessions
    )
    week_acts = list(ActivityEntry.objects.filter(user=user, date__gte=monday, date__lte=sunday))
    done_distance = sum(float(a.distance_km or 0) for a in week_acts)
    done_minutes = sum(a.duration_min for a in week_acts)
    sessions_planned = len(planned_sessions)
    sessions_done = len(week_acts)
    result["exercise_week"] = {
        "week_start": monday.isoformat(),
        "sessions_planned": sessions_planned,
        "sessions_done": sessions_done,
        "distance_planned_km": round(planned_distance, 1),
        "distance_done_km": round(done_distance, 1),
        "minutes_done": done_minutes,
        "compliance": (
            round(min(1.0, sessions_done / sessions_planned), 2) if sessions_planned else None
        ),
    }

    # --- This week's nutrition compliance --------------------------------
    week_nut = list(NutritionEntry.objects.filter(user=user, date__gte=monday, date__lte=sunday))
    scores = [e.adherence for e in week_nut if e.adherence is not None]
    result["nutrition_week"] = {
        "days_logged": len(week_nut),
        "adherence": round(sum(scores) / len(scores), 2) if scores else None,
    }

    # --- Overall verdict + message ---------------------------------------
    result["verdict"] = _verdict(result, losing)
    return result


def _verdict(result: dict, losing: bool) -> dict:
    """Compose an overall status plus a human message in Spanish.

    UI copy is Spanish by product decision; the codebase stays English.
    """
    weight = result["weight"]
    exercise = result["exercise_week"]
    nutrition = result["nutrition_week"]

    parts: list[str] = []
    scores: list[float] = []

    if weight["status"] == "on_track":
        parts.append("Tu peso va según lo previsto.")
        scores.append(1.0)
    elif weight["status"] == "ahead":
        parts.append("¡Vas por delante de lo previsto con el peso!")
        scores.append(1.0)
    elif weight["status"] == "behind":
        extra = "por encima" if losing else "por debajo"
        parts.append(f"Tu peso va {abs(weight['delta_kg'])} kg {extra} de lo previsto.")
        scores.append(0.0)
    else:
        parts.append("Registra tu peso para ver tu evolución.")

    comp = exercise["compliance"]
    if comp is not None:
        if comp >= 0.85:
            parts.append("Estás cumpliendo el plan de ejercicio de esta semana.")
            scores.append(1.0)
        elif comp >= 0.5:
            done, planned = exercise["sessions_done"], exercise["sessions_planned"]
            parts.append(f"Llevas {done} de {planned} sesiones de ejercicio esta semana.")
            scores.append(0.5)
        else:
            parts.append("Esta semana vas retrasado con el ejercicio.")
            scores.append(0.0)

    adherence = nutrition["adherence"]
    if adherence is not None:
        if adherence >= 0.8:
            parts.append("La alimentación la llevas muy bien.")
            scores.append(1.0)
        elif adherence >= 0.5:
            parts.append("La alimentación puede mejorar: revisa las comidas del plan.")
            scores.append(0.5)
        else:
            parts.append("Estás lejos del plan de alimentación esta semana.")
            scores.append(0.0)
    elif nutrition["days_logged"] == 0:
        parts.append("No has registrado comidas esta semana.")

    if not scores:
        status = "no_data"
    else:
        avg = sum(scores) / len(scores)
        status = "on_track" if avg >= 0.75 else "at_risk" if avg >= 0.4 else "off_track"

    return {"status": status, "message": " ".join(parts)}


def weekly_summary(user, weeks: int = 12, today: date | None = None) -> list[dict]:
    """Per-week aggregates for the evolution charts (exercise volume)."""
    today = today or date.today()
    monday_this, _ = _week_bounds(today)
    out = []
    for i in range(weeks - 1, -1, -1):
        monday = monday_this - timedelta(weeks=i)
        sunday = monday + timedelta(days=6)
        acts = ActivityEntry.objects.filter(user=user, date__gte=monday, date__lte=sunday)
        distance = sum(float(a.distance_km or 0) for a in acts)
        minutes = sum(a.duration_min for a in acts)
        out.append(
            {
                "week_start": monday.isoformat(),
                "sessions": acts.count(),
                "distance_km": round(distance, 1),
                "minutes": minutes,
            }
        )
    return out


def to_float(value: Decimal | None) -> float | None:
    return float(value) if value is not None else None

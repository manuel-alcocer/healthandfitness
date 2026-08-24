"""Daily-compliance calendar.

Scores each day of the plan against what was stipulated and buckets it:
  red    — nothing or very little done      (score < 0.5)
  yellow — part of the day fulfilled        (0.5 <= score < 0.8)
  green  — almost everything fulfilled      (0.8 <= score < 1)
  medal  — everything done, or more         (score >= 1: full meals adherence
           and the planned session met or exceeded its target)

Components per day:
  - nutrition (every day): the entry's adherence, 0 if nothing logged
  - exercise (only days with a non-rest planned session): fulfillment ratio
    against the session's distance target (or duration if no distance);
    logging any activity on a rest day adds a small bonus ("o más")
"""

from datetime import date, timedelta

from apps.goals.models import Goal
from apps.plans.models import Plan

from .models import ActivityEntry, NutritionEntry


def _session_for(schedule: list[dict], on: date) -> dict | None:
    weekday = on.isoweekday()  # 1=Monday .. 7=Sunday, same convention as the plan
    for session in schedule:
        if session.get("day") == weekday:
            return session
    return None


def _exercise_ratio(session: dict, acts: list[ActivityEntry]) -> float:
    """How much of the planned session was fulfilled (uncapped, can be > 1)."""
    if not acts:
        return 0.0
    target = session.get("target") or {}
    if target.get("distance_km"):
        done = sum(float(a.distance_km or 0) for a in acts)
        return done / float(target["distance_km"])
    if target.get("duration_min"):
        done = sum(a.duration_min for a in acts)
        return done / float(target["duration_min"])
    return 1.0


def _level(score: float) -> str:
    if score >= 1.0:
        return "medal"
    if score >= 0.8:
        return "green"
    if score >= 0.5:
        return "yellow"
    return "red"


def compute_calendar(user, year: int, month: int, today: date | None = None) -> dict:
    today = today or date.today()
    goal = (
        Goal.objects.filter(user=user, status=Goal.Status.ACTIVE).order_by("-created_at").first()
    )
    plan = Plan.objects.filter(goal=goal).first() if goal else None
    schedule = (plan.data.get("exercise") or {}).get("weekly_schedule", []) if plan else []

    first = date(year, month, 1)
    last = (first.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
    tracked_from = plan.start_date if plan else None

    acts_by_day: dict[date, list[ActivityEntry]] = {}
    for act in ActivityEntry.objects.filter(user=user, date__gte=first, date__lte=last):
        acts_by_day.setdefault(act.date, []).append(act)
    nutrition_by_day = {
        e.date: e
        for e in NutritionEntry.objects.filter(user=user, date__gte=first, date__lte=last)
    }

    days = []
    day = first
    while day <= last:
        info: dict = {"date": day.isoformat(), "level": "none"}
        if tracked_from and tracked_from <= day <= today:
            session = _session_for(schedule, day)
            planned_exercise = bool(session and session.get("type") != "rest")
            acts = acts_by_day.get(day, [])

            entry = nutrition_by_day.get(day)
            adherence = entry.adherence if entry and entry.adherence is not None else 0.0
            components = [adherence]

            ratio = None
            if planned_exercise:
                ratio = _exercise_ratio(session, acts)
                components.append(min(ratio, 1.0))

            score = sum(components) / len(components)
            # score can only reach ~1.0 when meals adherence is full AND the
            # planned session met (or exceeded) its target — that is the medal.
            if score >= 0.999:
                score = 1.0

            info.update(
                {
                    "level": _level(score),
                    "score": round(min(score, 1.0), 2),
                    "nutrition_adherence": round(adherence, 2) if entry else None,
                    "planned": (session or {}).get("title") if planned_exercise else None,
                    "exercise_ratio": round(ratio, 2) if ratio is not None else None,
                    "activities": len(acts),
                }
            )
        days.append(info)
        day += timedelta(days=1)

    medals = sum(1 for d in days if d["level"] == "medal")
    return {
        "year": year,
        "month": month,
        "today": today.isoformat(),
        "tracked_from": tracked_from.isoformat() if tracked_from else None,
        "medals": medals,
        "days": days,
    }

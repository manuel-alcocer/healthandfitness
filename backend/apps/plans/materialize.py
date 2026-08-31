"""Materialize a plan's weekly template into independent per-date days.

The plan document carries a weekly menu and a weekly exercise schedule; those
are only the seed. Each calendar date of the plan gets its own `PlanDay` row,
so a date can be edited without touching any other — two Mondays sharing the
same dishes is a coincidence of the seed, not a link.
"""

from datetime import date, timedelta

from .models import Plan, PlanDay

REST_SESSION = {"type": "rest", "title": "Descanso"}


def template_for_date(data: dict, on: date) -> tuple[list, dict]:
    """The (meals, session) the plan's weekly template stipulates for a date."""
    weekday = on.isoweekday()  # 1=Monday .. 7=Sunday, the plan's convention
    nutrition = data.get("nutrition") or {}
    menu = nutrition.get("weekly_menu")
    if menu:
        meals = next((e.get("meals") or [] for e in menu if e.get("day") == weekday), [])
    else:
        meals = nutrition.get("meals") or []

    schedule = (data.get("exercise") or {}).get("weekly_schedule") or []
    session = next((s for s in schedule if s.get("day") == weekday), None)
    if session is None:
        session = dict(REST_SESSION)
    else:
        session = {k: v for k, v in session.items() if k != "day"}
    return meals, session


def plan_end_date(plan: Plan) -> date:
    """Last date the plan covers: the final point of its weight curve."""
    targets = plan.data.get("weekly_weight_targets") or []
    dates = [date.fromisoformat(t["date"]) for t in targets if t.get("date")]
    return max(dates) if dates else plan.start_date

def materialize_days(plan: Plan, from_date: date | None = None) -> int:
    """(Re)generate the plan's per-date days from its weekly template.

    Days before `from_date` are left untouched — they are history and may
    hold what was actually planned at the time. Days from `from_date` on are
    replaced with fresh copies of the template. Returns the number of days
    written.
    """
    start = plan.start_date
    if from_date and from_date > start:
        start = from_date
    end = plan_end_date(plan)
    if end < start:
        return 0

    plan.days.filter(date__gte=start).delete()
    rows = []
    day = start
    while day <= end:
        meals, session = template_for_date(plan.data, day)
        rows.append(PlanDay(plan=plan, date=day, meals=meals, session=session))
        day += timedelta(days=1)
    PlanDay.objects.bulk_create(rows)
    return len(rows)

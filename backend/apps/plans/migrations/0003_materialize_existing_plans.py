"""Materialize existing plans into per-date PlanDay rows.

Plans predating this migration only had the weekly template; seed one
independent day per date from plan start to the end of the weight curve, so
per-day edits become possible without the template acting as a shared slot.
"""

from datetime import date, timedelta

from django.db import migrations

REST_SESSION = {"type": "rest", "title": "Descanso"}


def _template_for_date(data, on):
    weekday = on.isoweekday()
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


def materialize(apps, schema_editor):
    Plan = apps.get_model("plans", "Plan")
    PlanDay = apps.get_model("plans", "PlanDay")
    for plan in Plan.objects.all():
        targets = plan.data.get("weekly_weight_targets") or []
        dates = [date.fromisoformat(t["date"]) for t in targets if t.get("date")]
        end = max(dates) if dates else plan.start_date
        rows = []
        day = plan.start_date
        while day <= end:
            meals, session = _template_for_date(plan.data, day)
            rows.append(PlanDay(plan=plan, date=day, meals=meals, session=session))
            day += timedelta(days=1)
        PlanDay.objects.bulk_create(rows)


def unmaterialize(apps, schema_editor):
    apps.get_model("plans", "PlanDay").objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [
        ("plans", "0002_planday_weeklyfeedback"),
    ]

    operations = [
        migrations.RunPython(materialize, unmaterialize),
    ]

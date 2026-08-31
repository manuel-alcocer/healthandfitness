from datetime import date, timedelta

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.goals.models import Goal

from .materialize import template_for_date
from .models import Plan, PlanDay, WeeklyFeedback

MAX_DAYS_RANGE = 31


def active_plan_for(user) -> Plan | None:
    goal = (
        Goal.objects.filter(user=user, status=Goal.Status.ACTIVE)
        .order_by("-created_at")
        .first()
    )
    return Plan.objects.filter(goal=goal).first() if goal else None


def day_payload(plan: Plan, on: date, days_by_date: dict[date, PlanDay]) -> dict:
    """One date's meals + session: the materialized day, or the weekly
    template as fallback for dates outside the materialized range (and for
    legacy plans submitted before per-day materialization existed)."""
    day = days_by_date.get(on)
    if day:
        return {"date": on.isoformat(), "meals": day.meals, "session": day.session,
                "source": "day"}
    meals, session = template_for_date(plan.data, on)
    return {"date": on.isoformat(), "meals": meals, "session": session,
            "source": "template"}


class PlanView(APIView):
    """Return the caller's plan.

    An `active` goal exposes its plan; a `suggested` goal keeps the plan
    hidden until the user accepts the alternative (only the summary of the
    suggestion travels in the goal itself).
    """

    def get(self, request):
        plan = active_plan_for(request.user)
        if not plan:
            return Response({"detail": "No plan yet"}, status=status.HTTP_404_NOT_FOUND)
        return Response(
            {
                "id": plan.id,
                "goal_id": plan.goal_id,
                "start_date": plan.start_date,
                "created_at": plan.created_at,
                "data": plan.data,
            }
        )


class PlanDaysView(APIView):
    """The caller's concrete plan days for a date range (max 31 days).

    Each day is independent: what this returns for a date is that date's own
    content, not a slot of a repeating weekly template.
    """

    def get(self, request):
        plan = active_plan_for(request.user)
        if not plan:
            return Response({"detail": "No plan yet"}, status=status.HTTP_404_NOT_FOUND)
        try:
            start = date.fromisoformat(request.query_params["from"])
            end = date.fromisoformat(request.query_params.get("to", start.isoformat()))
        except (KeyError, ValueError):
            return Response(
                {"detail": "from/to must be YYYY-MM-DD"}, status=status.HTTP_400_BAD_REQUEST
            )
        if end < start or (end - start).days >= MAX_DAYS_RANGE:
            return Response(
                {"detail": f"range must be 1..{MAX_DAYS_RANGE} days"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        days_by_date = {d.date: d for d in plan.days.filter(date__gte=start, date__lte=end)}
        results = []
        day = start
        while day <= end:
            results.append(day_payload(plan, day, days_by_date))
            day += timedelta(days=1)
        return Response({"count": len(results), "results": results})


class WeeklyFeedbackListView(APIView):
    """The coach's weekly reviews for the caller, newest first."""

    def get(self, request):
        results = [
            {
                "id": fb.id,
                "week_start": fb.week_start.isoformat(),
                "summary": fb.summary,
                "stats": fb.stats,
                "adjustments": fb.adjustments,
                "created_at": fb.created_at,
                "updated_at": fb.updated_at,
            }
            for fb in WeeklyFeedback.objects.filter(user=request.user)[:26]
        ]
        return Response({"count": len(results), "results": results})

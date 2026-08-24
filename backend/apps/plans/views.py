from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.goals.models import Goal

from .models import Plan


class PlanView(APIView):
    """Return the caller's plan.

    An `active` goal exposes its plan; a `suggested` goal keeps the plan
    hidden until the user accepts the alternative (only the summary of the
    suggestion travels in the goal itself).
    """

    def get(self, request):
        goal = (
            Goal.objects.filter(user=request.user, status=Goal.Status.ACTIVE)
            .order_by("-created_at")
            .first()
        )
        plan = Plan.objects.filter(goal=goal).first() if goal else None
        if not plan:
            return Response({"detail": "No plan yet"}, status=status.HTTP_404_NOT_FOUND)
        return Response(
            {
                "id": plan.id,
                "goal_id": goal.id,
                "start_date": plan.start_date,
                "created_at": plan.created_at,
                "data": plan.data,
            }
        )

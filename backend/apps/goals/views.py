from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import Profile

from .models import Goal
from .serializers import GoalSerializer


class GoalView(APIView):
    """Submit or resubmit a goal; view the current one."""

    def get(self, request):
        goal = Goal.objects.filter(user=request.user).first()
        if not goal:
            return Response({"detail": "No goal yet"}, status=status.HTTP_404_NOT_FOUND)
        return Response(GoalSerializer(goal).data)

    def post(self, request):
        profile = Profile.objects.filter(user=request.user).first()
        if not profile:
            return Response(
                {"detail": "Completa primero tus datos biométricos"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        current = Goal.objects.filter(user=request.user).first()
        if current and current.status in (Goal.Status.PENDING, Goal.Status.ACTIVE):
            return Response(
                {"detail": "Ya tienes un objetivo en curso"},
                status=status.HTTP_409_CONFLICT,
            )
        serializer = GoalSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        # A resubmission after a suggestion supersedes the suggested goal.
        if current and current.status == Goal.Status.SUGGESTED:
            current.status = Goal.Status.CANCELLED
            current.save(update_fields=["status", "updated_at"])
        goal = serializer.save(user=request.user, start_weight_kg=profile.initial_weight_kg)
        return Response(GoalSerializer(goal).data, status=status.HTTP_201_CREATED)


class RequestRevisionView(APIView):
    """Ask the coach for an updated plan (e.g. after changing preferred
    activities in the profile). The current plan stays active meanwhile."""

    def post(self, request):
        goal = Goal.objects.filter(user=request.user, status=Goal.Status.ACTIVE).first()
        if not goal:
            return Response(
                {"detail": "Necesitas un plan activo para pedir una revisión"},
                status=status.HTTP_409_CONFLICT,
            )
        goal.revision_requested = True
        goal.revision_note = str(request.data.get("note", ""))[:2000]
        goal.save(update_fields=["revision_requested", "revision_note", "updated_at"])
        return Response(GoalSerializer(goal).data)


class AcceptSuggestionView(APIView):
    """Accept the admin's alternative goal after an unrealistic request."""

    def post(self, request):
        goal = Goal.objects.filter(user=request.user, status=Goal.Status.SUGGESTED).first()
        if not goal:
            return Response(
                {"detail": "No hay ninguna propuesta pendiente"},
                status=status.HTTP_404_NOT_FOUND,
            )
        goal.accept_suggestion()
        return Response(GoalSerializer(goal).data)

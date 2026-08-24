from datetime import date

from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import Profile, User
from apps.accounts.serializers import ProfileSerializer, UserSerializer
from apps.goals.models import Goal
from apps.goals.serializers import GoalSerializer
from apps.plans.models import Plan
from apps.plans.schema import PlanValidationError, validate_plan_data
from apps.tracking.progress import compute_progress, weekly_summary
from apps.tracking.serializers import (
    ActivityEntrySerializer,
    NutritionEntrySerializer,
    WeightEntrySerializer,
)

from .permissions import HasAdminToken


class AdminView(APIView):
    authentication_classes = []
    permission_classes = [HasAdminToken]


class UserListView(AdminView):
    """List users, optionally filtered by their latest goal's status."""

    def get(self, request):
        wanted = request.query_params.get("status")
        out = []
        for user in User.objects.all().order_by("date_joined"):
            goal = user.goals.first()
            if wanted and not goal:
                continue
            # "pending" is the review queue: fresh goals AND active goals whose
            # user asked for a plan revision.
            if wanted == "pending":
                awaiting = goal.status == "pending" or goal.revision_requested
                if not awaiting:
                    continue
            elif wanted and goal.status != wanted:
                continue
            profile = Profile.objects.filter(user=user).first()
            out.append(
                {
                    "user": UserSerializer(user).data,
                    "has_profile": profile is not None,
                    "goal": GoalSerializer(goal).data if goal else None,
                }
            )
        return Response({"count": len(out), "results": out})


class UserBundleView(AdminView):
    """Everything about one user: the input for plan generation."""

    def get(self, request, user_id):
        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return Response({"detail": "Unknown user"}, status=status.HTTP_404_NOT_FOUND)
        profile = Profile.objects.filter(user=user).first()
        goal = user.goals.first()
        bundle = {
            "user": UserSerializer(user).data,
            "profile": ProfileSerializer(profile).data if profile else None,
            "goal": GoalSerializer(goal).data if goal else None,
            "derived": None,
            "recent_weights": WeightEntrySerializer(
                user.weight_entries.all()[:30], many=True
            ).data,
            "recent_activities": ActivityEntrySerializer(
                user.activity_entries.all()[:30], many=True
            ).data,
            "recent_nutrition": NutritionEntrySerializer(
                user.nutrition_entries.all()[:14], many=True
            ).data,
        }
        if profile:
            bundle["derived"] = {
                "age": profile.age,
                "bmi": profile.bmi,
                "bmr_kcal": profile.bmr(),
                "tdee_kcal": profile.tdee(),
            }
        return Response(bundle)


class SubmitPlanView(AdminView):
    """Attach the generated plan (or an alternative suggestion) to a goal.

    Body:
      feasibility: "realistic" | "unrealistic"
      message: text shown to the user (Spanish)
      plan: plan document (docs/PLAN_SCHEMA.md)
      suggested_goal: {target_weight_kg, target_date}  (required if unrealistic;
        the plan must be built for this suggested goal)
    """

    def post(self, request, user_id):
        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return Response({"detail": "Unknown user"}, status=status.HTTP_404_NOT_FOUND)
        goal = user.goals.first()
        # The coach can (re)submit a plan for any live goal: fresh reviews,
        # suggestion re-reviews, user-requested revisions AND proactive
        # updates of an active plan. Only terminal goals are off-limits.
        if not goal or goal.status in (Goal.Status.COMPLETED, Goal.Status.CANCELLED):
            return Response(
                {"detail": "User has no live goal to attach a plan to"},
                status=status.HTTP_409_CONFLICT,
            )

        feasibility = request.data.get("feasibility")
        message = request.data.get("message", "")
        plan_data = request.data.get("plan")
        if feasibility not in ("realistic", "unrealistic"):
            return Response(
                {"detail": "feasibility must be realistic|unrealistic"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            validate_plan_data(plan_data)
        except (PlanValidationError, ValueError, TypeError, KeyError) as exc:
            return Response(
                {"detail": f"Invalid plan document: {exc}"}, status=status.HTTP_400_BAD_REQUEST
            )

        goal.admin_message = message
        goal.reviewed_at = timezone.now()
        goal.revision_requested = False
        if feasibility == "realistic":
            goal.status = Goal.Status.ACTIVE
            goal.suggested_target_weight_kg = None
            goal.suggested_target_date = None
        else:
            suggestion = request.data.get("suggested_goal") or {}
            try:
                goal.suggested_target_weight_kg = suggestion["target_weight_kg"]
                goal.suggested_target_date = date.fromisoformat(suggestion["target_date"])
            except (KeyError, ValueError, TypeError):
                return Response(
                    {"detail": "unrealistic submissions need suggested_goal"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            goal.status = Goal.Status.SUGGESTED
        goal.save()

        Plan.objects.update_or_create(
            goal=goal, defaults={"data": plan_data, "start_date": date.today()}
        )
        return Response({"detail": "ok", "goal": GoalSerializer(goal).data})


class UserProgressView(AdminView):
    """Same progress payload the user sees, for follow-up reviews."""

    def get(self, request, user_id):
        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return Response({"detail": "Unknown user"}, status=status.HTTP_404_NOT_FOUND)
        data = compute_progress(user)
        data["weekly_exercise"] = weekly_summary(user)
        return Response(data)

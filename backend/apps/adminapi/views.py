from datetime import date

from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import Profile, User
from apps.accounts.serializers import ProfileSerializer, UserSerializer
from apps.goals.models import Goal
from apps.goals.serializers import GoalSerializer
from apps.plans.materialize import materialize_days
from apps.plans.models import Plan, PlanDay, WeeklyFeedback
from apps.plans.schema import PlanValidationError, validate_day_patch, validate_plan_data
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

        # A replacement keeps the original start_date: tracking (calendar
        # history, materialized past days) began then, not at the revision.
        plan, created = Plan.objects.update_or_create(
            goal=goal,
            defaults={"data": plan_data},
            create_defaults={"data": plan_data, "start_date": date.today()},
        )
        # Fresh plan: materialize every date. Replacement (revision/update):
        # regenerate from today on, keeping past days as they were planned.
        days = materialize_days(plan, from_date=None if created else date.today())
        return Response(
            {"detail": "ok", "days_materialized": days, "goal": GoalSerializer(goal).data}
        )


def _live_plan(user) -> Plan | None:
    goal = user.goals.first()
    if not goal or goal.status in (Goal.Status.COMPLETED, Goal.Status.CANCELLED):
        return None
    return Plan.objects.filter(goal=goal).first()


class PlanDaysAdminView(AdminView):
    """List a user's materialized plan days (optionally a date range)."""

    def get(self, request, user_id):
        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return Response({"detail": "Unknown user"}, status=status.HTTP_404_NOT_FOUND)
        plan = _live_plan(user)
        if not plan:
            return Response({"detail": "User has no plan"}, status=status.HTTP_404_NOT_FOUND)
        days = plan.days.all()
        try:
            if request.query_params.get("from"):
                days = days.filter(date__gte=date.fromisoformat(request.query_params["from"]))
            if request.query_params.get("to"):
                days = days.filter(date__lte=date.fromisoformat(request.query_params["to"]))
        except ValueError:
            return Response(
                {"detail": "from/to must be YYYY-MM-DD"}, status=status.HTTP_400_BAD_REQUEST
            )
        results = [
            {"date": d.date.isoformat(), "meals": d.meals, "session": d.session}
            for d in days
        ]
        return Response({"count": len(results), "results": results})


class PlanDayAdminView(AdminView):
    """Edit ONE date of a user's plan: meals and/or session.

    Only that date changes — days are independent, never a weekly slot.
    """

    def patch(self, request, user_id, day):
        try:
            user = User.objects.get(pk=user_id)
            on = date.fromisoformat(day)
        except User.DoesNotExist:
            return Response({"detail": "Unknown user"}, status=status.HTTP_404_NOT_FOUND)
        except ValueError:
            return Response(
                {"detail": "date must be YYYY-MM-DD"}, status=status.HTTP_400_BAD_REQUEST
            )
        plan = _live_plan(user)
        if not plan:
            return Response({"detail": "User has no plan"}, status=status.HTTP_404_NOT_FOUND)
        try:
            validate_day_patch(request.data)
        except (PlanValidationError, ValueError, TypeError, KeyError) as exc:
            return Response(
                {"detail": f"Invalid day patch: {exc}"}, status=status.HTTP_400_BAD_REQUEST
            )
        defaults = {}
        if "meals" in request.data:
            defaults["meals"] = request.data["meals"]
        if "session" in request.data:
            defaults["session"] = request.data["session"]
        plan_day, _ = PlanDay.objects.update_or_create(
            plan=plan, date=on, defaults=defaults
        )
        return Response(
            {
                "detail": "ok",
                "day": {
                    "date": plan_day.date.isoformat(),
                    "meals": plan_day.meals,
                    "session": plan_day.session,
                },
            }
        )


class WeeklyFeedbackAdminView(AdminView):
    """Publish (or update) the coach's weekly review for a user.

    Body: week_start (Monday, YYYY-MM-DD), summary (Spanish text),
    stats (object, optional), adjustments (list of strings, optional).
    """

    def get(self, request, user_id):
        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return Response({"detail": "Unknown user"}, status=status.HTTP_404_NOT_FOUND)
        results = [
            {
                "week_start": fb.week_start.isoformat(),
                "summary": fb.summary,
                "stats": fb.stats,
                "adjustments": fb.adjustments,
                "updated_at": fb.updated_at,
            }
            for fb in WeeklyFeedback.objects.filter(user=user)[:26]
        ]
        return Response({"count": len(results), "results": results})

    def put(self, request, user_id):
        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return Response({"detail": "Unknown user"}, status=status.HTTP_404_NOT_FOUND)
        summary = request.data.get("summary")
        try:
            week_start = date.fromisoformat(request.data.get("week_start", ""))
        except ValueError:
            return Response(
                {"detail": "week_start must be YYYY-MM-DD"}, status=status.HTTP_400_BAD_REQUEST
            )
        if week_start.isoweekday() != 1:
            return Response(
                {"detail": "week_start must be a Monday"}, status=status.HTTP_400_BAD_REQUEST
            )
        if not summary or not isinstance(summary, str):
            return Response(
                {"detail": "summary is required"}, status=status.HTTP_400_BAD_REQUEST
            )
        stats = request.data.get("stats") or {}
        adjustments = request.data.get("adjustments") or []
        if not isinstance(stats, dict) or not isinstance(adjustments, list):
            return Response(
                {"detail": "stats must be an object and adjustments a list"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        fb, created = WeeklyFeedback.objects.update_or_create(
            user=user,
            week_start=week_start,
            defaults={"summary": summary, "stats": stats, "adjustments": adjustments},
        )
        return Response(
            {"detail": "ok", "created": created, "week_start": fb.week_start.isoformat()}
        )


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

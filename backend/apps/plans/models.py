from django.conf import settings
from django.db import models

from apps.goals.models import Goal


class Plan(models.Model):
    """The nutrition + exercise plan generated for a goal.

    `data` holds the full plan document (see docs/PLAN_SCHEMA.md): daily
    calories, macros, meals, weekly exercise schedule and the expected weekly
    weight curve the dashboard compares real weigh-ins against.

    The weekly menu/schedule in `data` is only the SEED: on submission it is
    materialized into independent `PlanDay` rows, one per calendar date.
    """

    goal = models.OneToOneField(Goal, on_delete=models.CASCADE, related_name="plan")
    data = models.JSONField()
    start_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Plan<{self.goal.user.email}>"


class PlanDay(models.Model):
    """One concrete date of a plan: that day's meals and exercise session.

    Seeded from the plan's weekly template but independent afterwards:
    editing one date never affects any other date, even if both happen to
    carry the same content because they started from the same template
    weekday.
    """

    plan = models.ForeignKey(Plan, on_delete=models.CASCADE, related_name="days")
    date = models.DateField()
    # [{"name": "Desayuno", "time": "08:00", "options": ["...", "..."]}]
    meals = models.JSONField(default=list)
    # {"type": "run", "title": "...", "target": {...}, "details": "..."}
    session = models.JSONField(default=dict)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["plan", "date"], name="unique_plan_day")
        ]
        ordering = ["date"]

    def __str__(self):
        return f"PlanDay<{self.plan.goal.user.email} {self.date}>"


class WeeklyFeedback(models.Model):
    """The coach's weekly review for a user: summary, stats and adjustments.

    One entry per user per week (Monday-keyed); resubmitting a week updates
    it. Shown to the user in the app's "Entrenador" area.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="weekly_feedback"
    )
    week_start = models.DateField()  # Monday of the reviewed week
    summary = models.TextField()  # coach's text (Spanish), paragraphs separated by \n\n
    # Snapshot of the week's numbers, e.g. {"weight_start_kg": 102.0, ...}
    stats = models.JSONField(default=dict, blank=True)
    # Human-readable list of plan changes applied with this review.
    adjustments = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "week_start"], name="unique_feedback_per_week"
            )
        ]
        ordering = ["-week_start"]

    def __str__(self):
        return f"WeeklyFeedback<{self.user.email} {self.week_start}>"

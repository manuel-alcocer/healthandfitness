from django.db import models

from apps.goals.models import Goal


class Plan(models.Model):
    """The nutrition + exercise plan generated for a goal.

    `data` holds the full plan document (see docs/PLAN_SCHEMA.md): daily
    calories, macros, meals, weekly exercise schedule and the expected weekly
    weight curve the dashboard compares real weigh-ins against.
    """

    goal = models.OneToOneField(Goal, on_delete=models.CASCADE, related_name="plan")
    data = models.JSONField()
    start_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Plan<{self.goal.user.email}>"

from django.conf import settings
from django.db import models


class Goal(models.Model):
    """A weight target with a deadline, reviewed by the admin.

    Lifecycle:
      pending   -> user submitted it, waiting for the admin review
      active    -> admin attached a plan (goal was realistic)
      suggested -> admin judged it unrealistic and proposed an alternative
                   (suggested_* fields + admin_message + a plan built for the
                   suggestion); accepting moves the suggestion into the main
                   fields and the goal becomes active
      completed / cancelled -> terminal states
    """

    class Status(models.TextChoices):
        PENDING = "pending", "Pendiente de revisión"
        ACTIVE = "active", "Activo"
        SUGGESTED = "suggested", "Alternativa propuesta"
        COMPLETED = "completed", "Completado"
        CANCELLED = "cancelled", "Cancelado"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="goals"
    )
    target_weight_kg = models.DecimalField(max_digits=5, decimal_places=2)
    target_date = models.DateField()
    motivation = models.TextField(blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)

    # Review outcome (set through the admin API)
    admin_message = models.TextField(blank=True)
    suggested_target_weight_kg = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )
    suggested_target_date = models.DateField(null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    # Weight at the moment the goal was submitted (copied from the profile so
    # progress is measured against a fixed starting point).
    start_weight_kg = models.DecimalField(max_digits=5, decimal_places=2)
    start_date = models.DateField(auto_now_add=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Goal<{self.user.email} -> {self.target_weight_kg}kg by {self.target_date}>"

    def accept_suggestion(self):
        """Adopt the admin's alternative goal and activate it."""
        if self.status != self.Status.SUGGESTED:
            raise ValueError("No suggestion to accept")
        self.target_weight_kg = self.suggested_target_weight_kg
        self.target_date = self.suggested_target_date
        self.status = self.Status.ACTIVE
        self.save()

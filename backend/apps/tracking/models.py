from django.conf import settings
from django.db import models


class WeightEntry(models.Model):
    """A weigh-in. One per day at most; resubmitting a date updates it."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="weight_entries"
    )
    date = models.DateField()
    weight_kg = models.DecimalField(max_digits=5, decimal_places=2)
    body_fat_pct = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    notes = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "date"], name="unique_weight_per_day")
        ]
        ordering = ["-date"]

    def __str__(self):
        return f"{self.user.email} {self.date}: {self.weight_kg}kg"


class ActivityEntry(models.Model):
    """A logged exercise session with its measured metrics."""

    class ActivityType(models.TextChoices):
        WALK = "walk", "Andar"
        RUN = "run", "Correr"
        SWIM = "swim", "Nadar"
        BIKE = "bike", "Bicicleta"
        GYM = "gym", "Gimnasio"
        HIKE = "hike", "Senderismo"
        OTHER = "other", "Otro"

    class Source(models.TextChoices):
        MANUAL = "manual", "Manual"
        STRAVA = "strava", "Strava"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="activity_entries"
    )
    date = models.DateField()
    activity_type = models.CharField(max_length=10, choices=ActivityType.choices)
    title = models.CharField(max_length=100, blank=True)
    duration_min = models.PositiveSmallIntegerField()
    distance_km = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    avg_hr = models.PositiveSmallIntegerField(null=True, blank=True)
    max_hr = models.PositiveSmallIntegerField(null=True, blank=True)
    avg_speed_kmh = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    elevation_m = models.PositiveSmallIntegerField(null=True, blank=True)
    calories = models.PositiveSmallIntegerField(null=True, blank=True)
    perceived_effort = models.PositiveSmallIntegerField(null=True, blank=True)  # RPE 1-10
    # Index of the plan's weekly_schedule session this fulfils, if any.
    plan_day = models.PositiveSmallIntegerField(null=True, blank=True)
    notes = models.CharField(max_length=300, blank=True)
    source = models.CharField(max_length=10, choices=Source.choices, default=Source.MANUAL)
    # Provider-side activity id (e.g. Strava's), used to deduplicate imports.
    external_id = models.CharField(max_length=40, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "external_id"],
                condition=~models.Q(external_id=""),
                name="unique_external_activity_per_user",
            )
        ]

    def __str__(self):
        return f"{self.user.email} {self.date}: {self.activity_type} {self.duration_min}min"


class NutritionEntry(models.Model):
    """Daily meal adherence against the plan. One entry per day."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="nutrition_entries"
    )
    date = models.DateField()
    # [{"name": "Desayuno", "status": "full" | "partial" | "skipped"}, ...]
    meals = models.JSONField(default=list)
    calories_estimate = models.PositiveSmallIntegerField(null=True, blank=True)
    water_l = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True)
    notes = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "date"], name="unique_nutrition_per_day")
        ]
        ordering = ["-date"]

    def __str__(self):
        return f"{self.user.email} {self.date}: nutrition"

    @property
    def adherence(self) -> float | None:
        """0..1 score for the day: full=1, partial=0.5, skipped=0."""
        if not self.meals:
            return None
        score = {"full": 1.0, "partial": 0.5, "skipped": 0.0}
        vals = [score.get(m.get("status"), 0.0) for m in self.meals]
        return round(sum(vals) / len(vals), 2)

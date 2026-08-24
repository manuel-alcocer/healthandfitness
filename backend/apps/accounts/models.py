from datetime import date

from django.contrib.auth.models import AbstractUser, UserManager
from django.db import models


class EmailUserManager(UserManager):
    """Let `create_user`/`create_superuser` work with email as the key field."""

    def _create_user_object(self, username, email, password, **extra_fields):
        if not email:
            raise ValueError("An email address is required")
        username = username or email
        return super()._create_user_object(username, email, password, **extra_fields)


class User(AbstractUser):
    """Application user; normally created on first Google sign-in."""

    email = models.EmailField(unique=True)
    google_sub = models.CharField(max_length=64, unique=True, null=True, blank=True)
    avatar_url = models.URLField(blank=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = EmailUserManager()

    def __str__(self):
        return self.email


class Profile(models.Model):
    """Biometric and lifestyle data the plan generation is based on."""

    class Sex(models.TextChoices):
        MALE = "M", "Hombre"
        FEMALE = "F", "Mujer"

    class ActivityLevel(models.TextChoices):
        SEDENTARY = "sedentary", "Sedentario"
        LIGHT = "light", "Ligero (1-2 días/semana)"
        MODERATE = "moderate", "Moderado (3-4 días/semana)"
        ACTIVE = "active", "Activo (5-6 días/semana)"
        VERY_ACTIVE = "very_active", "Muy activo (diario intenso)"

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    sex = models.CharField(max_length=1, choices=Sex.choices)
    birth_date = models.DateField()
    height_cm = models.PositiveSmallIntegerField()
    initial_weight_kg = models.DecimalField(max_digits=5, decimal_places=2)
    activity_level = models.CharField(
        max_length=20, choices=ActivityLevel.choices, default=ActivityLevel.SEDENTARY
    )
    resting_hr = models.PositiveSmallIntegerField(null=True, blank=True)
    body_fat_pct = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    waist_cm = models.PositiveSmallIntegerField(null=True, blank=True)
    hip_cm = models.PositiveSmallIntegerField(null=True, blank=True)
    health_conditions = models.TextField(blank=True)
    dietary_preferences = models.TextField(blank=True)
    training_days_per_week = models.PositiveSmallIntegerField(default=3)
    preferred_activities = models.JSONField(default=list, blank=True)
    equipment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Profile<{self.user.email}>"

    @property
    def age(self) -> int:
        today = date.today()
        born = self.birth_date
        return today.year - born.year - ((today.month, today.day) < (born.month, born.day))

    @property
    def bmi(self) -> float:
        h = self.height_cm / 100
        return round(float(self.initial_weight_kg) / (h * h), 1)

    def bmr(self, weight_kg: float | None = None) -> int:
        """Mifflin-St Jeor basal metabolic rate."""
        w = float(weight_kg if weight_kg is not None else self.initial_weight_kg)
        base = 10 * w + 6.25 * self.height_cm - 5 * self.age
        return round(base + (5 if self.sex == self.Sex.MALE else -161))

    ACTIVITY_FACTORS = {
        "sedentary": 1.2,
        "light": 1.375,
        "moderate": 1.55,
        "active": 1.725,
        "very_active": 1.9,
    }

    def tdee(self, weight_kg: float | None = None) -> int:
        """Total daily energy expenditure estimate."""
        return round(self.bmr(weight_kg) * self.ACTIVITY_FACTORS[self.activity_level])

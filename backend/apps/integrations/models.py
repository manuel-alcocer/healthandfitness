from django.conf import settings
from django.db import models


class GoogleHealthAccount(models.Model):
    """OAuth link between a user and their Google Health data (scale weigh-ins)."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="google_health_account"
    )
    access_token = models.TextField()
    refresh_token = models.TextField()
    # Unix epoch when the access token expires.
    token_expires_at = models.BigIntegerField()
    last_sync_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.email} ↔ Google Health"


class StravaAccount(models.Model):
    """OAuth link between a user and their Strava athlete profile."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="strava_account"
    )
    athlete_id = models.BigIntegerField(unique=True)
    athlete_name = models.CharField(max_length=120, blank=True)
    access_token = models.CharField(max_length=128)
    refresh_token = models.CharField(max_length=128)
    # Unix epoch, exactly as Strava reports token expiry.
    token_expires_at = models.BigIntegerField()
    last_sync_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.email} ↔ Strava athlete {self.athlete_id}"

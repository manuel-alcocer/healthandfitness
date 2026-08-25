"""Turn Strava activities into ActivityEntry rows, deduplicated by external id."""

import time
from datetime import timedelta

from django.utils import timezone

from apps.tracking.models import ActivityEntry

from . import strava
from .models import StravaAccount

# First connection pulls this far back; later syncs re-check a small overlap
# window so activities uploaded late (watch synced days after) still land.
FIRST_SYNC_DAYS = 60
RESYNC_OVERLAP_DAYS = 7

TOKEN_REFRESH_MARGIN_S = 300

# Strava sport_type -> our ActivityType. Anything unknown maps to "other".
SPORT_TYPE_MAP = {
    "Walk": ActivityEntry.ActivityType.WALK,
    "Run": ActivityEntry.ActivityType.RUN,
    "TrailRun": ActivityEntry.ActivityType.RUN,
    "VirtualRun": ActivityEntry.ActivityType.RUN,
    "Ride": ActivityEntry.ActivityType.BIKE,
    "VirtualRide": ActivityEntry.ActivityType.BIKE,
    "MountainBikeRide": ActivityEntry.ActivityType.BIKE,
    "GravelRide": ActivityEntry.ActivityType.BIKE,
    "EBikeRide": ActivityEntry.ActivityType.BIKE,
    "Swim": ActivityEntry.ActivityType.SWIM,
    "Hike": ActivityEntry.ActivityType.HIKE,
    "Snowshoe": ActivityEntry.ActivityType.HIKE,
    "WeightTraining": ActivityEntry.ActivityType.GYM,
    "Workout": ActivityEntry.ActivityType.GYM,
    "Crossfit": ActivityEntry.ActivityType.GYM,
    "HighIntensityIntervalTraining": ActivityEntry.ActivityType.GYM,
    "Elliptical": ActivityEntry.ActivityType.GYM,
    "StairStepper": ActivityEntry.ActivityType.GYM,
    "Rowing": ActivityEntry.ActivityType.GYM,
}


def get_valid_access_token(account: StravaAccount) -> str:
    if account.token_expires_at - time.time() > TOKEN_REFRESH_MARGIN_S:
        return account.access_token
    data = strava.refresh_tokens(account.refresh_token)
    account.access_token = data["access_token"]
    account.refresh_token = data.get("refresh_token", account.refresh_token)
    account.token_expires_at = data["expires_at"]
    account.save(update_fields=["access_token", "refresh_token", "token_expires_at"])
    return account.access_token


def map_activity(raw: dict) -> dict | None:
    """Field mapping for one Strava activity; None when not worth importing."""
    moving_s = raw.get("moving_time") or 0
    start_local = raw.get("start_date_local") or ""
    if raw.get("id") is None or moving_s < 60 or len(start_local) < 10:
        return None
    sport = raw.get("sport_type") or raw.get("type") or ""
    distance_m = raw.get("distance") or 0
    speed_ms = raw.get("average_speed") or 0

    def whole(value):
        return round(value) if value else None

    return {
        "external_id": str(raw["id"]),
        "date": start_local[:10],
        "activity_type": SPORT_TYPE_MAP.get(sport, ActivityEntry.ActivityType.OTHER),
        "title": (raw.get("name") or "")[:100],
        "duration_min": max(1, round(moving_s / 60)),
        "distance_km": round(distance_m / 1000, 2) if distance_m else None,
        "avg_hr": whole(raw.get("average_heartrate")),
        "max_hr": whole(raw.get("max_heartrate")),
        "avg_speed_kmh": round(speed_ms * 3.6, 2) if speed_ms else None,
        "elevation_m": whole(raw.get("total_elevation_gain")),
        "calories": whole(raw.get("calories")),
    }


def import_activities(account: StravaAccount) -> int:
    """Fetch new Strava activities for the account and store them. Returns count."""
    if account.last_sync_at:
        after = account.last_sync_at - timedelta(days=RESYNC_OVERLAP_DAYS)
    else:
        after = timezone.now() - timedelta(days=FIRST_SYNC_DAYS)

    token = get_valid_access_token(account)
    fetched = strava.fetch_activities(token, int(after.timestamp()))

    existing = set(
        ActivityEntry.objects.filter(
            user=account.user, source=ActivityEntry.Source.STRAVA
        ).values_list("external_id", flat=True)
    )
    created = 0
    for raw in fetched:
        fields = map_activity(raw)
        if fields is None or fields["external_id"] in existing:
            continue
        ActivityEntry.objects.create(
            user=account.user, source=ActivityEntry.Source.STRAVA, **fields
        )
        existing.add(fields["external_id"])
        created += 1

    account.last_sync_at = timezone.now()
    account.save(update_fields=["last_sync_at"])
    return created

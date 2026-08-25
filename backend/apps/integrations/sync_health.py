"""Turn Google Health weight data points into daily WeightEntry rows.

One entry per day: the morning weigh-in wins (fasted readings are the only
ones comparable day to day) — specifically the earliest reading inside the
03:00-14:00 local window, falling back to the earliest of the day when
nothing was measured in the morning (so a post-midnight weigh-in, which
lands on the next civil day, never displaces a real morning reading).
Hand-entered values are never overwritten.
"""

import time
from datetime import timedelta

from django.utils import timezone

from apps.tracking.models import WeightEntry

from . import google_health
from .models import GoogleHealthAccount

FIRST_SYNC_DAYS = 90
RESYNC_OVERLAP_DAYS = 7

TOKEN_REFRESH_MARGIN_S = 300

# Guard against scale glitches (a boot, luggage, a pet on the scale...).
MIN_WEIGHT_KG = 30
MAX_WEIGHT_KG = 300

# Local-hour window whose readings take precedence for the day.
MORNING_START_H = 3
MORNING_END_H = 14


def get_valid_access_token(account: GoogleHealthAccount) -> str:
    if account.token_expires_at - time.time() > TOKEN_REFRESH_MARGIN_S:
        return account.access_token
    try:
        data = google_health.refresh_tokens(account.refresh_token)
    except google_health.TokenRevokedError:
        # Testing-status consent screens expire refresh tokens after 7 days.
        account.needs_reauth = True
        account.save(update_fields=["needs_reauth"])
        raise
    account.access_token = data["access_token"]
    account.token_expires_at = int(time.time()) + int(data.get("expires_in", 3600))
    if account.needs_reauth:
        account.needs_reauth = False
        account.save(update_fields=["access_token", "token_expires_at", "needs_reauth"])
    else:
        account.save(update_fields=["access_token", "token_expires_at"])
    return account.access_token


def _point_date_and_time(point: dict) -> tuple[str, str, int] | None:
    """(local date, physical instant, local hour) of a data point, or None.

    civilTime arrives as a structured object ({"date": {"year", "month",
    "day"}, "time": {...}}) in practice, although the docs also show string
    forms — accept both, falling back to the physical instant.
    """
    weight = point.get("weight") or {}
    sample = weight.get("sampleTime") or {}
    physical = sample.get("physicalTime") or ""
    if len(physical) < 10:
        return None
    day = physical[:10]
    hour = int(physical[11:13]) if len(physical) >= 13 else 0
    civil = sample.get("civilTime")
    if isinstance(civil, dict):
        date_part = civil.get("date") or {}
        try:
            day = (
                f"{int(date_part['year']):04d}"
                f"-{int(date_part['month']):02d}"
                f"-{int(date_part['day']):02d}"
            )
        except (KeyError, TypeError, ValueError):
            pass
        try:
            hour = int((civil.get("time") or {}).get("hours", hour))
        except (TypeError, ValueError):
            pass
    elif isinstance(civil, str) and len(civil) >= 10:
        day = civil[:10]
        if len(civil) >= 13:
            try:
                hour = int(civil[11:13])
            except ValueError:
                pass
    return day, physical, hour


def daily_weights(points: list[dict]) -> dict[str, float]:
    """The day's weigh-in per local date, in kg: earliest morning reading
    (03:00-14:00 local), or the earliest of the day if none."""
    by_day: dict[str, list[tuple[str, int, float]]] = {}
    for point in points:
        when = _point_date_and_time(point)
        grams = (point.get("weight") or {}).get("weightGrams")
        if when is None or not grams:
            continue
        kg = round(float(grams) / 1000, 2)
        if not (MIN_WEIGHT_KG <= kg <= MAX_WEIGHT_KG):
            continue
        day, instant, hour = when
        by_day.setdefault(day, []).append((instant, hour, kg))

    result: dict[str, float] = {}
    for day, readings in by_day.items():
        morning = [r for r in readings if MORNING_START_H <= r[1] < MORNING_END_H]
        _, _, kg = min(morning or readings)
        result[day] = kg
    return result


def import_weights(account: GoogleHealthAccount) -> int:
    """Fetch weigh-ins from Google Health and upsert daily entries. Returns count."""
    if account.last_sync_at:
        after = account.last_sync_at - timedelta(days=RESYNC_OVERLAP_DAYS)
    else:
        after = timezone.now() - timedelta(days=FIRST_SYNC_DAYS)

    token = get_valid_access_token(account)
    points = google_health.fetch_weight_points(
        token, after.strftime("%Y-%m-%dT%H:%M:%SZ")
    )

    changed = 0
    for day, kg in daily_weights(points).items():
        existing = WeightEntry.objects.filter(user=account.user, date=day).first()
        if existing is None:
            WeightEntry.objects.create(
                user=account.user,
                date=day,
                weight_kg=kg,
                source=WeightEntry.Source.GOOGLE_HEALTH,
            )
            changed += 1
        elif existing.source == WeightEntry.Source.GOOGLE_HEALTH and float(
            existing.weight_kg
        ) != kg:
            existing.weight_kg = kg
            existing.save(update_fields=["weight_kg"])
            changed += 1
        # Manual entries win: never touched.

    account.last_sync_at = timezone.now()
    account.save(update_fields=["last_sync_at"])
    return changed

from datetime import datetime, timedelta

import pytest
from django.core import signing
from django.utils import timezone

from apps.integrations import sync_health
from apps.integrations import views as integ_views
from apps.integrations.models import GoogleHealthAccount
from apps.tracking.models import WeightEntry


@pytest.fixture
def gh_settings(settings):
    settings.GOOGLE_CLIENT_ID = "google-client-id"
    settings.GOOGLE_CLIENT_SECRET = "google-client-secret"
    settings.PUBLIC_BASE_URL = "https://hnf.example.net"
    return settings


@pytest.fixture
def account(user):
    return GoogleHealthAccount.objects.create(
        user=user,
        access_token="tok",
        refresh_token="ref",
        token_expires_at=int((timezone.now() + timedelta(hours=1)).timestamp()),
    )


def weight_point(grams, physical, civil=None):
    """Mimics the real API shape: civilTime is a structured object."""
    if civil is None:
        civil = {
            "date": {
                "year": int(physical[0:4]),
                "month": int(physical[5:7]),
                "day": int(physical[8:10]),
            }
        }
    return {
        "dataSource": {"platform": "HEALTH_CONNECT"},
        "weight": {
            "weightGrams": grams,
            "sampleTime": {"physicalTime": physical, "civilTime": civil},
        },
    }


def test_status_disabled_without_secret(api, settings):
    settings.GOOGLE_CLIENT_ID = "google-client-id"
    settings.GOOGLE_CLIENT_SECRET = ""
    resp = api.get("/api/integrations/google-health")
    assert resp.data == {"enabled": False, "connected": False}


def test_status_offers_auth_url(api, gh_settings):
    resp = api.get("/api/integrations/google-health")
    assert resp.data["enabled"] is True and resp.data["connected"] is False
    url = resp.data["auth_url"]
    assert url.startswith("https://accounts.google.com/o/oauth2/v2/auth?")
    assert "googlehealth.health_metrics_and_measurements.readonly" in url
    assert "access_type=offline" in url and "prompt=consent" in url
    assert "google-health%2Fcallback" in url


def test_callback_creates_account(client, user, gh_settings, monkeypatch):
    monkeypatch.setattr(
        integ_views.google_health,
        "exchange_code",
        lambda code, redirect_uri: {
            "access_token": "new-access",
            "refresh_token": "new-refresh",
            "expires_in": 3600,
        },
    )
    state = signing.TimestampSigner(salt=integ_views.GH_STATE_SALT).sign(str(user.pk))
    resp = client.get(f"/api/integrations/google-health/callback?code=abc&state={state}")
    assert resp.status_code == 302
    assert resp.url == "/perfil?salud=conectado"
    account = GoogleHealthAccount.objects.get(user=user)
    assert account.refresh_token == "new-refresh"


def test_callback_rejects_grant_without_refresh_token(client, user, gh_settings, monkeypatch):
    monkeypatch.setattr(
        integ_views.google_health,
        "exchange_code",
        lambda code, redirect_uri: {"access_token": "a", "expires_in": 3600},
    )
    state = signing.TimestampSigner(salt=integ_views.GH_STATE_SALT).sign(str(user.pk))
    resp = client.get(f"/api/integrations/google-health/callback?code=abc&state={state}")
    assert resp.url == "/perfil?salud=error"
    assert GoogleHealthAccount.objects.count() == 0


def test_sync_imports_earliest_daily_weight(api, gh_settings, account, monkeypatch):
    points = [
        weight_point(101250, "2026-08-24T06:10:00Z"),
        weight_point(101900, "2026-08-24T21:30:00Z"),  # later same day: ignored
        weight_point(100800, "2026-08-25T06:05:00Z"),
        weight_point(950, "2026-08-25T09:00:00Z"),  # 0.95 kg glitch: ignored
    ]
    monkeypatch.setattr(
        sync_health.google_health, "fetch_weight_points", lambda token, after: points
    )
    resp = api.post("/api/integrations/google-health/sync")
    assert resp.status_code == 200
    assert resp.data["imported"] == 2

    day24 = WeightEntry.objects.get(user=account.user, date="2026-08-24")
    assert float(day24.weight_kg) == 101.25
    assert day24.source == "google_health"
    assert float(WeightEntry.objects.get(user=account.user, date="2026-08-25").weight_kg) == 100.8

    # Second run with the same data changes nothing.
    resp = api.post("/api/integrations/google-health/sync")
    assert resp.data["imported"] == 0


def test_sync_never_overwrites_manual_entry(api, gh_settings, account, monkeypatch):
    WeightEntry.objects.create(
        user=account.user, date="2026-08-24", weight_kg="99.90", source="manual"
    )
    monkeypatch.setattr(
        sync_health.google_health,
        "fetch_weight_points",
        lambda token, after: [weight_point(101250, "2026-08-24T06:10:00Z")],
    )
    resp = api.post("/api/integrations/google-health/sync")
    assert resp.data["imported"] == 0
    assert float(WeightEntry.objects.get(user=account.user, date="2026-08-24").weight_kg) == 99.9


def test_sync_updates_prior_import(api, gh_settings, account, monkeypatch):
    WeightEntry.objects.create(
        user=account.user, date="2026-08-24", weight_kg="101.90", source="google_health"
    )
    monkeypatch.setattr(
        sync_health.google_health,
        "fetch_weight_points",
        lambda token, after: [weight_point(101250, "2026-08-24T06:10:00Z")],
    )
    resp = api.post("/api/integrations/google-health/sync")
    assert resp.data["imported"] == 1
    assert float(WeightEntry.objects.get(user=account.user, date="2026-08-24").weight_kg) == 101.25


def test_sync_refreshes_expired_token(api, gh_settings, account, monkeypatch):
    account.token_expires_at = int(datetime(2020, 1, 1).timestamp())
    account.save()
    monkeypatch.setattr(
        sync_health.google_health,
        "refresh_tokens",
        lambda rt: {"access_token": "fresh", "expires_in": 3600},
    )
    monkeypatch.setattr(
        sync_health.google_health, "fetch_weight_points", lambda token, after: []
    )
    resp = api.post("/api/integrations/google-health/sync")
    assert resp.status_code == 200
    account.refresh_from_db()
    assert account.access_token == "fresh"


def test_manual_weight_entry_flips_source(api, gh_settings, account):
    WeightEntry.objects.create(
        user=account.user, date="2026-08-24", weight_kg="101.25", source="google_health"
    )
    resp = api.post(
        "/api/tracking/weights", {"date": "2026-08-24", "weight_kg": "100.50"}, format="json"
    )
    assert resp.status_code == 200
    entry = WeightEntry.objects.get(user=account.user, date="2026-08-24")
    assert entry.source == "manual"
    assert float(entry.weight_kg) == 100.5


def test_expired_refresh_token_flags_reauth(api, gh_settings, account, monkeypatch):
    account.token_expires_at = int(datetime(2020, 1, 1).timestamp())
    account.save()

    def dead(rt):
        raise sync_health.google_health.TokenRevokedError("expired")

    monkeypatch.setattr(sync_health.google_health, "refresh_tokens", dead)
    resp = api.post("/api/integrations/google-health/sync")
    assert resp.status_code == 409
    account.refresh_from_db()
    assert account.needs_reauth is True

    # Status now offers a reconnect URL while still reporting the link.
    status_resp = api.get("/api/integrations/google-health")
    assert status_resp.data["connected"] is True
    assert status_resp.data["needs_reauth"] is True
    assert "auth_url" in status_resp.data


def test_reconnect_clears_reauth_flag(client, user, gh_settings, account, monkeypatch):
    account.needs_reauth = True
    account.save()
    monkeypatch.setattr(
        integ_views.google_health,
        "exchange_code",
        lambda code, redirect_uri: {
            "access_token": "again",
            "refresh_token": "again-ref",
            "expires_in": 3600,
        },
    )
    state = signing.TimestampSigner(salt=integ_views.GH_STATE_SALT).sign(str(user.pk))
    resp = client.get(f"/api/integrations/google-health/callback?code=abc&state={state}")
    assert resp.url == "/perfil?salud=conectado"
    account.refresh_from_db()
    assert account.needs_reauth is False
    assert account.refresh_token == "again-ref"


def test_disconnect(api, gh_settings, account, monkeypatch):
    monkeypatch.setattr(integ_views.google_health, "revoke", lambda token: None)
    resp = api.delete("/api/integrations/google-health")
    assert resp.status_code == 204
    assert GoogleHealthAccount.objects.count() == 0


def test_daily_weights_accepts_civil_time_variants():
    # Structured civilTime crossing midnight UTC: civil date (25th) wins
    # over the physical instant's date (24th).
    late = weight_point(
        101000,
        "2026-08-24T22:30:00Z",
        civil={"date": {"year": 2026, "month": 8, "day": 25}},
    )
    # String civilTime (documented form) and missing civilTime also work.
    string_form = weight_point(102000, "2026-08-23T06:00:00Z", civil="2026-08-23T08:00:00")
    bare = {
        "weight": {"weightGrams": 103000, "sampleTime": {"physicalTime": "2026-08-22T07:00:00Z"}}
    }
    days = sync_health.daily_weights([late, string_form, bare])
    assert days == {"2026-08-25": 101.0, "2026-08-23": 102.0, "2026-08-22": 103.0}

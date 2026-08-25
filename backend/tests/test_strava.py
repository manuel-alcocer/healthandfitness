from datetime import datetime, timedelta

import pytest
from django.core import signing
from django.utils import timezone

from apps.integrations import sync as strava_sync
from apps.integrations import views as strava_views
from apps.integrations.models import StravaAccount
from apps.tracking.models import ActivityEntry


@pytest.fixture
def strava_settings(settings):
    settings.STRAVA_CLIENT_ID = "12345"
    settings.STRAVA_CLIENT_SECRET = "test-secret"
    settings.PUBLIC_BASE_URL = "https://hnf.example.net"
    return settings


@pytest.fixture
def account(user):
    return StravaAccount.objects.create(
        user=user,
        athlete_id=777,
        athlete_name="Ana Atleta",
        access_token="tok",
        refresh_token="ref",
        token_expires_at=int((timezone.now() + timedelta(hours=2)).timestamp()),
    )


def strava_activity(**overrides):
    base = {
        "id": 1111,
        "sport_type": "Walk",
        "name": "Paseo por el parque",
        "start_date_local": "2026-08-24T18:30:00Z",
        "moving_time": 3600,
        "distance": 5200.0,
        "average_heartrate": 112.4,
        "max_heartrate": 131.0,
        "average_speed": 1.44,
        "total_elevation_gain": 42.0,
    }
    base.update(overrides)
    return base


def test_status_disabled_without_credentials(api):
    resp = api.get("/api/integrations/strava")
    assert resp.status_code == 200
    assert resp.data == {"enabled": False, "connected": False}


def test_status_offers_auth_url_when_not_connected(api, strava_settings):
    resp = api.get("/api/integrations/strava")
    assert resp.status_code == 200
    assert resp.data["enabled"] is True
    assert resp.data["connected"] is False
    url = resp.data["auth_url"]
    assert url.startswith("https://www.strava.com/oauth/authorize?")
    assert "client_id=12345" in url
    assert "hnf.example.net" in url
    assert "state=" in url


def test_status_when_connected(api, strava_settings, account):
    resp = api.get("/api/integrations/strava")
    assert resp.data["connected"] is True
    assert resp.data["athlete_name"] == "Ana Atleta"
    assert "auth_url" not in resp.data


def test_callback_creates_account(client, user, strava_settings, monkeypatch):
    monkeypatch.setattr(
        strava_views.strava,
        "exchange_code",
        lambda code: {
            "access_token": "new-access",
            "refresh_token": "new-refresh",
            "expires_at": 1900000000,
            "athlete": {"id": 424242, "firstname": "Ana", "lastname": "Atleta"},
        },
    )
    state = signing.TimestampSigner(salt=strava_views.STATE_SALT).sign(str(user.pk))
    resp = client.get(f"/api/integrations/strava/callback?code=abc&state={state}")
    assert resp.status_code == 302
    assert resp.url == "/perfil?strava=conectado"
    account = StravaAccount.objects.get(user=user)
    assert account.athlete_id == 424242
    assert account.athlete_name == "Ana Atleta"
    assert account.access_token == "new-access"


def test_callback_rejects_bad_state(client, db, strava_settings):
    resp = client.get("/api/integrations/strava/callback?code=abc&state=forged")
    assert resp.status_code == 302
    assert resp.url == "/perfil?strava=error"
    assert StravaAccount.objects.count() == 0


def test_callback_user_denied(client, db, strava_settings):
    resp = client.get("/api/integrations/strava/callback?error=access_denied")
    assert resp.url == "/perfil?strava=denegado"


def test_sync_imports_and_deduplicates(api, strava_settings, account, monkeypatch):
    payload = [
        strava_activity(),
        strava_activity(id=2222, sport_type="WeightTraining", distance=0, average_speed=0),
        strava_activity(id=3333, moving_time=30),  # too short: skipped
    ]
    monkeypatch.setattr(strava_sync.strava, "fetch_activities", lambda token, after: payload)

    resp = api.post("/api/integrations/strava/sync")
    assert resp.status_code == 200
    assert resp.data["imported"] == 2

    walk = ActivityEntry.objects.get(external_id="1111")
    assert walk.activity_type == "walk"
    assert walk.source == "strava"
    assert str(walk.date) == "2026-08-24"
    assert walk.duration_min == 60
    assert float(walk.distance_km) == 5.2
    assert walk.avg_hr == 112
    assert float(walk.avg_speed_kmh) == 5.18
    assert walk.elevation_m == 42

    gym = ActivityEntry.objects.get(external_id="2222")
    assert gym.activity_type == "gym"
    assert gym.distance_km is None

    # Second sync with the same payload creates nothing new.
    resp = api.post("/api/integrations/strava/sync")
    assert resp.data["imported"] == 0
    assert ActivityEntry.objects.filter(source="strava").count() == 2

    account.refresh_from_db()
    assert account.last_sync_at is not None


def test_sync_refreshes_expired_token(api, strava_settings, account, monkeypatch):
    account.token_expires_at = int(datetime(2020, 1, 1).timestamp())
    account.save()
    monkeypatch.setattr(
        strava_sync.strava,
        "refresh_tokens",
        lambda rt: {
            "access_token": "fresh",
            "refresh_token": "fresh-ref",
            "expires_at": 1900000000,
        },
    )
    monkeypatch.setattr(strava_sync.strava, "fetch_activities", lambda token, after: [])
    resp = api.post("/api/integrations/strava/sync")
    assert resp.status_code == 200
    account.refresh_from_db()
    assert account.access_token == "fresh"
    assert account.refresh_token == "fresh-ref"


def test_sync_without_account(api, strava_settings):
    resp = api.post("/api/integrations/strava/sync")
    assert resp.status_code == 400


def test_disconnect(api, strava_settings, account, monkeypatch):
    monkeypatch.setattr(strava_views.strava, "deauthorize", lambda token: None)
    resp = api.delete("/api/integrations/strava")
    assert resp.status_code == 204
    assert StravaAccount.objects.count() == 0


def test_unknown_sport_maps_to_other():
    fields = strava_sync.map_activity(strava_activity(sport_type="Windsurf"))
    assert fields["activity_type"] == "other"

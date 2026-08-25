"""Minimal Strava API client: OAuth code flow, token refresh, activity listing.

Only what the sync needs. Every network failure surfaces as StravaError so the
views can turn it into a clean API response.
"""

from urllib.parse import urlencode

import requests
from django.conf import settings

AUTHORIZE_URL = "https://www.strava.com/oauth/authorize"
TOKEN_URL = "https://www.strava.com/oauth/token"
DEAUTHORIZE_URL = "https://www.strava.com/oauth/deauthorize"
API_BASE = "https://www.strava.com/api/v3"

PER_PAGE = 200
MAX_PAGES = 5  # hard safety cap: 1000 activities per sync run


class StravaError(Exception):
    pass


def enabled() -> bool:
    return bool(settings.STRAVA_CLIENT_ID and settings.STRAVA_CLIENT_SECRET)


def authorize_url(redirect_uri: str, state: str) -> str:
    params = {
        "client_id": settings.STRAVA_CLIENT_ID,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "approval_prompt": "auto",
        "scope": "read,activity:read_all",
        "state": state,
    }
    return f"{AUTHORIZE_URL}?{urlencode(params)}"


def _token_request(payload: dict) -> dict:
    payload = {
        **payload,
        "client_id": settings.STRAVA_CLIENT_ID,
        "client_secret": settings.STRAVA_CLIENT_SECRET,
    }
    try:
        resp = requests.post(TOKEN_URL, data=payload, timeout=15)
    except requests.RequestException as exc:
        raise StravaError(f"Strava token request failed: {exc}") from exc
    if resp.status_code != 200:
        raise StravaError(f"Strava token request rejected ({resp.status_code})")
    return resp.json()


def exchange_code(code: str) -> dict:
    return _token_request({"grant_type": "authorization_code", "code": code})


def refresh_tokens(refresh_token: str) -> dict:
    return _token_request({"grant_type": "refresh_token", "refresh_token": refresh_token})


def deauthorize(access_token: str) -> None:
    """Best effort — the local link gets removed regardless of the outcome."""
    try:
        requests.post(DEAUTHORIZE_URL, data={"access_token": access_token}, timeout=15)
    except requests.RequestException:
        pass


def fetch_activities(access_token: str, after_epoch: int) -> list[dict]:
    """List the athlete's activities started after the given unix epoch."""
    activities: list[dict] = []
    for page in range(1, MAX_PAGES + 1):
        try:
            resp = requests.get(
                f"{API_BASE}/athlete/activities",
                headers={"Authorization": f"Bearer {access_token}"},
                params={"after": after_epoch, "per_page": PER_PAGE, "page": page},
                timeout=20,
            )
        except requests.RequestException as exc:
            raise StravaError(f"Strava activities request failed: {exc}") from exc
        if resp.status_code != 200:
            raise StravaError(f"Strava activities request rejected ({resp.status_code})")
        batch = resp.json()
        activities.extend(batch)
        if len(batch) < PER_PAGE:
            break
    return activities

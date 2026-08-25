"""Minimal Google Health API client: OAuth code flow and weight data points.

Weight lands here from any source the user's Google Health account syncs
(e.g. a Renpho scale via Health Connect). Failures surface as GoogleHealthError.
"""

from urllib.parse import urlencode

import requests
from django.conf import settings

AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
REVOKE_URL = "https://oauth2.googleapis.com/revoke"
API_BASE = "https://health.googleapis.com/v4"

SCOPE = "https://www.googleapis.com/auth/googlehealth.health_metrics_and_measurements.readonly"

MAX_PAGES = 10


class GoogleHealthError(Exception):
    pass


class TokenRevokedError(GoogleHealthError):
    """The refresh token is dead (expired/revoked); the user must reconnect."""


def enabled() -> bool:
    return bool(settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET)


def authorize_url(redirect_uri: str, state: str) -> str:
    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": SCOPE,
        "access_type": "offline",
        # Always re-issue a refresh token; Google omits it on silent re-auth.
        "prompt": "consent",
        "state": state,
    }
    return f"{AUTHORIZE_URL}?{urlencode(params)}"


def _token_request(payload: dict) -> dict:
    payload = {
        **payload,
        "client_id": settings.GOOGLE_CLIENT_ID,
        "client_secret": settings.GOOGLE_CLIENT_SECRET,
    }
    try:
        resp = requests.post(TOKEN_URL, data=payload, timeout=15)
    except requests.RequestException as exc:
        raise GoogleHealthError(f"Google token request failed: {exc}") from exc
    if resp.status_code != 200:
        try:
            error = resp.json().get("error", "")
        except ValueError:
            error = ""
        if error == "invalid_grant":
            raise TokenRevokedError("Google refresh token expired or revoked")
        raise GoogleHealthError(f"Google token request rejected ({resp.status_code})")
    return resp.json()


def exchange_code(code: str, redirect_uri: str) -> dict:
    return _token_request(
        {"grant_type": "authorization_code", "code": code, "redirect_uri": redirect_uri}
    )


def refresh_tokens(refresh_token: str) -> dict:
    return _token_request({"grant_type": "refresh_token", "refresh_token": refresh_token})


def revoke(token: str) -> None:
    """Best effort — the local link is removed regardless of the outcome."""
    try:
        requests.post(REVOKE_URL, params={"token": token}, timeout=15)
    except requests.RequestException:
        pass


def fetch_weight_points(access_token: str, after_iso: str) -> list[dict]:
    """Weight data points measured at or after the given RFC-3339 instant."""
    points: list[dict] = []
    page_token = None
    for _ in range(MAX_PAGES):
        params: dict = {
            "filter": f'weight.sample_time.physical_time >= "{after_iso}"',
            "pageSize": 1000,
        }
        if page_token:
            params["pageToken"] = page_token
        try:
            resp = requests.get(
                f"{API_BASE}/users/me/dataTypes/weight/dataPoints",
                headers={"Authorization": f"Bearer {access_token}"},
                params=params,
                timeout=20,
            )
        except requests.RequestException as exc:
            raise GoogleHealthError(f"Google Health request failed: {exc}") from exc
        if resp.status_code != 200:
            raise GoogleHealthError(f"Google Health request rejected ({resp.status_code})")
        body = resp.json()
        points.extend(body.get("dataPoints") or [])
        page_token = body.get("nextPageToken")
        if not page_token:
            break
    return points

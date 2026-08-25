import logging
import time

from django.conf import settings
from django.core import signing
from django.shortcuts import redirect
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User

from . import google_health, strava
from .models import GoogleHealthAccount, StravaAccount
from .sync import import_activities
from .sync_health import import_weights

logger = logging.getLogger(__name__)

STATE_SALT = "strava-oauth"
GH_STATE_SALT = "google-health-oauth"
STATE_MAX_AGE_S = 600
CALLBACK_PATH = "/api/integrations/strava/callback"
GH_CALLBACK_PATH = "/api/integrations/google-health/callback"


def _callback_uri(request, path: str) -> str:
    if settings.PUBLIC_BASE_URL:
        return f"{settings.PUBLIC_BASE_URL.rstrip('/')}{path}"
    return request.build_absolute_uri(path)


def _redirect_uri(request) -> str:
    return _callback_uri(request, CALLBACK_PATH)


class StravaAccountView(APIView):
    """Status of the caller's Strava link. DELETE unlinks (and deauthorizes)."""

    def get(self, request):
        if not strava.enabled():
            return Response({"enabled": False, "connected": False})
        account = StravaAccount.objects.filter(user=request.user).first()
        payload: dict = {"enabled": True, "connected": account is not None}
        if account:
            payload["athlete_name"] = account.athlete_name
            payload["last_sync_at"] = account.last_sync_at
        else:
            state = signing.TimestampSigner(salt=STATE_SALT).sign(str(request.user.pk))
            payload["auth_url"] = strava.authorize_url(_redirect_uri(request), state)
        return Response(payload)

    def delete(self, request):
        account = StravaAccount.objects.filter(user=request.user).first()
        if account:
            strava.deauthorize(account.access_token)
            account.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class StravaCallbackView(APIView):
    """OAuth redirect target. Unauthenticated: the signed state carries the user."""

    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        if request.query_params.get("error"):
            return redirect("/perfil?strava=denegado")
        try:
            user_id = signing.TimestampSigner(salt=STATE_SALT).unsign(
                request.query_params.get("state", ""), max_age=STATE_MAX_AGE_S
            )
            user = User.objects.get(pk=int(user_id))
        except (signing.BadSignature, User.DoesNotExist, ValueError):
            logger.warning("Rejected Strava callback with invalid state")
            return redirect("/perfil?strava=error")

        try:
            data = strava.exchange_code(request.query_params.get("code", ""))
        except strava.StravaError:
            logger.exception("Strava code exchange failed for %s", user.email)
            return redirect("/perfil?strava=error")

        athlete = data.get("athlete") or {}
        name = " ".join(
            part for part in (athlete.get("firstname"), athlete.get("lastname")) if part
        )
        athlete_id = athlete.get("id") or 0
        # A Strava athlete can only be linked to one app user at a time.
        StravaAccount.objects.filter(athlete_id=athlete_id).exclude(user=user).delete()
        StravaAccount.objects.update_or_create(
            user=user,
            defaults={
                "athlete_id": athlete_id,
                "athlete_name": name[:120],
                "access_token": data["access_token"],
                "refresh_token": data["refresh_token"],
                "token_expires_at": data["expires_at"],
            },
        )
        return redirect("/perfil?strava=conectado")


class StravaSyncView(APIView):
    """Pull new activities from Strava into the caller's tracking log."""

    def post(self, request):
        account = StravaAccount.objects.filter(user=request.user).first()
        if not account:
            return Response(
                {"detail": "Strava no está conectado"}, status=status.HTTP_400_BAD_REQUEST
            )
        try:
            imported = import_activities(account)
        except strava.StravaError:
            logger.exception("Strava sync failed for %s", request.user.email)
            return Response(
                {"detail": "No se pudo sincronizar con Strava"},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        return Response({"imported": imported, "last_sync_at": account.last_sync_at})


class GoogleHealthAccountView(APIView):
    """Status of the caller's Google Health link. DELETE unlinks (and revokes)."""

    def get(self, request):
        if not google_health.enabled():
            return Response({"enabled": False, "connected": False})
        account = GoogleHealthAccount.objects.filter(user=request.user).first()
        payload: dict = {"enabled": True, "connected": account is not None}
        if account:
            payload["last_sync_at"] = account.last_sync_at
        else:
            state = signing.TimestampSigner(salt=GH_STATE_SALT).sign(str(request.user.pk))
            payload["auth_url"] = google_health.authorize_url(
                _callback_uri(request, GH_CALLBACK_PATH), state
            )
        return Response(payload)

    def delete(self, request):
        account = GoogleHealthAccount.objects.filter(user=request.user).first()
        if account:
            google_health.revoke(account.refresh_token)
            account.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class GoogleHealthCallbackView(APIView):
    """OAuth redirect target. Unauthenticated: the signed state carries the user."""

    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        if request.query_params.get("error"):
            return redirect("/perfil?salud=denegado")
        try:
            user_id = signing.TimestampSigner(salt=GH_STATE_SALT).unsign(
                request.query_params.get("state", ""), max_age=STATE_MAX_AGE_S
            )
            user = User.objects.get(pk=int(user_id))
        except (signing.BadSignature, User.DoesNotExist, ValueError):
            logger.warning("Rejected Google Health callback with invalid state")
            return redirect("/perfil?salud=error")

        try:
            data = google_health.exchange_code(
                request.query_params.get("code", ""),
                _callback_uri(request, GH_CALLBACK_PATH),
            )
        except google_health.GoogleHealthError:
            logger.exception("Google Health code exchange failed for %s", user.email)
            return redirect("/perfil?salud=error")

        refresh_token = data.get("refresh_token")
        if not refresh_token:
            # Without offline access the link dies within the hour: reject it.
            logger.warning("Google Health grant without refresh token for %s", user.email)
            return redirect("/perfil?salud=error")

        GoogleHealthAccount.objects.update_or_create(
            user=user,
            defaults={
                "access_token": data["access_token"],
                "refresh_token": refresh_token,
                "token_expires_at": int(time.time()) + int(data.get("expires_in", 3600)),
            },
        )
        return redirect("/perfil?salud=conectado")


class GoogleHealthSyncView(APIView):
    """Pull new weigh-ins from Google Health into the caller's weight log."""

    def post(self, request):
        account = GoogleHealthAccount.objects.filter(user=request.user).first()
        if not account:
            return Response(
                {"detail": "Google Health no está conectado"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            imported = import_weights(account)
        except google_health.GoogleHealthError:
            logger.exception("Google Health sync failed for %s", request.user.email)
            return Response(
                {"detail": "No se pudo sincronizar con Google Health"},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        return Response({"imported": imported, "last_sync_at": account.last_sync_at})

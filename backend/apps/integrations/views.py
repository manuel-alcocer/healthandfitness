import logging

from django.conf import settings
from django.core import signing
from django.shortcuts import redirect
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User

from . import strava
from .models import StravaAccount
from .sync import import_activities

logger = logging.getLogger(__name__)

STATE_SALT = "strava-oauth"
STATE_MAX_AGE_S = 600
CALLBACK_PATH = "/api/integrations/strava/callback"


def _redirect_uri(request) -> str:
    if settings.PUBLIC_BASE_URL:
        return f"{settings.PUBLIC_BASE_URL.rstrip('/')}{CALLBACK_PATH}"
    return request.build_absolute_uri(CALLBACK_PATH)


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

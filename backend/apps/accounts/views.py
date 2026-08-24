import logging

from django.conf import settings
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView

from .models import Profile, User
from .serializers import ProfileSerializer, UserSerializer

logger = logging.getLogger(__name__)


class AuthConfigView(APIView):
    """Public runtime config the SPA needs before anyone logs in."""

    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        return Response({"google_client_id": settings.GOOGLE_CLIENT_ID})


class GoogleLoginView(APIView):
    """Exchange a Google ID token (from Google Identity Services) for JWTs."""

    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        credential = request.data.get("credential")
        if not credential:
            return Response({"detail": "Missing credential"}, status=status.HTTP_400_BAD_REQUEST)
        if not settings.GOOGLE_CLIENT_ID:
            return Response(
                {"detail": "Google Sign-In is not configured"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        try:
            idinfo = google_id_token.verify_oauth2_token(
                credential, google_requests.Request(), settings.GOOGLE_CLIENT_ID
            )
        except ValueError:
            logger.warning("Rejected invalid Google ID token")
            return Response({"detail": "Invalid token"}, status=status.HTTP_401_UNAUTHORIZED)

        if not idinfo.get("email_verified"):
            return Response({"detail": "Email not verified"}, status=status.HTTP_401_UNAUTHORIZED)

        email = idinfo["email"].lower()
        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                "username": email,
                "google_sub": idinfo["sub"],
                "first_name": idinfo.get("given_name", ""),
                "last_name": idinfo.get("family_name", ""),
                "avatar_url": idinfo.get("picture", ""),
            },
        )
        if not created:
            updates = []
            if user.google_sub != idinfo["sub"]:
                user.google_sub = idinfo["sub"]
                updates.append("google_sub")
            if idinfo.get("picture") and user.avatar_url != idinfo["picture"]:
                user.avatar_url = idinfo["picture"]
                updates.append("avatar_url")
            if updates:
                user.save(update_fields=updates)

        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": UserSerializer(user).data,
                "created": created,
            }
        )


class MeView(APIView):
    """Everything the SPA needs to route the user: profile + goal state."""

    def get(self, request):
        from apps.goals.models import Goal
        from apps.goals.serializers import GoalSerializer

        user = request.user
        profile = Profile.objects.filter(user=user).first()
        goal = Goal.objects.filter(user=user).order_by("-created_at").first()
        return Response(
            {
                "user": UserSerializer(user).data,
                "profile": ProfileSerializer(profile).data if profile else None,
                "goal": GoalSerializer(goal).data if goal else None,
            }
        )


class ProfileView(APIView):
    """Create or update the caller's biometric profile."""

    def get(self, request):
        profile = Profile.objects.filter(user=request.user).first()
        if not profile:
            return Response({"detail": "No profile yet"}, status=status.HTTP_404_NOT_FOUND)
        return Response(ProfileSerializer(profile).data)

    def put(self, request):
        profile = Profile.objects.filter(user=request.user).first()
        serializer = ProfileSerializer(profile, data=request.data, partial=profile is not None)
        serializer.is_valid(raise_exception=True)
        serializer.save(user=request.user)
        return Response(serializer.data, status=status.HTTP_200_OK if profile else 201)


class RefreshView(TokenRefreshView):
    permission_classes = [AllowAny]
    authentication_classes = []

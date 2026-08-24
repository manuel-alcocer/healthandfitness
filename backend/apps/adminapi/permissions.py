import hmac

from django.conf import settings
from rest_framework.permissions import BasePermission


class HasAdminToken(BasePermission):
    """Shared-secret auth for the admin CLI: X-Admin-Token header."""

    message = "Invalid or missing admin token"

    def has_permission(self, request, view):
        token = request.headers.get("X-Admin-Token", "")
        expected = settings.ADMIN_API_TOKEN
        return bool(expected) and hmac.compare_digest(token, expected)

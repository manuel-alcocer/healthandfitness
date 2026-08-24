from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path


def healthz(_request):
    return JsonResponse({"status": "ok"})


urlpatterns = [
    path("healthz", healthz),
    path("admin/", admin.site.urls),
    path("api/auth/", include("apps.accounts.urls")),
    path("api/", include("apps.goals.urls")),
    path("api/", include("apps.plans.urls")),
    path("api/", include("apps.tracking.urls")),
    path("api/admin/", include("apps.adminapi.urls")),
]

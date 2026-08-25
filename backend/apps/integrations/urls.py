from django.urls import path

from .views import (
    GoogleHealthAccountView,
    GoogleHealthCallbackView,
    GoogleHealthSyncView,
    StravaAccountView,
    StravaCallbackView,
    StravaSyncView,
)

urlpatterns = [
    path("strava", StravaAccountView.as_view()),
    path("strava/callback", StravaCallbackView.as_view()),
    path("strava/sync", StravaSyncView.as_view()),
    path("google-health", GoogleHealthAccountView.as_view()),
    path("google-health/callback", GoogleHealthCallbackView.as_view()),
    path("google-health/sync", GoogleHealthSyncView.as_view()),
]

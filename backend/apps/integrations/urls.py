from django.urls import path

from .views import StravaAccountView, StravaCallbackView, StravaSyncView

urlpatterns = [
    path("strava", StravaAccountView.as_view()),
    path("strava/callback", StravaCallbackView.as_view()),
    path("strava/sync", StravaSyncView.as_view()),
]

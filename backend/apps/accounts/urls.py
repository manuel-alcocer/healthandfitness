from django.urls import path

from .views import AuthConfigView, GoogleLoginView, MeView, ProfileView, RefreshView

urlpatterns = [
    path("config", AuthConfigView.as_view()),
    path("google", GoogleLoginView.as_view()),
    path("refresh", RefreshView.as_view()),
    path("me", MeView.as_view()),
    path("profile", ProfileView.as_view()),
]

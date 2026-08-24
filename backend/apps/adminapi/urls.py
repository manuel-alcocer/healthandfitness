from django.urls import path

from .views import SubmitPlanView, UserBundleView, UserListView, UserProgressView

urlpatterns = [
    path("users", UserListView.as_view()),
    path("users/<int:user_id>/bundle", UserBundleView.as_view()),
    path("users/<int:user_id>/plan", SubmitPlanView.as_view()),
    path("users/<int:user_id>/progress", UserProgressView.as_view()),
]

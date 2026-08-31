from django.urls import path

from .views import (
    PlanDayAdminView,
    PlanDaysAdminView,
    SubmitPlanView,
    UserBundleView,
    UserListView,
    UserProgressView,
    WeeklyFeedbackAdminView,
)

urlpatterns = [
    path("users", UserListView.as_view()),
    path("users/<int:user_id>/bundle", UserBundleView.as_view()),
    path("users/<int:user_id>/plan", SubmitPlanView.as_view()),
    path("users/<int:user_id>/plan/days", PlanDaysAdminView.as_view()),
    path("users/<int:user_id>/plan/days/<str:day>", PlanDayAdminView.as_view()),
    path("users/<int:user_id>/feedback", WeeklyFeedbackAdminView.as_view()),
    path("users/<int:user_id>/progress", UserProgressView.as_view()),
]

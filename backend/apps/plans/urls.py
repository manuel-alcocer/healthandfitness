from django.urls import path

from .views import PlanDaysView, PlanView, WeeklyFeedbackListView

urlpatterns = [
    path("plan", PlanView.as_view()),
    path("plan/days", PlanDaysView.as_view()),
    path("feedback", WeeklyFeedbackListView.as_view()),
]

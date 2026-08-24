from django.urls import path

from .views import AcceptSuggestionView, GoalView

urlpatterns = [
    path("goal", GoalView.as_view()),
    path("goal/accept-suggestion", AcceptSuggestionView.as_view()),
]

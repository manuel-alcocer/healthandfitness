from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    ActivityEntryViewSet,
    CalendarView,
    NutritionEntryViewSet,
    ProgressView,
    WeightEntryViewSet,
)

router = DefaultRouter(trailing_slash=False)
router.register("tracking/weights", WeightEntryViewSet, basename="weights")
router.register("tracking/activities", ActivityEntryViewSet, basename="activities")
router.register("tracking/nutrition", NutritionEntryViewSet, basename="nutrition")

urlpatterns = [
    path("progress", ProgressView.as_view()),
    path("calendar", CalendarView.as_view()),
    path("", include(router.urls)),
]

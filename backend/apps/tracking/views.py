from datetime import date

from rest_framework import mixins, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from .calendar import compute_calendar
from .models import ActivityEntry, NutritionEntry, WeightEntry
from .progress import compute_progress, weekly_summary
from .serializers import (
    ActivityEntrySerializer,
    NutritionEntrySerializer,
    WeightEntrySerializer,
)


class OwnedModelViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """CRUD over the caller's own entries only."""

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class WeightEntryViewSet(OwnedModelViewSet):
    queryset = WeightEntry.objects.all()
    serializer_class = WeightEntrySerializer

    def create(self, request, *args, **kwargs):
        """Upsert by date: weighing yourself twice a day just updates the value."""
        existing = WeightEntry.objects.filter(
            user=request.user, date=request.data.get("date")
        ).first()
        if existing:
            serializer = self.get_serializer(existing, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            # A hand-entered value wins over (and stops) scale imports for the day.
            serializer.save(source=WeightEntry.Source.MANUAL)
            return Response(serializer.data)
        return super().create(request, *args, **kwargs)


class ActivityEntryViewSet(OwnedModelViewSet):
    queryset = ActivityEntry.objects.all()
    serializer_class = ActivityEntrySerializer


class NutritionEntryViewSet(OwnedModelViewSet):
    queryset = NutritionEntry.objects.all()
    serializer_class = NutritionEntrySerializer

    def create(self, request, *args, **kwargs):
        existing = NutritionEntry.objects.filter(
            user=request.user, date=request.data.get("date")
        ).first()
        if existing:
            serializer = self.get_serializer(existing, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data)
        return super().create(request, *args, **kwargs)


class CalendarView(APIView):
    """Month grid of daily compliance levels (red/yellow/green/medal)."""

    def get(self, request):
        raw = request.query_params.get("month", "")
        try:
            year, month = (int(p) for p in raw.split("-"))
            date(year, month, 1)
        except (ValueError, TypeError):
            today = date.today()
            year, month = today.year, today.month
        return Response(compute_calendar(request.user, year, month))


class ProgressView(APIView):
    """The dashboard payload: series, weekly compliance and verdict."""

    def get(self, request):
        data = compute_progress(request.user)
        data["weekly_exercise"] = weekly_summary(request.user)
        return Response(data)

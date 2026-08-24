from django.contrib import admin

from .models import ActivityEntry, NutritionEntry, WeightEntry


@admin.register(WeightEntry)
class WeightEntryAdmin(admin.ModelAdmin):
    list_display = ["user", "date", "weight_kg"]
    search_fields = ["user__email"]


@admin.register(ActivityEntry)
class ActivityEntryAdmin(admin.ModelAdmin):
    list_display = ["user", "date", "activity_type", "duration_min", "distance_km", "avg_hr"]
    list_filter = ["activity_type"]
    search_fields = ["user__email"]


@admin.register(NutritionEntry)
class NutritionEntryAdmin(admin.ModelAdmin):
    list_display = ["user", "date", "adherence"]
    search_fields = ["user__email"]

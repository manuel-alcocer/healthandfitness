from django.contrib import admin

from .models import Plan, PlanDay, WeeklyFeedback


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ["goal", "start_date", "created_at"]


@admin.register(PlanDay)
class PlanDayAdmin(admin.ModelAdmin):
    list_display = ["plan", "date", "updated_at"]
    list_filter = ["plan"]


@admin.register(WeeklyFeedback)
class WeeklyFeedbackAdmin(admin.ModelAdmin):
    list_display = ["user", "week_start", "updated_at"]

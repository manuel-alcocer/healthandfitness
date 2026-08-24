from django.contrib import admin

from .models import Goal


@admin.register(Goal)
class GoalAdmin(admin.ModelAdmin):
    list_display = ["user", "target_weight_kg", "target_date", "status", "created_at"]
    list_filter = ["status"]
    search_fields = ["user__email"]

from django.contrib import admin

from .models import StravaAccount


@admin.register(StravaAccount)
class StravaAccountAdmin(admin.ModelAdmin):
    list_display = ("user", "athlete_id", "athlete_name", "last_sync_at", "created_at")
    search_fields = ("user__email", "athlete_name")

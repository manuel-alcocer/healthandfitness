from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Profile, User


@admin.register(User)
class HnfUserAdmin(UserAdmin):
    list_display = ["email", "first_name", "last_name", "is_staff", "date_joined"]
    ordering = ["email"]


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ["user", "sex", "birth_date", "height_cm", "initial_weight_kg"]
    search_fields = ["user__email"]

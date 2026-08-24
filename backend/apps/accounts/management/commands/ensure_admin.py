"""Idempotently create/update the admin superuser from environment settings.

Runs in the k8s migrate job so the Django admin is always reachable with the
password stored in the cluster secret.
"""

from django.conf import settings
from django.core.management.base import BaseCommand

from apps.accounts.models import User


class Command(BaseCommand):
    help = "Create or update the superuser defined by ADMIN_EMAIL/ADMIN_PASSWORD"

    def handle(self, *args, **options):
        email = settings.ADMIN_EMAIL
        password = settings.ADMIN_PASSWORD
        if not email or not password:
            self.stdout.write("ADMIN_EMAIL/ADMIN_PASSWORD not set; skipping")
            return
        user, created = User.objects.get_or_create(
            email=email.lower(), defaults={"username": email.lower()}
        )
        user.is_staff = True
        user.is_superuser = True
        user.set_password(password)
        user.save()
        self.stdout.write(f"Superuser {'created' if created else 'updated'}: {email}")

# core/management/commands/create_admin.py
"""
Create/update the admin superuser from environment variables.
Credentials are NEVER hardcoded here (this file lives on GitHub).

Usage:
  DJANGO_SUPERUSER_USERNAME=... DJANGO_SUPERUSER_EMAIL=... DJANGO_SUPERUSER_PASSWORD=... \
      python manage.py create_admin
"""
import os

from django.core.management.base import BaseCommand
from core.models import CustomUser


class Command(BaseCommand):
    help = 'Create or update the admin superuser from DJANGO_SUPERUSER_* environment variables'

    def handle(self, *args, **options):
        username = os.environ.get('DJANGO_SUPERUSER_USERNAME', '')
        email = os.environ.get('DJANGO_SUPERUSER_EMAIL', '')
        password = os.environ.get('DJANGO_SUPERUSER_PASSWORD', '')

        if not (username and password):
            self.stderr.write(self.style.ERROR(
                'Variables manquantes : définissez DJANGO_SUPERUSER_USERNAME, '
                'DJANGO_SUPERUSER_EMAIL et DJANGO_SUPERUSER_PASSWORD avant de lancer la commande.'
            ))
            return

        if CustomUser.objects.filter(username=username).exists():
            user = CustomUser.objects.get(username=username)
            user.set_password(password)
            user.is_staff = True
            user.is_superuser = True
            user.category = 'viewer'
            user.email_verified = True
            user.save()
            self.stdout.write(self.style.SUCCESS(f'Superuser "{username}" mis à jour'))
        else:
            CustomUser.objects.create_superuser(
                username=username,
                email=email,
                password=password,
                category='viewer',
                email_verified=True,
            )
            self.stdout.write(self.style.SUCCESS(f'Superuser "{username}" créé'))

# core/management/commands/update_postcard_flags.py
"""
Update has_images and has_animation flags for all postcards
"""

from django.core.management.base import BaseCommand
from core.models import Postcard


class Command(BaseCommand):
    help = 'Update postcard flags based on actual files'

    def handle(self, *args, **options):
        postcards = Postcard.objects.all()
        total = postcards.count()

        self.stdout.write(f'Updating flags for {total} postcards...')

        updated = 0
        for i, postcard in enumerate(postcards):
            postcard.update_image_flags()
            updated += 1

            if (i + 1) % 100 == 0:
                self.stdout.write(f'  Progress: {i + 1}/{total}')

        self.stdout.write(self.style.SUCCESS(f'✓ Updated {updated} postcards'))
# core/management/commands/create_postcards_from_images.py
"""
Create postcard database entries from existing image files.
"""

from pathlib import Path
from django.core.management.base import BaseCommand
from django.conf import settings
from core.models import Postcard


class Command(BaseCommand):
    help = 'Create postcard entries from existing image files in media folder'

    def handle(self, *args, **options):
        media_root = Path(settings.MEDIA_ROOT)
        vignette_dir = media_root / 'postcards' / 'Vignette'

        if not vignette_dir.exists():
            self.stdout.write(self.style.ERROR(f'Vignette directory not found: {vignette_dir}'))
            return

        # Get all image files
        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.JPG', '.JPEG', '.PNG', '.GIF'}

        created = 0
        updated = 0

        for file_path in vignette_dir.iterdir():
            if file_path.suffix not in image_extensions:
                continue

            # Extract number from filename
            number = file_path.stem

            # Skip if not numeric
            if not number.isdigit():
                continue

            # Pad to 6 digits
            number = number.zfill(6)

            # Create or get postcard
            postcard, was_created = Postcard.objects.get_or_create(
                number=number,
                defaults={
                    'title': f'Carte postale {number}',
                    'keywords': '',
                    'description': '',
                    'rarity': 'common',
                    'has_images': True,
                }
            )

            if was_created:
                created += 1
                if created % 100 == 0:
                    self.stdout.write(f'Created {created} postcards...')
            else:
                # Update has_images if needed
                if not postcard.has_images:
                    postcard.has_images = True
                    postcard.save(update_fields=['has_images'])
                    updated += 1

        self.stdout.write(self.style.SUCCESS(f'\nDone! Created {created}, Updated {updated} postcards'))
        self.stdout.write(f'Total postcards in database: {Postcard.objects.count()}')
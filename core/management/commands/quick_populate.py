# core/management/commands/quick_populate.py
"""
Quick command to populate database with basic postcard entries.
Run with: python manage.py quick_populate
"""

from django.core.management.base import BaseCommand
from django.conf import settings
from core.models import Postcard
from pathlib import Path


class Command(BaseCommand):
    help = 'Populate database with postcards based on existing image files'

    def add_arguments(self, parser):
        parser.add_argument(
            '--scan-only',
            action='store_true',
            help='Only scan and report, do not create entries'
        )

    def handle(self, *args, **options):
        media_root = Path(settings.MEDIA_ROOT)
        vignette_path = media_root / 'postcards' / 'Vignette'

        scan_only = options['scan_only']

        if not vignette_path.exists():
            self.stderr.write(self.style.ERROR(f'Vignette folder not found: {vignette_path}'))
            self.stdout.write('Creating directory structure...')

            for folder in ['Vignette', 'Grande', 'Dos', 'Zoom']:
                (media_root / 'postcards' / folder).mkdir(parents=True, exist_ok=True)
            (media_root / 'animated_cp').mkdir(parents=True, exist_ok=True)

            self.stdout.write(self.style.SUCCESS('Directory structure created'))
            return

        # Find all image files
        extensions = ['*.jpg', '*.jpeg', '*.png', '*.JPG', '*.JPEG', '*.PNG']
        image_files = []

        for ext in extensions:
            image_files.extend(vignette_path.glob(ext))

        self.stdout.write(f'Found {len(image_files)} image files in Vignette folder')

        if scan_only:
            for f in image_files[:10]:
                self.stdout.write(f'  {f.name}')
            if len(image_files) > 10:
                self.stdout.write(f'  ... and {len(image_files) - 10} more')
            return

        created = 0
        skipped = 0

        for img_file in image_files:
            # Extract number from filename (e.g., "000001.jpg" -> "000001")
            number = img_file.stem

            # Check if already exists
            if Postcard.objects.filter(number=number).exists():
                skipped += 1
                continue

            # Create postcard entry
            Postcard.objects.create(
                number=number,
                title=f'Carte postale {number}',
                has_images=True
            )
            created += 1

        self.stdout.write(self.style.SUCCESS(f'\nPopulation completed:'))
        self.stdout.write(f'  Created: {created}')
        self.stdout.write(f'  Skipped (existing): {skipped}')

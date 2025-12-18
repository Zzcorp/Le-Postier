# core/management/commands/populate_from_images.py
"""
Populate database with postcard entries based on downloaded image files.
Creates basic entries for all images found on disk.
"""

from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import transaction
from core.models import Postcard
from pathlib import Path
import os


def get_media_root():
    """Get the correct media root path"""
    if os.environ.get('RENDER', 'false').lower() == 'true' or Path('/var/data').exists():
        return Path('/var/data/media')
    return Path(settings.MEDIA_ROOT)


class Command(BaseCommand):
    help = 'Populate database with postcards from downloaded image files'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Preview without creating')
        parser.add_argument('--update', action='store_true', help='Update existing entries')
        parser.add_argument('--clear', action='store_true', help='Clear existing entries first')

    def handle(self, *args, **options):
        media_root = get_media_root()

        self.stdout.write(f"\n{'=' * 60}")
        self.stdout.write("Populate Database from Image Files")
        self.stdout.write(f"{'=' * 60}")
        self.stdout.write(f"Media root: {media_root}")
        self.stdout.write(f"Media root exists: {media_root.exists()}")

        if options['clear'] and not options['dry_run']:
            count = Postcard.objects.count()
            Postcard.objects.all().delete()
            self.stdout.write(f"Cleared {count} existing postcards")

        # Scan Vignette folder (primary source)
        vignette_path = media_root / 'postcards' / 'Vignette'

        if not vignette_path.exists():
            self.stderr.write(self.style.ERROR(f"Vignette folder not found: {vignette_path}"))
            return

        # Find all image files
        image_files = set()
        for ext in ['*.jpg', '*.jpeg', '*.png', '*.JPG', '*.JPEG', '*.PNG']:
            for f in vignette_path.glob(ext):
                # Extract number from filename
                num = f.stem
                # Handle files like "000001_1.jpg"
                if '_' in num:
                    num = num.split('_')[0]
                image_files.add(num)

        self.stdout.write(f"\nFound {len(image_files)} unique postcards in Vignette folder")

        # Check animated folder
        animated_path = media_root / 'animated_cp'
        animated_files = set()
        if animated_path.exists():
            for ext in ['*.mp4', '*.webm', '*.MP4', '*.WEBM']:
                for f in animated_path.glob(ext):
                    num = f.stem.split('_')[0]
                    animated_files.add(num)
            self.stdout.write(f"Found {len(animated_files)} animated postcards")

        if options['dry_run']:
            self.stdout.write(self.style.WARNING("\n[DRY RUN] Would create entries for:"))
            for num in sorted(list(image_files))[:20]:
                self.stdout.write(f"  - {num}")
            if len(image_files) > 20:
                self.stdout.write(f"  ... and {len(image_files) - 20} more")
            return

        # Create database entries
        created = 0
        updated = 0
        skipped = 0

        self.stdout.write("\nCreating database entries...")

        with transaction.atomic():
            for i, num in enumerate(sorted(image_files)):
                try:
                    has_animation = num in animated_files

                    if options['update']:
                        postcard, is_new = Postcard.objects.update_or_create(
                            number=num,
                            defaults={
                                'title': f'Carte Postale N° {num}',
                                'has_images': True,
                            }
                        )
                        if is_new:
                            created += 1
                        else:
                            updated += 1
                    else:
                        postcard, is_new = Postcard.objects.get_or_create(
                            number=num,
                            defaults={
                                'title': f'Carte Postale N° {num}',
                                'has_images': True,
                            }
                        )
                        if is_new:
                            created += 1
                        else:
                            skipped += 1

                    if (i + 1) % 500 == 0:
                        self.stdout.write(f"  Progress: {i + 1}/{len(image_files)}")

                except Exception as e:
                    self.stderr.write(f"  Error for {num}: {e}")

        self.stdout.write(f"\n{'=' * 60}")
        self.stdout.write(self.style.SUCCESS("POPULATION COMPLETE"))
        self.stdout.write(f"{'=' * 60}")
        self.stdout.write(f"Created: {created}")
        self.stdout.write(f"Updated: {updated}")
        self.stdout.write(f"Skipped: {skipped}")
        self.stdout.write(f"Total in DB: {Postcard.objects.count()}")
        self.stdout.write(f"{'=' * 60}\n")
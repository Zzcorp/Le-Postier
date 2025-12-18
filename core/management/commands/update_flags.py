# core/management/commands/update_flags.py
"""
Update has_images flag for all postcards based on actual files on disk.
"""

from django.core.management.base import BaseCommand
from django.conf import settings
from core.models import Postcard
from pathlib import Path
import os


def get_media_root():
    """Get the correct media root path - always use persistent disk on Render"""
    if os.environ.get('RENDER', 'false').lower() == 'true' or Path('/var/data').exists():
        return Path('/var/data/media')
    return Path(settings.MEDIA_ROOT)


class Command(BaseCommand):
    help = 'Update postcard flags based on actual media files on persistent disk'

    def add_arguments(self, parser):
        parser.add_argument('--verbose', action='store_true', help='Show detailed output')

    def handle(self, *args, **options):
        verbose = options['verbose']

        # CRITICAL: Use the correct media root
        media_root = get_media_root()

        self.stdout.write(f"\n{'=' * 60}")
        self.stdout.write("Updating Postcard Flags")
        self.stdout.write(f"{'=' * 60}")
        self.stdout.write(f"RENDER env: {os.environ.get('RENDER', 'not set')}")
        self.stdout.write(f"/var/data exists: {Path('/var/data').exists()}")
        self.stdout.write(self.style.SUCCESS(f"Media root: {media_root}"))
        self.stdout.write(f"Media root exists: {media_root.exists()}")

        if not media_root.exists():
            self.stderr.write(self.style.ERROR(f"Media root does not exist: {media_root}"))
            self.stderr.write("Creating directories...")
            self.create_directories(media_root)

        # Scan what files exist
        self.stdout.write("\nScanning media folders...")

        existing_files = {
            'Vignette': set(),
            'Grande': set(),
            'Dos': set(),
            'Zoom': set(),
            'animated': set(),
        }

        # Scan postcard folders
        for folder in ['Vignette', 'Grande', 'Dos', 'Zoom']:
            folder_path = media_root / 'postcards' / folder
            if folder_path.exists():
                for ext in ['*.jpg', '*.jpeg', '*.png', '*.JPG', '*.JPEG', '*.PNG', '*.gif', '*.GIF']:
                    for f in folder_path.glob(ext):
                        num = f.stem
                        if '_' in num:
                            num = num.split('_')[0]
                        existing_files[folder].add(num)
                self.stdout.write(f"  {folder}: {len(existing_files[folder])} files")
            else:
                self.stdout.write(f"  {folder}: NOT FOUND")

        # Scan animated folder
        animated_path = media_root / 'animated_cp'
        if animated_path.exists():
            for ext in ['*.mp4', '*.webm', '*.MP4', '*.WEBM']:
                for f in animated_path.glob(ext):
                    num = f.stem.split('_')[0]
                    existing_files['animated'].add(num)
            self.stdout.write(f"  animated: {len(existing_files['animated'])} files")
        else:
            self.stdout.write(f"  animated: NOT FOUND")

        # Update postcards
        self.stdout.write("\nUpdating postcards in database...")

        postcards = Postcard.objects.all()
        total = postcards.count()

        if total == 0:
            self.stdout.write(self.style.WARNING("No postcards in database. Run import_csv or populate_from_images first."))
            return

        updated = 0
        has_images_count = 0
        has_animation_count = 0

        for i, postcard in enumerate(postcards):
            padded_num = postcard.get_padded_number()

            has_vignette = padded_num in existing_files['Vignette']
            has_animation = padded_num in existing_files['animated']

            changed = False
            if postcard.has_images != has_vignette:
                postcard.has_images = has_vignette
                changed = True

            if changed:
                postcard.save(update_fields=['has_images'])
                updated += 1

            if has_vignette:
                has_images_count += 1
            if has_animation:
                has_animation_count += 1

            if verbose and (i + 1) % 500 == 0:
                self.stdout.write(f"  Progress: {i + 1}/{total}")

        self.stdout.write(f"\n{'=' * 60}")
        self.stdout.write(self.style.SUCCESS("UPDATE COMPLETE"))
        self.stdout.write(f"{'=' * 60}")
        self.stdout.write(f"Total postcards: {total}")
        self.stdout.write(f"With images: {has_images_count}")
        self.stdout.write(f"With animation: {has_animation_count}")
        self.stdout.write(f"Records updated: {updated}")
        self.stdout.write(f"{'=' * 60}\n")

    def create_directories(self, media_root):
        """Create all necessary directories"""
        directories = [
            media_root / 'postcards' / 'Vignette',
            media_root / 'postcards' / 'Grande',
            media_root / 'postcards' / 'Dos',
            media_root / 'postcards' / 'Zoom',
            media_root / 'animated_cp',
            media_root / 'signatures',
        ]
        for d in directories:
            d.mkdir(parents=True, exist_ok=True)
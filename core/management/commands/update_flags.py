# core/management/commands/update_flags.py
"""
Update has_images flag for all postcards based on actual files.
"""

from django.core.management.base import BaseCommand
from django.conf import settings
from core.models import Postcard
from pathlib import Path


class Command(BaseCommand):
    help = 'Update postcard flags based on actual media files'

    def add_arguments(self, parser):
        parser.add_argument('--verbose', action='store_true',
                            help='Show detailed output')

    def handle(self, *args, **options):
        verbose = options['verbose']
        media_root = Path(settings.MEDIA_ROOT)

        self.stdout.write(f"\n{'=' * 60}")
        self.stdout.write("Updating Postcard Flags")
        self.stdout.write(f"{'=' * 60}")
        self.stdout.write(f"Media root: {media_root}")

        # First, scan what files exist
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
                for ext in ['*.jpg', '*.jpeg', '*.png', '*.JPG', '*.JPEG', '*.PNG']:
                    for f in folder_path.glob(ext):
                        # Extract number from filename
                        num = f.stem
                        existing_files[folder].add(num)
                self.stdout.write(f"  {folder}: {len(existing_files[folder])} files")

        # Scan animated folder
        animated_path = media_root / 'animated_cp'
        if animated_path.exists():
            for ext in ['*.mp4', '*.webm', '*.MP4', '*.WEBM']:
                for f in animated_path.glob(ext):
                    # Handle both 000001.mp4 and 000001_0.mp4 formats
                    num = f.stem.split('_')[0]
                    existing_files['animated'].add(num)
            self.stdout.write(f"  animated: {len(existing_files['animated'])} files")

        # Update postcards
        self.stdout.write("\nUpdating postcards...")

        postcards = Postcard.objects.all()
        total = postcards.count()
        updated = 0
        has_images_count = 0
        has_animation_count = 0

        for i, postcard in enumerate(postcards):
            padded_num = postcard.get_padded_number()

            # Check if has vignette
            has_vignette = padded_num in existing_files['Vignette']

            # Check if has animation
            has_animation = padded_num in existing_files['animated']

            # Update if changed
            changed = False
            if postcard.has_images != has_vignette:
                postcard.has_images = has_vignette
                changed = True

            # Try to update has_animation if field exists
            try:
                if hasattr(postcard, 'has_animation') and postcard.has_animation != has_animation:
                    postcard.has_animation = has_animation
                    changed = True
            except:
                pass

            if changed:
                postcard.save()
                updated += 1

            if has_vignette:
                has_images_count += 1
            if has_animation:
                has_animation_count += 1

            if verbose and (i + 1) % 200 == 0:
                self.stdout.write(f"  Progress: {i + 1}/{total}")

        self.stdout.write(f"\n{'=' * 60}")
        self.stdout.write(self.style.SUCCESS("UPDATE COMPLETE"))
        self.stdout.write(f"{'=' * 60}")
        self.stdout.write(f"Total postcards: {total}")
        self.stdout.write(f"With images: {has_images_count}")
        self.stdout.write(f"With animation: {has_animation_count}")
        self.stdout.write(f"Updated: {updated}")
        self.stdout.write(f"{'=' * 60}\n")
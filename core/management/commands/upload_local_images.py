# core/management/commands/upload_local_images.py
from django.core.management.base import BaseCommand
from django.core.files import File
from django.core.files.storage import default_storage
from core.models import Postcard
import os
from pathlib import Path


class Command(BaseCommand):
    help = 'Upload images from local directory to Django media storage'

    def add_arguments(self, parser):
        parser.add_argument('--images-dir', type=str, required=True,
                            help='Directory containing postcard images organized by type')
        parser.add_argument('--dry-run', action='store_true',
                            help='Show what would be done without making changes')

    def handle(self, *args, **options):
        images_dir = Path(options['images_dir'])
        dry_run = options['dry_run']

        if not images_dir.exists():
            self.stdout.write(self.style.ERROR(f'Directory not found: {images_dir}'))
            return

        self.stdout.write(self.style.SUCCESS(f'📁 Scanning directory: {images_dir}'))

        # Expected structure:
        # images_dir/
        #   Vignette/
        #     000001.jpg
        #     000002.jpg
        #   Grande/
        #   Dos/
        #   Zoom/

        image_types = {
            'Vignette': 'vignette_image',
            'Grande': 'grande_image',
            'Dos': 'dos_image',
            'Zoom': 'zoom_image',
        }

        uploaded_count = 0
        skipped_count = 0
        error_count = 0

        postcards = Postcard.objects.all()
        total = postcards.count()

        for postcard in postcards:
            num_padded = str(postcard.number).zfill(6)
            postcard_updated = False

            for folder_name, field_name in image_types.items():
                # Check if field already has a file
                field = getattr(postcard, field_name)
                if field:
                    continue

                # Look for image file
                image_path = images_dir / folder_name / f'{num_padded}.jpg'
                if not image_path.exists():
                    # Try without padding
                    image_path = images_dir / folder_name / f'{postcard.number}.jpg'

                if image_path.exists():
                    if not dry_run:
                        try:
                            with open(image_path, 'rb') as img_file:
                                django_file = File(img_file, name=image_path.name)
                                setattr(postcard, field_name, django_file)
                                postcard_updated = True
                                self.stdout.write(f'  ✅ {num_padded} - {folder_name}')
                        except Exception as e:
                            self.stdout.write(self.style.ERROR(f'  ❌ {num_padded} - {folder_name}: {e}'))
                            error_count += 1
                    else:
                        self.stdout.write(f'  [DRY RUN] Would upload: {num_padded} - {folder_name}')

            if postcard_updated:
                if not dry_run:
                    postcard.save()
                uploaded_count += 1
            else:
                skipped_count += 1

            if (uploaded_count + skipped_count) % 50 == 0:
                self.stdout.write(f'  Progress: {uploaded_count + skipped_count}/{total}')

        self.stdout.write('\n' + '=' * 70)
        self.stdout.write(self.style.SUCCESS('✅ UPLOAD COMPLETE'))
        self.stdout.write('=' * 70)
        self.stdout.write(f'   Postcards processed: {uploaded_count}')
        self.stdout.write(f'   Skipped (no images): {skipped_count}')
        self.stdout.write(f'   Errors: {error_count}')
# core/management/commands/check_media.py
from django.core.management.base import BaseCommand
from django.conf import settings
from pathlib import Path
import os


def get_media_root():
    """Get the correct media root path - always use persistent disk on Render"""
    if os.environ.get('RENDER', 'false').lower() == 'true' or Path('/var/data').exists():
        return Path('/var/data/media')
    return Path(settings.MEDIA_ROOT)


class Command(BaseCommand):
    help = 'Check media files status and configuration'

    def handle(self, *args, **options):
        # Use the correct media root
        media_root = get_media_root()

        self.stdout.write(f"\n{'=' * 60}")
        self.stdout.write("Media Configuration Check")
        self.stdout.write(f"{'=' * 60}")

        self.stdout.write(f'\nEnvironment:')
        self.stdout.write(f'  RENDER env: {os.environ.get("RENDER", "not set")}')
        self.stdout.write(f'  /var/data exists: {Path("/var/data").exists()}')
        self.stdout.write(f'  settings.MEDIA_ROOT: {settings.MEDIA_ROOT}')
        self.stdout.write(f'  Actual MEDIA_ROOT used: {media_root}')
        self.stdout.write(f'  MEDIA_URL setting: {settings.MEDIA_URL}')

        self.stdout.write(f'\nMedia Root: {media_root}')
        self.stdout.write(f'  Exists: {media_root.exists()}')
        self.stdout.write(f'  Is directory: {media_root.is_dir() if media_root.exists() else "N/A"}')

        if not media_root.exists():
            self.stdout.write(self.style.WARNING('\nMedia directory does not exist!'))
            self.stdout.write('Creating directories...')
            self.create_directories(media_root)

        # Check postcards folders
        self.stdout.write('\nPostcards Images:')
        total_images = 0
        for folder in ['Vignette', 'Grande', 'Dos', 'Zoom']:
            folder_path = media_root / 'postcards' / folder
            if folder_path.exists():
                files = list(folder_path.glob('*.*'))
                count = len(files)
                total_images += count
                size = sum(f.stat().st_size for f in files) if files else 0
                size_mb = size / (1024 * 1024)
                self.stdout.write(f'  {folder}: {count} files ({size_mb:.2f} MB)')
                if files[:3]:
                    self.stdout.write(f'    Sample: {", ".join(f.name for f in files[:3])}')
            else:
                self.stdout.write(f'  {folder}: NOT FOUND (creating...)')
                folder_path.mkdir(parents=True, exist_ok=True)

        # Check animated
        animated_path = media_root / 'animated_cp'
        if animated_path.exists():
            files = list(animated_path.glob('*.*'))
            count = len(files)
            size = sum(f.stat().st_size for f in files) if files else 0
            size_mb = size / (1024 * 1024)
            self.stdout.write(f'\nAnimated: {count} files ({size_mb:.2f} MB)')
            if files[:3]:
                self.stdout.write(f'    Sample: {", ".join(f.name for f in files[:3])}')
        else:
            self.stdout.write(f'\nAnimated: NOT FOUND (creating...)')
            animated_path.mkdir(parents=True, exist_ok=True)

        # Disk space
        try:
            import shutil
            total, used, free = shutil.disk_usage(media_root)
            self.stdout.write(f'\nDisk Space:')
            self.stdout.write(f'  Total: {total / (1024 ** 3):.2f} GB')
            self.stdout.write(f'  Used: {used / (1024 ** 3):.2f} GB')
            self.stdout.write(f'  Free: {free / (1024 ** 3):.2f} GB')
        except Exception as e:
            self.stdout.write(f'\nCould not get disk space: {e}')

        # Database check
        from core.models import Postcard
        total_postcards = Postcard.objects.count()
        postcards_with_images = Postcard.objects.filter(has_images=True).count()

        self.stdout.write(f'\nDatabase:')
        self.stdout.write(f'  Total postcards: {total_postcards}')
        self.stdout.write(f'  With has_images=True: {postcards_with_images}')

        # Test a specific postcard
        if total_postcards > 0:
            sample = Postcard.objects.first()
            self.stdout.write(f'\nSample postcard test (#{sample.number}):')
            self.stdout.write(f'  Padded number: {sample.get_padded_number()}')
            self.stdout.write(f'  Vignette URL: {sample.get_vignette_url() or "NOT FOUND"}')
            self.stdout.write(f'  Grande URL: {sample.get_grande_url() or "NOT FOUND"}')
            self.stdout.write(f'  Animated URLs: {sample.get_animated_urls() or "NONE"}')

        self.stdout.write(f"\n{'=' * 60}\n")

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
            self.stdout.write(f'  Created: {d}')
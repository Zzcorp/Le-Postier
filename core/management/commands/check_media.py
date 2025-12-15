# core/management/commands/check_media.py
from django.core.management.base import BaseCommand
from django.conf import settings
from pathlib import Path


class Command(BaseCommand):
    help = 'Check media files status'

    def handle(self, *args, **options):
        media_root = Path(settings.MEDIA_ROOT)

        self.stdout.write(f'\nMedia Root: {media_root}')
        self.stdout.write(f'Exists: {media_root.exists()}')

        if not media_root.exists():
            self.stdout.write(self.style.ERROR('Media directory does not exist!'))
            return

        # Check postcards folders
        self.stdout.write('\nPostcards Images:')
        for folder in ['Vignette', 'Grande', 'Dos', 'Zoom']:
            folder_path = media_root / 'postcards' / folder
            if folder_path.exists():
                count = len(list(folder_path.glob('*.*')))
                size = sum(f.stat().st_size for f in folder_path.glob('*.*'))
                size_mb = size / (1024 * 1024)
                self.stdout.write(f'  {folder}: {count} files ({size_mb:.2f} MB)')
            else:
                self.stdout.write(f'  {folder}: Not found')

        # Check animated
        animated_path = media_root / 'animated_cp'
        if animated_path.exists():
            count = len(list(animated_path.glob('*.*')))
            size = sum(f.stat().st_size for f in animated_path.glob('*.*'))
            size_mb = size / (1024 * 1024)
            self.stdout.write(f'\nAnimated: {count} files ({size_mb:.2f} MB)')

        # Disk space
        import shutil
        total, used, free = shutil.disk_usage(media_root)
        self.stdout.write(f'\nDisk Space:')
        self.stdout.write(f'  Total: {total / (1024 ** 3):.2f} GB')
        self.stdout.write(f'  Used: {used / (1024 ** 3):.2f} GB')
        self.stdout.write(f'  Free: {free / (1024 ** 3):.2f} GB')
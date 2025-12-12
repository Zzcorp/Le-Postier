# core/management/commands/scan_media.py
"""
Management command to scan and report on media files.
"""

import os
from pathlib import Path
from django.core.management.base import BaseCommand
from django.conf import settings
from core.models import Postcard


class Command(BaseCommand):
    help = 'Scan media directory and report statistics'

    def add_arguments(self, parser):
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed file listing'
        )

    def handle(self, *args, **options):
        media_root = Path(settings.MEDIA_ROOT)
        verbose = options['verbose']

        self.stdout.write(f'\n{"=" * 60}')
        self.stdout.write(f'MEDIA SCAN REPORT')
        self.stdout.write(f'{"=" * 60}')
        self.stdout.write(f'Media Root: {media_root}')
        self.stdout.write(f'Exists: {media_root.exists()}')

        if not media_root.exists():
            self.stdout.write(self.style.ERROR('Media root does not exist!'))
            return

        # Scan postcard directories
        postcard_dirs = ['Vignette', 'Grande', 'Dos', 'Zoom']
        postcard_base = media_root / 'postcards'

        self.stdout.write(f'\n{"─" * 60}')
        self.stdout.write('POSTCARD IMAGES')
        self.stdout.write(f'{"─" * 60}')

        total_images = 0
        for dir_name in postcard_dirs:
            dir_path = postcard_base / dir_name
            if dir_path.exists():
                count = len(list(dir_path.glob('*.*')))
                total_images += count
                self.stdout.write(f'  {dir_name}: {count} files')

                if verbose and count > 0:
                    for f in sorted(dir_path.iterdir())[:5]:
                        self.stdout.write(f'    - {f.name}')
                    if count > 5:
                        self.stdout.write(f'    ... and {count - 5} more')
            else:
                self.stdout.write(f'  {dir_name}: (not found)')

        self.stdout.write(f'  Total images: {total_images}')

        # Scan animated directory
        self.stdout.write(f'\n{"─" * 60}')
        self.stdout.write('ANIMATED POSTCARDS')
        self.stdout.write(f'{"─" * 60}')

        animated_dir = media_root / 'animated_cp'
        if animated_dir.exists():
            video_count = len(list(animated_dir.glob('*.mp4'))) + len(list(animated_dir.glob('*.webm')))
            self.stdout.write(f'  Videos: {video_count} files')

            if verbose and video_count > 0:
                for f in sorted(animated_dir.iterdir())[:5]:
                    size_mb = f.stat().st_size / (1024 * 1024)
                    self.stdout.write(f'    - {f.name} ({size_mb:.1f} MB)')
                if video_count > 5:
                    self.stdout.write(f'    ... and {video_count - 5} more')
        else:
            self.stdout.write(f'  Animated directory: (not found)')

        # Database statistics
        self.stdout.write(f'\n{"─" * 60}')
        self.stdout.write('DATABASE STATISTICS')
        self.stdout.write(f'{"─" * 60}')

        total_postcards = Postcard.objects.count()
        with_images = Postcard.objects.filter(has_images=True).count()
        with_animation = Postcard.objects.filter(has_animation=True).count()

        self.stdout.write(f'  Total postcards in DB: {total_postcards}')
        self.stdout.write(f'  With images: {with_images}')
        self.stdout.write(f'  With animations: {with_animation}')

        # Disk space
        self.stdout.write(f'\n{"─" * 60}')
        self.stdout.write('DISK USAGE')
        self.stdout.write(f'{"─" * 60}')

        total_size = 0
        for root, dirs, files in os.walk(media_root):
            for f in files:
                total_size += os.path.getsize(os.path.join(root, f))

        size_mb = total_size / (1024 * 1024)
        size_gb = total_size / (1024 * 1024 * 1024)

        self.stdout.write(f'  Total size: {size_mb:.1f} MB ({size_gb:.2f} GB)')

        self.stdout.write(f'\n{"=" * 60}\n')
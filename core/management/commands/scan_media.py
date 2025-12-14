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
        parser.add_argument(
            '--create-entries',
            action='store_true',
            help='Create database entries for found images'
        )

    def handle(self, *args, **options):
        media_root = Path(settings.MEDIA_ROOT)
        verbose = options['verbose']
        create_entries = options.get('create_entries', False)

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
        found_numbers = set()

        for dir_name in postcard_dirs:
            dir_path = postcard_base / dir_name
            if dir_path.exists():
                files = list(dir_path.glob('*.*'))
                count = len(files)
                total_images += count
                self.stdout.write(f'  {dir_name}: {count} files')

                # Collect postcard numbers from filenames
                for f in files:
                    # Extract number from filename (e.g., 000001.jpg -> 000001)
                    stem = f.stem
                    if stem.isdigit():
                        found_numbers.add(stem.zfill(6))

                if verbose and count > 0:
                    for f in sorted(files)[:5]:
                        self.stdout.write(f'    - {f.name}')
                    if count > 5:
                        self.stdout.write(f'    ... and {count - 5} more')
            else:
                self.stdout.write(f'  {dir_name}: (not found)')

        self.stdout.write(f'  Total images: {total_images}')
        self.stdout.write(f'  Unique postcard numbers found: {len(found_numbers)}')

        # Scan animated directory
        self.stdout.write(f'\n{"─" * 60}')
        self.stdout.write('ANIMATED POSTCARDS')
        self.stdout.write(f'{"─" * 60}')

        animated_dir = media_root / 'animated_cp'
        animated_numbers = set()

        if animated_dir.exists():
            video_files = list(animated_dir.glob('*.mp4')) + list(animated_dir.glob('*.webm'))
            video_count = len(video_files)
            self.stdout.write(f'  Videos: {video_count} files')

            for f in video_files:
                stem = f.stem.split('_')[0]  # Handle 000001_0.mp4 format
                if stem.isdigit():
                    animated_numbers.add(stem.zfill(6))

            if verbose and video_count > 0:
                for f in sorted(video_files)[:5]:
                    size_mb = f.stat().st_size / (1024 * 1024)
                    self.stdout.write(f'    - {f.name} ({size_mb:.1f} MB)')
                if video_count > 5:
                    self.stdout.write(f'    ... and {video_count - 5} more')
        else:
            self.stdout.write(f'  Animated directory: (not found)')

        # Create database entries if requested
        if create_entries and found_numbers:
            self.stdout.write(f'\n{"─" * 60}')
            self.stdout.write('CREATING DATABASE ENTRIES')
            self.stdout.write(f'{"─" * 60}')

            created = 0
            updated = 0

            for number in sorted(found_numbers):
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

                # Update flags
                has_anim = number in animated_numbers
                needs_update = False

                if not postcard.has_images:
                    postcard.has_images = True
                    needs_update = True

                # Check if has_animation field exists
                if hasattr(postcard, 'has_animation'):
                    if postcard.has_animation != has_anim:
                        postcard.has_animation = has_anim
                        needs_update = True

                if needs_update and not was_created:
                    postcard.save()
                    updated += 1

                if was_created:
                    created += 1

            self.stdout.write(self.style.SUCCESS(f'  Created: {created} postcards'))
            self.stdout.write(f'  Updated: {updated} postcards')

        # Database statistics
        self.stdout.write(f'\n{"─" * 60}')
        self.stdout.write('DATABASE STATISTICS')
        self.stdout.write(f'{"─" * 60}')

        total_postcards = Postcard.objects.count()

        # Safe query for has_images
        try:
            with_images = Postcard.objects.filter(has_images=True).count()
        except Exception:
            with_images = 0

        # Safe query for has_animation (field might not exist)
        try:
            with_animation = Postcard.objects.filter(has_animation=True).count()
        except Exception:
            with_animation = 0
            self.stdout.write(self.style.WARNING('  Note: has_animation field not in database'))

        self.stdout.write(f'  Total postcards in DB: {total_postcards}')
        self.stdout.write(f'  With images flag: {with_images}')
        self.stdout.write(f'  With animations flag: {with_animation}')

        # Disk space
        self.stdout.write(f'\n{"─" * 60}')
        self.stdout.write('DISK USAGE')
        self.stdout.write(f'{"─" * 60}')

        total_size = 0
        for root, dirs, files in os.walk(media_root):
            for f in files:
                try:
                    total_size += os.path.getsize(os.path.join(root, f))
                except OSError:
                    pass

        size_mb = total_size / (1024 * 1024)
        size_gb = total_size / (1024 * 1024 * 1024)

        self.stdout.write(f'  Total size: {size_mb:.1f} MB ({size_gb:.2f} GB)')

        self.stdout.write(f'\n{"=" * 60}')

        if total_postcards == 0 and found_numbers:
            self.stdout.write(self.style.WARNING(
                f'\n⚠️  You have {len(found_numbers)} images but 0 database entries!'
            ))
            self.stdout.write(self.style.WARNING(
                '   Run: python manage.py scan_media --create-entries'
            ))

        self.stdout.write('')
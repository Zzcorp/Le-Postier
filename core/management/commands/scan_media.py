# core/management/commands/scan_media.py
"""
Scan media folder and show detailed statistics about available files.
"""

from django.core.management.base import BaseCommand
from django.conf import settings
from pathlib import Path


class Command(BaseCommand):
    help = 'Scan media folder and display statistics'

    def handle(self, *args, **options):
        media_root = Path(settings.MEDIA_ROOT)

        self.stdout.write('=' * 70)
        self.stdout.write('MEDIA FOLDER SCAN')
        self.stdout.write(f'Media Root: {media_root}')
        self.stdout.write('=' * 70)

        if not media_root.exists():
            self.stdout.write(self.style.ERROR(f'\n❌ Media root does not exist: {media_root}'))
            return

        # Scan postcards folder
        postcards_dir = media_root / 'postcards'

        self.stdout.write('\n📁 POSTCARDS FOLDER:')

        for folder in ['Vignette', 'Grande', 'Dos', 'Zoom']:
            folder_path = postcards_dir / folder
            if folder_path.exists():
                files = list(folder_path.glob('*.[jJpP][pPnN][gG]*'))
                total_size = sum(f.stat().st_size for f in files) / (1024 * 1024)  # MB
                self.stdout.write(f'   {folder}: {len(files)} files ({total_size:.1f} MB)')

                # Show sample files
                if files:
                    samples = sorted([f.name for f in files[:5]])
                    self.stdout.write(f'      Sample: {", ".join(samples)}...')
            else:
                self.stdout.write(f'   {folder}: ❌ Not found')

        # Scan animated folder
        animated_dir = media_root / 'animated_cp'

        self.stdout.write('\n📁 ANIMATED FOLDER:')

        if animated_dir.exists():
            videos = list(animated_dir.glob('*.[mMwW][pP4eEbBmM]*'))
            total_size = sum(f.stat().st_size for f in videos) / (1024 * 1024)  # MB
            self.stdout.write(f'   Videos: {len(videos)} files ({total_size:.1f} MB)')

            # Count unique postcards with videos
            unique_postcards = set()
            for v in videos:
                name = v.stem
                if '_' in name:
                    name = name.rsplit('_', 1)[0]
                unique_postcards.add(name)

            self.stdout.write(f'   Unique postcards with animation: {len(unique_postcards)}')

            # Show sample files
            if videos:
                samples = sorted([f.name for f in videos[:5]])
                self.stdout.write(f'   Sample: {", ".join(samples)}...')
        else:
            self.stdout.write(f'   ❌ Not found')

        # Scan signatures folder
        signatures_dir = media_root / 'signatures'

        self.stdout.write('\n📁 SIGNATURES FOLDER:')

        if signatures_dir.exists():
            sigs = list(signatures_dir.glob('*'))
            self.stdout.write(f'   Files: {len(sigs)}')
        else:
            self.stdout.write(f'   ❌ Not found (will be created)')

        self.stdout.write('\n' + '=' * 70)
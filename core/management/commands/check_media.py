# core/management/commands/check_media.py
from django.core.management.base import BaseCommand
from django.conf import settings
from core.models import Postcard
from pathlib import Path
import os


class Command(BaseCommand):
    help = 'Check media files and their relationship to database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--detailed',
            action='store_true',
            help='Show detailed file listing'
        )
        parser.add_argument(
            '--find-orphans',
            action='store_true',
            help='Find files without matching database entries'
        )
        parser.add_argument(
            '--find-missing',
            action='store_true',
            help='Find database entries without files'
        )

    def handle(self, *args, **options):
        detailed = options['detailed']
        find_orphans = options['find_orphans']
        find_missing = options['find_missing']

        # Determine media root
        is_render = os.environ.get('RENDER', 'false').lower() == 'true'
        persistent_exists = Path('/var/data').exists()

        if is_render or persistent_exists:
            media_root = Path('/var/data/media')
        else:
            media_root = Path(settings.MEDIA_ROOT)

        self.stdout.write('=' * 60)
        self.stdout.write('MEDIA CHECK REPORT')
        self.stdout.write('=' * 60)
        self.stdout.write(f'RENDER env: {is_render}')
        self.stdout.write(f'/var/data exists: {persistent_exists}')
        self.stdout.write(f'Media root: {media_root}')
        self.stdout.write(f'Media root exists: {media_root.exists()}')
        self.stdout.write('')

        if not media_root.exists():
            self.stderr.write(self.style.ERROR('Media root does not exist!'))
            return

        # Check each directory
        directories = {
            'Vignette': media_root / 'postcards' / 'Vignette',
            'Grande': media_root / 'postcards' / 'Grande',
            'Dos': media_root / 'postcards' / 'Dos',
            'Zoom': media_root / 'postcards' / 'Zoom',
            'Animated': media_root / 'animated_cp',
            'Signatures': media_root / 'signatures',
            'Covers': media_root / 'covers',
        }

        file_counts = {}
        all_numbers = {}

        for name, path in directories.items():
            if path.exists():
                files = list(path.glob('*.*'))
                file_counts[name] = len(files)
                self.stdout.write(self.style.SUCCESS(f'{name}: {len(files)} files'))

                if detailed and files:
                    self.stdout.write(f'  Sample files:')
                    for f in sorted(files, key=lambda x: x.name)[:10]:
                        size_kb = f.stat().st_size / 1024
                        self.stdout.write(f'    - {f.name} ({size_kb:.1f} KB)')
                    if len(files) > 10:
                        self.stdout.write(f'    ... and {len(files) - 10} more')

                # Collect numbers for orphan/missing check
                if name in ['Vignette', 'Grande', 'Animated']:
                    for f in files:
                        stem = f.stem.split('_')[0]  # Handle _0, _1 suffixes
                        try:
                            num = int(stem)
                            all_numbers[str(num)] = name
                            all_numbers[str(num).zfill(6)] = name
                        except ValueError:
                            all_numbers[stem] = name
            else:
                file_counts[name] = 0
                self.stdout.write(self.style.WARNING(f'{name}: NOT FOUND'))

        # Database stats
        self.stdout.write('')
        self.stdout.write('Database:')
        total_postcards = Postcard.objects.count()
        with_images = Postcard.objects.filter(has_images=True).count()
        without_images = Postcard.objects.filter(has_images=False).count()

        self.stdout.write(f'  Total postcards: {total_postcards}')
        self.stdout.write(f'  With images flag: {with_images}')
        self.stdout.write(f'  Without images flag: {without_images}')

        # Find orphans (files without DB entries)
        if find_orphans and all_numbers:
            self.stdout.write('')
            self.stdout.write('Orphan Analysis (files without DB entries):')

            db_numbers = set()
            for p in Postcard.objects.values_list('number', flat=True):
                db_numbers.add(str(p).strip())
                try:
                    db_numbers.add(str(int(''.join(filter(str.isdigit, str(p))))))
                except:
                    pass

            orphan_count = 0
            orphans = []
            for file_num in all_numbers.keys():
                if file_num not in db_numbers:
                    orphan_count += 1
                    orphans.append(file_num)

            self.stdout.write(f'  Orphan files: {orphan_count}')
            if orphans and detailed:
                for o in orphans[:20]:
                    self.stdout.write(f'    - {o}')
                if len(orphans) > 20:
                    self.stdout.write(f'    ... and {len(orphans) - 20} more')

        # Find missing (DB entries without files)
        if find_missing:
            self.stdout.write('')
            self.stdout.write('Missing Analysis (DB entries without Vignette):')

            vignette_path = directories['Vignette']
            if vignette_path.exists():
                vignette_numbers = set()
                for f in vignette_path.glob('*.*'):
                    stem = f.stem.lower()
                    vignette_numbers.add(stem)
                    try:
                        vignette_numbers.add(str(int(stem)))
                    except:
                        pass

                missing_count = 0
                missing = []
                for p in Postcard.objects.filter(has_images=True):
                    number = str(p.number).strip().lower()
                    padded = p.get_padded_number().lower()

                    if number not in vignette_numbers and padded not in vignette_numbers:
                        missing_count += 1
                        missing.append(p.number)

                self.stdout.write(f'  DB entries with has_images=True but no Vignette: {missing_count}')
                if missing and detailed:
                    for m in missing[:20]:
                        self.stdout.write(f'    - {m}')
                    if len(missing) > 20:
                        self.stdout.write(f'    ... and {len(missing) - 20} more')

        # Disk usage
        self.stdout.write('')
        self.stdout.write('Disk Usage:')

        total_size = 0
        for name, path in directories.items():
            if path.exists():
                size = sum(f.stat().st_size for f in path.glob('*.*'))
                total_size += size
                self.stdout.write(f'  {name}: {size / (1024 * 1024):.2f} MB')

        self.stdout.write(f'  TOTAL: {total_size / (1024 * 1024):.2f} MB')

        self.stdout.write('')
        self.stdout.write('=' * 60)
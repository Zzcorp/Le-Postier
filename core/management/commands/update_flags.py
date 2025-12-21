# core/management/commands/update_flags.py
from django.core.management.base import BaseCommand
from django.conf import settings
from core.models import Postcard
from pathlib import Path
import os


class Command(BaseCommand):
    help = 'Update has_images flags for all postcards based on actual files on disk'

    def add_arguments(self, parser):
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed output'
        )
        parser.add_argument(
            '--check-only',
            action='store_true',
            help='Only check and report, do not update'
        )

    def handle(self, *args, **options):
        verbose = options['verbose']
        check_only = options['check_only']

        # Determine media root - CRITICAL for Render
        is_render = os.environ.get('RENDER', 'false').lower() == 'true'
        persistent_exists = Path('/var/data').exists()

        if is_render or persistent_exists:
            media_root = Path('/var/data/media')
        else:
            media_root = Path(settings.MEDIA_ROOT)

        self.stdout.write(f'Environment: RENDER={is_render}, /var/data exists={persistent_exists}')
        self.stdout.write(f'Using media root: {media_root}')
        self.stdout.write(f'Media root exists: {media_root.exists()}')

        # Define directories
        vignette_dir = media_root / 'postcards' / 'Vignette'
        grande_dir = media_root / 'postcards' / 'Grande'
        dos_dir = media_root / 'postcards' / 'Dos'
        zoom_dir = media_root / 'postcards' / 'Zoom'
        animated_dir = media_root / 'animated_cp'

        # Report directory status
        self.stdout.write('')
        self.stdout.write('Directory Status:')
        for name, dir_path in [
            ('Vignette', vignette_dir),
            ('Grande', grande_dir),
            ('Dos', dos_dir),
            ('Zoom', zoom_dir),
            ('Animated', animated_dir)
        ]:
            if dir_path.exists():
                files = list(dir_path.glob('*.*'))
                self.stdout.write(self.style.SUCCESS(f'  {name}: {len(files)} files'))
                if verbose and files:
                    for f in files[:5]:
                        self.stdout.write(f'    - {f.name}')
                    if len(files) > 5:
                        self.stdout.write(f'    ... and {len(files) - 5} more')
            else:
                self.stdout.write(self.style.WARNING(f'  {name}: NOT FOUND at {dir_path}'))

        # Build file indexes (stem -> filename mapping)
        # Handle both padded (000001) and unpadded (1) numbers
        self.stdout.write('')
        self.stdout.write('Building file indexes...')

        def build_index(directory):
            """Build index mapping both padded and unpadded numbers to files"""
            index = {}
            if not directory.exists():
                return index

            for f in directory.glob('*.*'):
                if f.suffix.lower() in ['.jpg', '.jpeg', '.png', '.gif', '.mp4', '.webm']:
                    stem = f.stem.lower()
                    # Store by exact stem
                    index[stem] = f

                    # Also store by numeric value (removes leading zeros)
                    try:
                        # Handle files like "000001_0" for multiple animations
                        base = stem.split('_')[0]
                        num = int(base)
                        index[str(num)] = f
                        index[str(num).zfill(6)] = f
                    except ValueError:
                        pass

            return index

        vignette_index = build_index(vignette_dir)
        grande_index = build_index(grande_dir)
        animated_index = build_index(animated_dir)

        self.stdout.write(f'Vignette index: {len(vignette_index)} entries')
        self.stdout.write(f'Grande index: {len(grande_index)} entries')
        self.stdout.write(f'Animated index: {len(animated_index)} entries')

        # Update postcards
        self.stdout.write('')
        self.stdout.write('Updating postcards...')

        postcards = Postcard.objects.all()
        total = postcards.count()

        updated_to_has_images = 0
        updated_to_no_images = 0
        already_correct = 0
        with_animation = 0

        updates = []

        for i, postcard in enumerate(postcards, 1):
            # Get different number formats
            number = str(postcard.number).strip()
            number_lower = number.lower()

            # Get padded number
            try:
                num_digits = ''.join(filter(str.isdigit, number))
                if num_digits:
                    padded = num_digits.zfill(6)
                else:
                    padded = number.zfill(6)
            except:
                padded = number.zfill(6)

            padded_lower = padded.lower()

            # Check for vignette (primary indicator of has_images)
            has_vignette = (
                    number_lower in vignette_index or
                    padded_lower in vignette_index or
                    number in vignette_index or
                    padded in vignette_index
            )

            # Also check grande as fallback
            has_grande = (
                    number_lower in grande_index or
                    padded_lower in grande_index or
                    number in grande_index or
                    padded in grande_index
            )

            # Has images if either vignette or grande exists
            should_have_images = has_vignette or has_grande

            # Check animation
            has_animation = (
                    number_lower in animated_index or
                    padded_lower in animated_index or
                    number in animated_index or
                    padded in animated_index
            )

            if has_animation:
                with_animation += 1

            # Compare with current flag
            if postcard.has_images != should_have_images:
                if not check_only:
                    postcard.has_images = should_have_images
                    updates.append(postcard)

                if should_have_images:
                    updated_to_has_images += 1
                    if verbose:
                        self.stdout.write(f'  + {number}: now has images')
                else:
                    updated_to_no_images += 1
                    if verbose:
                        self.stdout.write(f'  - {number}: no longer has images')
            else:
                already_correct += 1

            if i % 1000 == 0:
                self.stdout.write(f'Processed {i}/{total}...')

        # Bulk update
        if updates and not check_only:
            Postcard.objects.bulk_update(updates, ['has_images'], batch_size=500)
            self.stdout.write(f'Saved {len(updates)} updates')

        # Final report
        self.stdout.write('')
        self.stdout.write('=' * 60)
        self.stdout.write('UPDATE FLAGS SUMMARY')
        self.stdout.write('=' * 60)
        self.stdout.write(f'Total postcards: {total}')
        self.stdout.write(f'Already correct: {already_correct}')
        self.stdout.write(self.style.SUCCESS(f'Updated to has_images=True: {updated_to_has_images}'))
        self.stdout.write(self.style.WARNING(f'Updated to has_images=False: {updated_to_no_images}'))
        self.stdout.write(f'With animation files: {with_animation}')
        self.stdout.write('')
        self.stdout.write(f'Final counts:')
        self.stdout.write(f'  With images: {Postcard.objects.filter(has_images=True).count()}')
        self.stdout.write(f'  Without images: {Postcard.objects.filter(has_images=False).count()}')

        if check_only:
            self.stdout.write('')
            self.stdout.write(self.style.WARNING('CHECK ONLY mode - no changes were saved'))
            self.stdout.write('Run without --check-only to apply changes')
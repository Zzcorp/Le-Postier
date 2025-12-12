# core/management/commands/import_postcards_csv.py
"""
Management command to import postcards from a CSV file.
Creates postcard database entries from CSV data.
"""

import csv
import os
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from core.models import Postcard


class Command(BaseCommand):
    help = 'Import postcards from a CSV file or create from existing images'

    def add_arguments(self, parser):
        parser.add_argument(
            '--csv',
            type=str,
            help='Path to CSV file containing postcard data'
        )
        parser.add_argument(
            '--create-from-images',
            action='store_true',
            help='Create postcard entries from existing image files in media folder'
        )
        parser.add_argument(
            '--update-flags',
            action='store_true',
            help='Update has_images and has_animation flags for existing postcards'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be imported without making changes'
        )

    def handle(self, *args, **options):
        if options['csv']:
            self.import_from_csv(options['csv'], options['dry_run'])
        elif options['create_from_images']:
            self.create_from_images(options['dry_run'])
        elif options['update_flags']:
            self.update_flags()
        else:
            self.stdout.write(self.style.WARNING(
                'Please specify --csv <path>, --create-from-images, or --update-flags'
            ))

    def import_from_csv(self, csv_path, dry_run=False):
        """Import postcards from a CSV file."""
        if not os.path.exists(csv_path):
            raise CommandError(f'CSV file not found: {csv_path}')

        self.stdout.write(f'Reading CSV file: {csv_path}')

        created_count = 0
        updated_count = 0
        error_count = 0

        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            # Try to detect delimiter
            sample = f.read(1024)
            f.seek(0)

            # Check for common delimiters
            if ';' in sample:
                delimiter = ';'
            elif '\t' in sample:
                delimiter = '\t'
            else:
                delimiter = ','

            reader = csv.DictReader(f, delimiter=delimiter)

            # Normalize field names (handle different column name formats)
            if reader.fieldnames:
                self.stdout.write(f'Found columns: {reader.fieldnames}')

            for row in reader:
                try:
                    # Try different possible column names
                    number = (
                            row.get('number') or
                            row.get('Number') or
                            row.get('numero') or
                            row.get('Numero') or
                            row.get('N°') or
                            row.get('id') or
                            ''
                    ).strip()

                    title = (
                            row.get('title') or
                            row.get('Title') or
                            row.get('titre') or
                            row.get('Titre') or
                            row.get('name') or
                            row.get('Name') or
                            ''
                    ).strip()

                    keywords = (
                            row.get('keywords') or
                            row.get('Keywords') or
                            row.get('mots_cles') or
                            row.get('Mots_cles') or
                            row.get('tags') or
                            ''
                    ).strip()

                    description = (
                            row.get('description') or
                            row.get('Description') or
                            ''
                    ).strip()

                    rarity = (
                            row.get('rarity') or
                            row.get('Rarity') or
                            row.get('rarete') or
                            'common'
                    ).strip().lower()

                    # Validate rarity
                    if rarity not in ['common', 'rare', 'very_rare']:
                        rarity = 'common'

                    if not number:
                        self.stdout.write(self.style.WARNING(f'Skipping row without number: {row}'))
                        continue

                    # Pad number to 6 digits if numeric
                    if number.isdigit():
                        number = number.zfill(6)

                    if dry_run:
                        self.stdout.write(f'Would create/update: {number} - {title[:50]}')
                        continue

                    postcard, created = Postcard.objects.update_or_create(
                        number=number,
                        defaults={
                            'title': title or f'Carte postale {number}',
                            'keywords': keywords,
                            'description': description,
                            'rarity': rarity,
                        }
                    )

                    # Update image flags
                    postcard.has_images = postcard.check_has_vignette()
                    postcard.has_animation = postcard.check_has_animation()
                    postcard.save(update_fields=['has_images', 'has_animation'])

                    if created:
                        created_count += 1
                    else:
                        updated_count += 1

                except Exception as e:
                    error_count += 1
                    self.stdout.write(self.style.ERROR(f'Error processing row: {e}'))
                    continue

        if dry_run:
            self.stdout.write(self.style.SUCCESS('Dry run complete - no changes made'))
        else:
            self.stdout.write(self.style.SUCCESS(
                f'Import complete: {created_count} created, {updated_count} updated, {error_count} errors'
            ))

    def create_from_images(self, dry_run=False):
        """Create postcard entries from existing image files."""
        media_root = Path(settings.MEDIA_ROOT)
        vignette_dir = media_root / 'postcards' / 'Vignette'

        if not vignette_dir.exists():
            self.stdout.write(self.style.WARNING(f'Vignette directory not found: {vignette_dir}'))
            self.stdout.write('Creating from all image directories...')

            # Try other directories
            for dir_name in ['Grande', 'Dos', 'Zoom']:
                alt_dir = media_root / 'postcards' / dir_name
                if alt_dir.exists():
                    vignette_dir = alt_dir
                    break

        if not vignette_dir.exists():
            raise CommandError('No postcard image directories found')

        created_count = 0

        # Get all image files
        image_extensions = {'.jpg', '.jpeg', '.png', '.gif'}

        for file_path in vignette_dir.iterdir():
            if file_path.suffix.lower() not in image_extensions:
                continue

            # Extract number from filename (e.g., 000001.jpg -> 000001)
            number = file_path.stem

            # Skip if not a valid number pattern
            if not number.replace('_', '').isdigit():
                continue

            if dry_run:
                self.stdout.write(f'Would create: {number}')
                continue

            postcard, created = Postcard.objects.get_or_create(
                number=number,
                defaults={
                    'title': f'Carte postale {number}',
                    'keywords': '',
                    'description': '',
                    'rarity': 'common',
                }
            )

            # Update image flags
            postcard.has_images = postcard.check_has_vignette()
            postcard.has_animation = postcard.check_has_animation()
            postcard.save(update_fields=['has_images', 'has_animation'])

            if created:
                created_count += 1

        if dry_run:
            self.stdout.write(self.style.SUCCESS('Dry run complete'))
        else:
            self.stdout.write(self.style.SUCCESS(f'Created {created_count} postcards from images'))

    def update_flags(self):
        """Update has_images and has_animation flags for all postcards."""
        postcards = Postcard.objects.all()
        total = postcards.count()

        self.stdout.write(f'Updating flags for {total} postcards...')

        updated = 0
        with_images = 0
        with_animation = 0

        for postcard in postcards:
            old_images = postcard.has_images
            old_animation = postcard.has_animation

            postcard.has_images = postcard.check_has_vignette()
            postcard.has_animation = postcard.check_has_animation()

            if old_images != postcard.has_images or old_animation != postcard.has_animation:
                postcard.save(update_fields=['has_images', 'has_animation'])
                updated += 1

            if postcard.has_images:
                with_images += 1
            if postcard.has_animation:
                with_animation += 1

        self.stdout.write(self.style.SUCCESS(
            f'Updated {updated} postcards. '
            f'{with_images} have images, {with_animation} have animations.'
        ))
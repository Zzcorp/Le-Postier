# core/management/commands/import_postcards_csv.py
"""
Import postcards from CSV file
Usage: python manage.py import_postcards_csv /path/to/postcards.csv
"""

import csv
from django.core.management.base import BaseCommand
from core.models import Postcard


class Command(BaseCommand):
    help = 'Import postcards from CSV file'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help='Path to CSV file')
        parser.add_argument('--encoding', type=str, default='utf-8', help='CSV encoding')
        parser.add_argument('--delimiter', type=str, default=',', help='CSV delimiter')
        parser.add_argument('--update-existing', action='store_true', help='Update existing postcards')
        parser.add_argument('--dry-run', action='store_true', help='Test without saving')

    def handle(self, *args, **options):
        csv_file = options['csv_file']
        encoding = options['encoding']
        delimiter = options['delimiter']
        update_existing = options['update_existing']
        dry_run = options['dry_run']

        self.stdout.write(f'Reading CSV from: {csv_file}')

        created = 0
        updated = 0
        skipped = 0
        errors = 0

        try:
            with open(csv_file, 'r', encoding=encoding) as f:
                # Try to detect encoding and delimiter
                sample = f.read(1024)
                f.seek(0)

                # Auto-detect delimiter
                if ';' in sample and ',' not in sample.split('\n')[0]:
                    delimiter = ';'

                reader = csv.DictReader(f, delimiter=delimiter)

                # Show detected columns
                self.stdout.write(f'Detected columns: {", ".join(reader.fieldnames)}')

                for i, row in enumerate(reader, 1):
                    try:
                        result = self.process_row(row, update_existing, dry_run)
                        if result == 'created':
                            created += 1
                        elif result == 'updated':
                            updated += 1
                        elif result == 'skipped':
                            skipped += 1

                        if i % 100 == 0:
                            self.stdout.write(f'  Progress: {i} rows processed...')

                    except Exception as e:
                        errors += 1
                        if errors < 10:  # Show first 10 errors only
                            self.stdout.write(self.style.WARNING(
                                f'  Row {i} error: {e} | Data: {row}'
                            ))

        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f'File not found: {csv_file}'))
            return
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error reading CSV: {e}'))
            import traceback
            traceback.print_exc()
            return

        # Summary
        self.stdout.write('\n' + '=' * 60)
        if dry_run:
            self.stdout.write(self.style.WARNING('[DRY RUN - No changes made]'))
        self.stdout.write(self.style.SUCCESS(
            f'Created: {created} | Updated: {updated} | Skipped: {skipped} | Errors: {errors}'
        ))
        self.stdout.write('=' * 60)

    def process_row(self, row, update_existing, dry_run):
        """Process a single CSV row"""
        # Map common CSV column names to model fields
        number = (
                row.get('number') or
                row.get('Number') or
                row.get('numero') or
                row.get('Numero') or
                row.get('id') or
                row.get('ID')
        )

        title = (
                row.get('title') or
                row.get('Title') or
                row.get('titre') or
                row.get('Titre') or
                row.get('name') or
                row.get('Name')
        )

        if not number or not title:
            # If no number/title, try to use first and second columns
            cols = list(row.values())
            if len(cols) >= 2:
                number = cols[0]
                title = cols[1]
            else:
                raise ValueError("Missing number and title")

        # Clean number
        number = str(number).strip()
        title = str(title).strip()

        # Get other fields with fallbacks
        description = (
                row.get('description') or
                row.get('Description') or
                row.get('desc') or
                ''
        )

        keywords = (
                row.get('keywords') or
                row.get('Keywords') or
                row.get('mots_cles') or
                row.get('tags') or
                ''
        )

        rarity_str = (
                row.get('rarity') or
                row.get('Rarity') or
                row.get('rarete') or
                'common'
        )

        # Map rarity
        rarity_map = {
            'commune': 'common',
            'common': 'common',
            'c': 'common',
            'rare': 'rare',
            'r': 'rare',
            'tres_rare': 'very_rare',
            'très_rare': 'very_rare',
            'very_rare': 'very_rare',
            'very rare': 'very_rare',
            'vr': 'very_rare',
        }
        rarity = rarity_map.get(str(rarity_str).lower().strip(), 'common')

        if dry_run:
            self.stdout.write(f'[DRY RUN] Would create/update: {number} - {title}')
            return 'created'

        # Create or update
        try:
            postcard, created = Postcard.objects.update_or_create(
                number=number,
                defaults={
                    'title': title,
                    'description': description.strip(),
                    'keywords': keywords.strip(),
                    'rarity': rarity,
                }
            )

            if created:
                return 'created'
            elif update_existing:
                return 'updated'
            else:
                return 'skipped'

        except Exception as e:
            raise ValueError(f"Database error: {e}")
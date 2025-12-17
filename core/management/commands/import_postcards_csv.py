# core/management/commands/import_postcards_csv.py
"""
Management command to import postcards from CSV file.
Run with: python manage.py import_postcards_csv data.csv
"""

from django.core.management.base import BaseCommand
from django.conf import settings
from core.models import Postcard
import csv
from pathlib import Path


class Command(BaseCommand):
    help = 'Import postcards from CSV file'

    def add_arguments(self, parser):
        parser.add_argument(
            'csv_file',
            type=str,
            help='Path to CSV file'
        )
        parser.add_argument(
            '--update',
            action='store_true',
            help='Update existing postcards instead of skipping'
        )
        parser.add_argument(
            '--delimiter',
            type=str,
            default=',',
            help='CSV delimiter (default: comma)'
        )
        parser.add_argument(
            '--encoding',
            type=str,
            default='utf-8',
            help='File encoding (default: utf-8)'
        )

    def handle(self, *args, **options):
        csv_path = Path(options['csv_file'])
        update_existing = options['update']
        delimiter = options['delimiter']
        encoding = options['encoding']

        if not csv_path.exists():
            self.stderr.write(self.style.ERROR(f'File not found: {csv_path}'))
            return

        self.stdout.write(f'Importing postcards from {csv_path}...')

        created = 0
        updated = 0
        skipped = 0
        errors = 0

        try:
            # Try different encodings if needed
            encodings_to_try = [encoding, 'utf-8-sig', 'latin-1', 'cp1252']

            for enc in encodings_to_try:
                try:
                    with open(csv_path, 'r', encoding=enc) as f:
                        # Detect delimiter if not specified
                        sample = f.read(4096)
                        f.seek(0)

                        if delimiter == ',':
                            # Auto-detect delimiter
                            sniffer = csv.Sniffer()
                            try:
                                dialect = sniffer.sniff(sample)
                                delimiter = dialect.delimiter
                            except csv.Error:
                                pass

                        reader = csv.DictReader(f, delimiter=delimiter)

                        # Normalize field names (lowercase, strip whitespace)
                        if reader.fieldnames:
                            reader.fieldnames = [name.lower().strip() for name in reader.fieldnames]

                        self.stdout.write(f'Detected columns: {reader.fieldnames}')

                        for row_num, row in enumerate(reader, 2):
                            try:
                                result = self.process_row(row, update_existing, row_num)
                                if result == 'created':
                                    created += 1
                                elif result == 'updated':
                                    updated += 1
                                elif result == 'skipped':
                                    skipped += 1
                            except Exception as e:
                                self.stderr.write(self.style.ERROR(f'Row {row_num}: {e}'))
                                errors += 1

                        break  # Successfully read file

                except UnicodeDecodeError:
                    if enc == encodings_to_try[-1]:
                        raise
                    continue

        except Exception as e:
            self.stderr.write(self.style.ERROR(f'Error reading file: {e}'))
            return

        self.stdout.write(self.style.SUCCESS(f'\nImport completed:'))
        self.stdout.write(f'  Created: {created}')
        self.stdout.write(f'  Updated: {updated}')
        self.stdout.write(f'  Skipped: {skipped}')
        self.stdout.write(f'  Errors: {errors}')

        # Update image flags
        self.stdout.write('\nUpdating image flags...')
        self.update_image_flags()

    def process_row(self, row, update_existing, row_num):
        """Process a single CSV row"""
        # Try to find the number field (various possible column names)
        number = None
        for key in ['number', 'numero', 'num', 'id', 'n°', 'no', 'numéro']:
            if key in row and row[key]:
                number = str(row[key]).strip()
                break

        if not number:
            # Try first column
            first_key = list(row.keys())[0] if row else None
            if first_key and row[first_key]:
                number = str(row[first_key]).strip()

        if not number:
            raise ValueError('No number field found')

        # Clean number - ensure it's properly formatted
        # Remove any non-numeric prefix/suffix but keep the number
        import re
        number_match = re.search(r'\d+', number)
        if number_match:
            # Pad to 6 digits if it's a pure number
            num_part = number_match.group()
            if num_part == number:
                number = num_part.zfill(6)

        # Find title field
        title = ''
        for key in ['title', 'titre', 'name', 'nom', 'description', 'libelle', 'libellé']:
            if key in row and row[key]:
                title = str(row[key]).strip()
                break

        if not title:
            title = f'Carte postale {number}'

        # Find keywords field
        keywords = ''
        for key in ['keywords', 'mots-cles', 'mots_cles', 'motscles', 'tags', 'mots-clés', 'mots_clés']:
            if key in row and row[key]:
                keywords = str(row[key]).strip()
                break

        # Find description field
        description = ''
        for key in ['description', 'desc', 'details', 'détails']:
            if key in row and row[key]:
                description = str(row[key]).strip()
                break

        # Find rarity field
        rarity = 'common'
        for key in ['rarity', 'rarete', 'rareté']:
            if key in row and row[key]:
                rarity_value = str(row[key]).strip().lower()
                if rarity_value in ['rare', 'r']:
                    rarity = 'rare'
                elif rarity_value in ['very_rare', 'very rare', 'tres rare', 'très rare', 'vr', 'tr']:
                    rarity = 'very_rare'
                break

        # Check if postcard exists
        existing = Postcard.objects.filter(number=number).first()

        if existing:
            if update_existing:
                existing.title = title
                existing.keywords = keywords
                existing.description = description
                existing.rarity = rarity
                existing.save()
                return 'updated'
            else:
                return 'skipped'
        else:
            Postcard.objects.create(
                number=number,
                title=title,
                keywords=keywords,
                description=description,
                rarity=rarity
            )
            return 'created'

    def update_image_flags(self):
        """Update has_images flag for all postcards"""
        postcards = Postcard.objects.all()
        updated = 0

        for postcard in postcards:
            old_has_images = postcard.has_images
            new_has_images = postcard.check_has_vignette()

            if old_has_images != new_has_images:
                postcard.has_images = new_has_images
                postcard.save(update_fields=['has_images'])
                updated += 1

        self.stdout.write(f'Updated {updated} postcard image flags')
# core/management/commands/import_csv.py
"""
Import postcard metadata from CSV file.
Handles various CSV formats and encodings.
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from django.conf import settings
from core.models import Postcard
from pathlib import Path
import csv
import re


class Command(BaseCommand):
    help = 'Import postcard metadata from CSV file'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help='Path to CSV file')
        parser.add_argument('--delimiter', type=str, default='auto',
                            help='CSV delimiter (auto, comma, semicolon, tab)')
        parser.add_argument('--encoding', type=str, default='auto',
                            help='File encoding (auto, utf-8, latin-1, etc.)')
        parser.add_argument('--update', action='store_true',
                            help='Update existing postcards')
        parser.add_argument('--dry-run', action='store_true',
                            help='Preview without saving')
        parser.add_argument('--clear', action='store_true',
                            help='Clear existing postcards first')
        parser.add_argument('--limit', type=int, default=0,
                            help='Limit number of imports')
        parser.add_argument('--skip-header', action='store_true', default=True,
                            help='Skip first row as header')
        parser.add_argument('--number-col', type=int, default=0,
                            help='Column index for postcard number')
        parser.add_argument('--title-col', type=int, default=1,
                            help='Column index for title')
        parser.add_argument('--keywords-col', type=int, default=2,
                            help='Column index for keywords')
        parser.add_argument('--desc-col', type=int, default=-1,
                            help='Column index for description (-1 to skip)')
        parser.add_argument('--rarity-col', type=int, default=-1,
                            help='Column index for rarity (-1 to skip)')

    def handle(self, *args, **options):
        csv_path = Path(options['csv_file'])

        if not csv_path.exists():
            self.stderr.write(self.style.ERROR(f"File not found: {csv_path}"))
            return

        self.stdout.write(f"\n{'=' * 70}")
        self.stdout.write(f"CSV Import: {csv_path.name}")
        self.stdout.write(f"{'=' * 70}")

        # Detect encoding
        encoding = self.detect_encoding(csv_path, options['encoding'])
        self.stdout.write(f"Encoding: {encoding}")

        # Detect delimiter
        delimiter = self.detect_delimiter(csv_path, encoding, options['delimiter'])
        self.stdout.write(f"Delimiter: '{delimiter}'")

        # Read and preview CSV
        rows = self.read_csv(csv_path, encoding, delimiter)

        if not rows:
            self.stderr.write(self.style.ERROR("No data found in CSV"))
            return

        self.stdout.write(f"Total rows: {len(rows)}")

        # Skip header if needed
        if options['skip_header'] and rows:
            header = rows[0]
            rows = rows[1:]
            self.stdout.write(f"Header: {header[:5]}...")

        # Preview first few rows
        self.stdout.write("\nPreview (first 3 rows):")
        for i, row in enumerate(rows[:3]):
            self.stdout.write(f"  Row {i + 1}: {row[:4]}...")

        if options['dry_run']:
            self.stdout.write(self.style.WARNING("\n[DRY RUN] - No changes will be made"))

        # Clear existing if requested
        if options['clear'] and not options['dry_run']:
            count = Postcard.objects.count()
            Postcard.objects.all().delete()
            self.stdout.write(f"\nCleared {count} existing postcards")

        # Import data
        self.import_rows(rows, options)

    def detect_encoding(self, filepath, hint):
        """Detect file encoding"""
        if hint != 'auto':
            return hint

        encodings = ['utf-8-sig', 'utf-8', 'latin-1', 'cp1252', 'iso-8859-1']

        for enc in encodings:
            try:
                with open(filepath, 'r', encoding=enc) as f:
                    f.read(1024)
                return enc
            except (UnicodeDecodeError, UnicodeError):
                continue

        return 'utf-8'

    def detect_delimiter(self, filepath, encoding, hint):
        """Detect CSV delimiter"""
        if hint == 'comma':
            return ','
        elif hint == 'semicolon':
            return ';'
        elif hint == 'tab':
            return '\t'
        elif hint != 'auto':
            return hint

        with open(filepath, 'r', encoding=encoding) as f:
            sample = f.read(4096)

        # Count occurrences
        counts = {
            ';': sample.count(';'),
            ',': sample.count(','),
            '\t': sample.count('\t'),
        }

        # Return delimiter with most occurrences
        return max(counts, key=counts.get)

    def read_csv(self, filepath, encoding, delimiter):
        """Read CSV file"""
        rows = []

        with open(filepath, 'r', encoding=encoding) as f:
            reader = csv.reader(f, delimiter=delimiter)
            for row in reader:
                if row:  # Skip empty rows
                    rows.append(row)

        return rows

    def import_rows(self, rows, options):
        """Import rows to database"""
        number_col = options['number_col']
        title_col = options['title_col']
        keywords_col = options['keywords_col']
        desc_col = options['desc_col']
        rarity_col = options['rarity_col']
        update_existing = options['update']
        dry_run = options['dry_run']
        limit = options['limit']

        if limit > 0:
            rows = rows[:limit]

        created = 0
        updated = 0
        skipped = 0
        errors = 0

        self.stdout.write(f"\nImporting {len(rows)} rows...")

        with transaction.atomic():
            for i, row in enumerate(rows):
                try:
                    # Extract number
                    if number_col >= len(row):
                        continue

                    number = str(row[number_col]).strip()

                    # Clean number - extract digits and pad
                    number_digits = ''.join(filter(str.isdigit, number))
                    if not number_digits:
                        errors += 1
                        continue

                    number = number_digits.zfill(6)

                    # Extract title
                    title = ''
                    if title_col >= 0 and title_col < len(row):
                        title = str(row[title_col]).strip()
                    if not title:
                        title = f"Carte Postale N° {number}"

                    # Extract keywords
                    keywords = ''
                    if keywords_col >= 0 and keywords_col < len(row):
                        keywords = str(row[keywords_col]).strip()

                    # Extract description
                    description = ''
                    if desc_col >= 0 and desc_col < len(row):
                        description = str(row[desc_col]).strip()

                    # Extract rarity
                    rarity = 'common'
                    if rarity_col >= 0 and rarity_col < len(row):
                        rarity = self.map_rarity(str(row[rarity_col]).strip())

                    if dry_run:
                        self.stdout.write(f"  [{i + 1}] {number}: {title[:40]}...")
                        created += 1
                        continue

                    # Create or update
                    if update_existing:
                        postcard, is_new = Postcard.objects.update_or_create(
                            number=number,
                            defaults={
                                'title': title[:500],
                                'description': description,
                                'keywords': keywords,
                                'rarity': rarity,
                            }
                        )
                        if is_new:
                            created += 1
                        else:
                            updated += 1
                    else:
                        postcard, is_new = Postcard.objects.get_or_create(
                            number=number,
                            defaults={
                                'title': title[:500],
                                'description': description,
                                'keywords': keywords,
                                'rarity': rarity,
                            }
                        )
                        if is_new:
                            created += 1
                        else:
                            skipped += 1

                    # Progress indicator
                    if (i + 1) % 200 == 0:
                        self.stdout.write(f"  Progress: {i + 1}/{len(rows)}")

                except Exception as e:
                    errors += 1
                    if errors < 10:
                        self.stderr.write(self.style.WARNING(f"  Row {i + 1} error: {e}"))

        # Summary
        self.stdout.write(f"\n{'=' * 70}")
        self.stdout.write(self.style.SUCCESS("IMPORT COMPLETE"))
        self.stdout.write(f"{'=' * 70}")
        self.stdout.write(f"Created: {created}")
        self.stdout.write(f"Updated: {updated}")
        self.stdout.write(f"Skipped: {skipped}")
        self.stdout.write(f"Errors: {errors}")
        self.stdout.write(f"Total in DB: {Postcard.objects.count()}")
        self.stdout.write(f"{'=' * 70}\n")

    def map_rarity(self, value):
        """Map rarity value to model choice"""
        if not value:
            return 'common'

        value = value.lower().strip()

        mapping = {
            'common': 'common', 'commune': 'common', 'c': 'common',
            '0': 'common', '1': 'common', 'normale': 'common',
            'rare': 'rare', 'r': 'rare', '2': 'rare',
            'very_rare': 'very_rare', 'very rare': 'very_rare',
            'tres_rare': 'very_rare', 'très rare': 'very_rare',
            'tres rare': 'very_rare', 'vr': 'very_rare',
            'tr': 'very_rare', '3': 'very_rare',
        }

        return mapping.get(value, 'common')
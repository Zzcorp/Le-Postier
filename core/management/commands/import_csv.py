# core/management/commands/import_csv.py
"""
Import postcard metadata from CSV file.
Handles various CSV formats and encodings.
Updates existing postcards with title, keywords, description.
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
        parser.add_argument('--create-missing', action='store_true',
                            help='Create postcards that do not exist')
        parser.add_argument('--dry-run', action='store_true',
                            help='Preview without saving')
        parser.add_argument('--clear', action='store_true',
                            help='Clear existing postcards first')
        parser.add_argument('--limit', type=int, default=0,
                            help='Limit number of imports')
        parser.add_argument('--skip-header', action='store_true', default=True,
                            help='Skip first row as header')
        parser.add_argument('--preview', action='store_true',
                            help='Preview CSV structure and first rows')
        # Column mapping
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
        header = None
        if options['skip_header'] and rows:
            header = rows[0]
            rows = rows[1:]
            self.stdout.write(f"Header: {header[:5]}{'...' if len(header) > 5 else ''}")

        # Preview first few rows
        self.stdout.write("\nPreview (first 3 rows):")
        for i, row in enumerate(rows[:3]):
            preview = [str(c)[:30] for c in row[:4]]
            self.stdout.write(f"  Row {i + 1}: {preview}")

        if options['preview']:
            self.stdout.write("\nPreview mode - no import performed")
            self.show_column_analysis(rows[:100], header)
            return

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

    def show_column_analysis(self, rows, header):
        """Analyze columns to help with mapping"""
        self.stdout.write("\n" + "=" * 50)
        self.stdout.write("Column Analysis")
        self.stdout.write("=" * 50)

        if not rows:
            return

        num_cols = max(len(row) for row in rows)

        for col_idx in range(min(num_cols, 10)):
            samples = []
            for row in rows[:5]:
                if col_idx < len(row):
                    val = str(row[col_idx])[:40]
                    samples.append(val)

            col_name = header[col_idx] if header and col_idx < len(header) else f"Column {col_idx}"
            self.stdout.write(f"\n[{col_idx}] {col_name}:")
            for s in samples:
                self.stdout.write(f"    {s}")

    def import_rows(self, rows, options):
        """Import rows to database"""
        number_col = options['number_col']
        title_col = options['title_col']
        keywords_col = options['keywords_col']
        desc_col = options['desc_col']
        rarity_col = options['rarity_col']
        update_existing = options['update']
        create_missing = options.get('create_missing', True)
        dry_run = options['dry_run']
        limit = options['limit']

        if limit > 0:
            rows = rows[:limit]

        created = 0
        updated = 0
        skipped = 0
        not_found = 0
        errors = 0

        self.stdout.write(f"\nImporting {len(rows)} rows...")

        with transaction.atomic():
            for i, row in enumerate(rows):
                try:
                    # Extract number
                    if number_col >= len(row):
                        errors += 1
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

                    # Check if postcard exists
                    try:
                        postcard = Postcard.objects.get(number=number)
                        if update_existing:
                            postcard.title = title[:500]
                            postcard.description = description
                            postcard.keywords = keywords
                            postcard.rarity = rarity
                            postcard.save()
                            updated += 1
                        else:
                            skipped += 1
                    except Postcard.DoesNotExist:
                        if create_missing:
                            Postcard.objects.create(
                                number=number,
                                title=title[:500],
                                description=description,
                                keywords=keywords,
                                rarity=rarity,
                                has_images=False,  # Will be updated by update_flags
                            )
                            created += 1
                        else:
                            not_found += 1

                    # Progress indicator
                    if (i + 1) % 500 == 0:
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
        self.stdout.write(f"Not Found: {not_found}")
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
# core/management/commands/update_keywords.py
import csv
import os
from django.core.management.base import BaseCommand
from core.models import Postcard


class Command(BaseCommand):
    help = 'Update postcard keywords from CSV file'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help='Path to the CSV file')
        parser.add_argument(
            '--delimiter',
            type=str,
            default=';',
            help='CSV delimiter (default: ;)',
        )
        parser.add_argument(
            '--encoding',
            type=str,
            default='utf-8',
            help='File encoding (default: utf-8)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be updated without actually updating',
        )

    def handle(self, *args, **options):
        csv_file = options['csv_file']
        delimiter = options['delimiter']
        encoding = options['encoding']
        dry_run = options['dry_run']

        if not os.path.exists(csv_file):
            self.stderr.write(self.style.ERROR(f'File not found: {csv_file}'))
            return

        self.stdout.write(f'Reading CSV file: {csv_file}')

        # Try different encodings
        encodings_to_try = [encoding, 'utf-8', 'utf-8-sig', 'latin-1', 'cp1252', 'iso-8859-1']

        file_content = None
        used_encoding = None

        for enc in encodings_to_try:
            try:
                with open(csv_file, 'r', encoding=enc) as f:
                    file_content = f.read()
                    used_encoding = enc
                    break
            except UnicodeDecodeError:
                continue

        if file_content is None:
            self.stderr.write(self.style.ERROR('Could not read file with any encoding'))
            return

        self.stdout.write(f'Using encoding: {used_encoding}')

        # Parse CSV
        lines = file_content.splitlines()

        if not lines:
            self.stderr.write(self.style.ERROR('CSV file is empty'))
            return

        # Auto-detect delimiter
        first_line = lines[0]
        if delimiter not in first_line:
            for test_delim in [';', ',', '\t', '|']:
                if test_delim in first_line:
                    delimiter = test_delim
                    self.stdout.write(f'Auto-detected delimiter: "{delimiter}"')
                    break

        reader = csv.reader(lines, delimiter=delimiter)

        # Get header row
        header = next(reader)
        header = [col.strip().lower().replace('\ufeff', '') for col in header]

        self.stdout.write(f'Columns found: {header}')

        # Find number and keywords columns
        number_col = None
        keywords_col = None

        number_names = ['number', 'numero', 'numéro', 'num', 'n°', 'no', 'id', 'ref']
        keywords_names = ['keywords', 'keyword', 'mots-cles', 'mots-clés', 'mots_cles', 'motscles', 'tags', 'tag',
                          'categories', 'category']

        for i, col in enumerate(header):
            if col in number_names:
                number_col = i
                self.stdout.write(f'Number column: {col} (index {i})')
            if col in keywords_names:
                keywords_col = i
                self.stdout.write(f'Keywords column: {col} (index {i})')

        if number_col is None:
            self.stderr.write(self.style.ERROR('Could not find number column'))
            self.stderr.write(f'Available: {header}')
            return

        if keywords_col is None:
            self.stderr.write(self.style.ERROR('Could not find keywords column'))
            self.stderr.write(f'Available: {header}')
            return

        self.stdout.write('')

        # Process rows
        updated_count = 0
        not_found_count = 0
        empty_keywords_count = 0
        error_count = 0

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be made'))
            self.stdout.write('')

        row_num = 1
        for row in reader:
            row_num += 1

            if not row or len(row) <= max(number_col, keywords_col):
                continue

            try:
                number = row[number_col].strip()
                keywords = row[keywords_col].strip()

                if not number:
                    continue

                if not keywords:
                    empty_keywords_count += 1
                    continue

                # Find the postcard
                postcard = Postcard.objects.filter(number=number).first()

                if not postcard:
                    not_found_count += 1
                    if not_found_count <= 10:
                        self.stdout.write(f'  Not found: {number}')
                    continue

                if dry_run:
                    if row_num <= 20:
                        self.stdout.write(f'  Would update {number}: "{keywords[:50]}..."')
                else:
                    postcard.keywords = keywords
                    postcard.save(update_fields=['keywords'])

                    if row_num <= 20 or row_num % 500 == 0:
                        self.stdout.write(f'  Updated {number}: "{keywords[:50]}..."')

                updated_count += 1

            except Exception as e:
                error_count += 1
                self.stderr.write(f'  Row {row_num}: Error - {str(e)}')

        # Summary
        self.stdout.write('')
        self.stdout.write('=' * 50)
        self.stdout.write('UPDATE SUMMARY')
        self.stdout.write('=' * 50)

        if dry_run:
            self.stdout.write(self.style.WARNING(f'Would update: {updated_count}'))
        else:
            self.stdout.write(self.style.SUCCESS(f'Updated: {updated_count}'))

        self.stdout.write(f'Not found in DB: {not_found_count}')
        self.stdout.write(f'Empty keywords in CSV: {empty_keywords_count}')
        self.stdout.write(f'Errors: {error_count}')

        # Verify
        total_with_keywords = Postcard.objects.exclude(keywords='').exclude(keywords__isnull=True).count()
        total_postcards = Postcard.objects.count()
        self.stdout.write('')
        self.stdout.write(f'Total postcards: {total_postcards}')
        self.stdout.write(f'Postcards with keywords: {total_with_keywords}')
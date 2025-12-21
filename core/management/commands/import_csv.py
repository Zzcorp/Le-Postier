# core/management/commands/import_csv.py
import csv
import os
from django.core.management.base import BaseCommand
from core.models import Postcard


class Command(BaseCommand):
    help = 'Import postcards from CSV file with keywords support'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help='Path to the CSV file')
        parser.add_argument(
            '--update',
            action='store_true',
            help='Update existing postcards instead of skipping them',
        )
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
            help='Show what would be imported without actually importing',
        )

    def handle(self, *args, **options):
        csv_file = options['csv_file']
        update_existing = options['update']
        delimiter = options['delimiter']
        encoding = options['encoding']
        dry_run = options['dry_run']

        if not os.path.exists(csv_file):
            self.stderr.write(self.style.ERROR(f'File not found: {csv_file}'))
            return

        self.stdout.write(f'Reading CSV file: {csv_file}')
        self.stdout.write(f'Delimiter: "{delimiter}", Encoding: {encoding}')
        self.stdout.write(f'Update existing: {update_existing}')
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN - No changes will be made'))
        self.stdout.write('')

        # Try different encodings if the specified one fails
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

        self.stdout.write(f'Successfully read file with encoding: {used_encoding}')

        # Parse CSV
        lines = file_content.splitlines()

        if not lines:
            self.stderr.write(self.style.ERROR('CSV file is empty'))
            return

        # Detect delimiter if needed
        first_line = lines[0]
        if delimiter not in first_line:
            # Try to auto-detect delimiter
            for test_delim in [';', ',', '\t', '|']:
                if test_delim in first_line:
                    delimiter = test_delim
                    self.stdout.write(f'Auto-detected delimiter: "{delimiter}"')
                    break

        reader = csv.reader(lines, delimiter=delimiter)

        # Get header row
        try:
            header = next(reader)
        except StopIteration:
            self.stderr.write(self.style.ERROR('CSV file has no header row'))
            return

        # Clean header names (remove BOM, whitespace, lowercase)
        header = [col.strip().lower().replace('\ufeff', '') for col in header]

        self.stdout.write(f'Found columns: {header}')
        self.stdout.write('')

        # Map column names to our fields
        # Support various column name formats
        column_mapping = {
            'number': ['number', 'numero', 'numéro', 'num', 'n°', 'no', 'id', 'ref', 'reference', 'référence'],
            'title': ['title', 'titre', 'name', 'nom', 'description', 'label', 'libelle', 'libellé'],
            'keywords': ['keywords', 'keyword', 'mots-cles', 'mots-clés', 'mots_cles', 'motscles', 'tags', 'tag',
                         'categories', 'category', 'categorie', 'catégorie', 'themes', 'theme', 'thème'],
            'description': ['description', 'desc', 'details', 'détails', 'note', 'notes', 'comment', 'commentaire'],
            'rarity': ['rarity', 'rarete', 'rareté', 'rare'],
        }

        # Find column indices
        col_indices = {}
        for field, possible_names in column_mapping.items():
            for i, col in enumerate(header):
                if col in possible_names:
                    col_indices[field] = i
                    self.stdout.write(f'  Mapped "{col}" -> {field}')
                    break

        self.stdout.write('')

        # Check required columns
        if 'number' not in col_indices:
            self.stderr.write(self.style.ERROR('Could not find "number" column'))
            self.stderr.write(f'Available columns: {header}')
            return

        if 'title' not in col_indices:
            self.stderr.write(self.style.ERROR('Could not find "title" column'))
            self.stderr.write(f'Available columns: {header}')
            return

        # Report on keywords column
        if 'keywords' in col_indices:
            self.stdout.write(self.style.SUCCESS(f'Keywords column found at index {col_indices["keywords"]}'))
        else:
            self.stdout.write(self.style.WARNING('No keywords column found - keywords will be empty'))

        self.stdout.write('')

        # Process rows
        created_count = 0
        updated_count = 0
        skipped_count = 0
        error_count = 0
        keywords_count = 0

        row_num = 1  # Header is row 0
        for row in reader:
            row_num += 1

            # Skip empty rows
            if not row or all(cell.strip() == '' for cell in row):
                continue

            try:
                # Get number
                number = row[col_indices['number']].strip() if col_indices['number'] < len(row) else ''
                if not number:
                    self.stdout.write(f'  Row {row_num}: Skipping - no number')
                    skipped_count += 1
                    continue

                # Get title
                title = row[col_indices['title']].strip() if col_indices['title'] < len(row) else ''
                if not title:
                    title = f'Carte postale {number}'

                # Get keywords
                keywords = ''
                if 'keywords' in col_indices and col_indices['keywords'] < len(row):
                    keywords = row[col_indices['keywords']].strip()
                    if keywords:
                        keywords_count += 1

                # Get description
                description = ''
                if 'description' in col_indices and col_indices['description'] < len(row):
                    description = row[col_indices['description']].strip()

                # Get rarity
                rarity = 'common'
                if 'rarity' in col_indices and col_indices['rarity'] < len(row):
                    rarity_value = row[col_indices['rarity']].strip().lower()
                    if rarity_value in ['rare', 'r']:
                        rarity = 'rare'
                    elif rarity_value in ['very_rare', 'very rare', 'tres rare', 'très rare', 'vr', 'tr']:
                        rarity = 'very_rare'

                if dry_run:
                    self.stdout.write(f'  Would import: {number} - {title[:40]}... (keywords: {len(keywords)} chars)')
                    continue

                # Check if postcard exists
                existing = Postcard.objects.filter(number=number).first()

                if existing:
                    if update_existing:
                        existing.title = title
                        existing.keywords = keywords
                        existing.description = description
                        existing.rarity = rarity
                        existing.save()
                        updated_count += 1
                        if row_num <= 10 or row_num % 100 == 0:
                            self.stdout.write(f'  Updated: {number} - {title[:40]}...')
                    else:
                        skipped_count += 1
                else:
                    Postcard.objects.create(
                        number=number,
                        title=title,
                        keywords=keywords,
                        description=description,
                        rarity=rarity,
                    )
                    created_count += 1
                    if row_num <= 10 or row_num % 100 == 0:
                        self.stdout.write(f'  Created: {number} - {title[:40]}...')

            except Exception as e:
                self.stderr.write(f'  Row {row_num}: Error - {str(e)}')
                error_count += 1
                continue

        # Summary
        self.stdout.write('')
        self.stdout.write('=' * 50)
        self.stdout.write('IMPORT SUMMARY')
        self.stdout.write('=' * 50)

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN - No changes were made'))
        else:
            self.stdout.write(self.style.SUCCESS(f'Created: {created_count}'))
            self.stdout.write(self.style.SUCCESS(f'Updated: {updated_count}'))

        self.stdout.write(f'Skipped: {skipped_count}')
        self.stdout.write(f'Errors: {error_count}')
        self.stdout.write(f'Rows with keywords: {keywords_count}')
        self.stdout.write('')

        # Verify keywords were imported
        total_with_keywords = Postcard.objects.exclude(keywords='').exclude(keywords__isnull=True).count()
        self.stdout.write(f'Total postcards in DB with keywords: {total_with_keywords}')
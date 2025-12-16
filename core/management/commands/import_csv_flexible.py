# core/management/commands/import_csv_flexible.py
"""
Flexible CSV importer that auto-detects format
"""

import csv
import re
from django.core.management.base import BaseCommand
from django.db import transaction
from core.models import Postcard


class Command(BaseCommand):
    help = 'Import postcards from any CSV format'

    def add_arguments(self, parser):
        parser.add_argument('file', type=str, help='Path to CSV file')
        parser.add_argument('--preview', action='store_true', help='Preview first 10 rows without importing')
        parser.add_argument('--dry-run', action='store_true', help='Test without saving')
        parser.add_argument('--clear', action='store_true', help='Clear existing data first')
        parser.add_argument('--limit', type=int, help='Limit number of records')

    def handle(self, *args, **options):
        file_path = options['file']

        self.stdout.write(f"\n{'=' * 60}")
        self.stdout.write(f"Importing from: {file_path}")
        self.stdout.write('=' * 60)

        # Step 1: Detect file format
        file_info = self.analyze_file(file_path)

        if not file_info:
            return

        self.stdout.write(f"\nFile Analysis:")
        self.stdout.write(f"  Encoding: {file_info['encoding']}")
        self.stdout.write(f"  Delimiter: '{file_info['delimiter']}'")
        self.stdout.write(f"  Has header: {file_info['has_header']}")
        self.stdout.write(f"  Columns detected: {file_info['columns']}")
        self.stdout.write(f"  Total rows: {file_info['row_count']}")

        # Preview mode
        if options['preview']:
            self.preview_data(file_path, file_info)
            return

        # Import
        if options['clear'] and not options['dry_run']:
            count = Postcard.objects.count()
            Postcard.objects.all().delete()
            self.stdout.write(f"\nCleared {count} existing postcards")

        self.import_data(file_path, file_info, options)

    def analyze_file(self, file_path):
        """Analyze CSV file to detect format"""
        encodings = ['utf-8-sig', 'utf-8', 'latin-1', 'cp1252', 'iso-8859-1']

        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    content = f.read()

                if content:
                    # Count delimiters in first few lines
                    lines = content.split('\n')[:10]
                    first_line = lines[0] if lines else ''

                    # Detect delimiter
                    semicolon_count = first_line.count(';')
                    comma_count = first_line.count(',')
                    tab_count = first_line.count('\t')

                    if semicolon_count > comma_count and semicolon_count > tab_count:
                        delimiter = ';'
                    elif tab_count > comma_count:
                        delimiter = '\t'
                    else:
                        delimiter = ','

                    # Parse with detected delimiter
                    with open(file_path, 'r', encoding=encoding) as f:
                        reader = csv.reader(f, delimiter=delimiter)
                        rows = list(reader)

                    if not rows:
                        continue

                    # Detect if first row is header
                    first_row = rows[0]
                    has_header = self.is_header_row(first_row)

                    # Get column info
                    if has_header:
                        columns = first_row
                        data_rows = rows[1:]
                    else:
                        columns = [f'col_{i}' for i in range(len(first_row))]
                        data_rows = rows

                    return {
                        'encoding': encoding,
                        'delimiter': delimiter,
                        'has_header': has_header,
                        'columns': columns,
                        'row_count': len(data_rows),
                        'sample_rows': data_rows[:5]
                    }

            except (UnicodeDecodeError, UnicodeError):
                continue
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"Error with {encoding}: {e}"))
                continue

        self.stdout.write(self.style.ERROR("Could not read file with any encoding"))
        return None

    def is_header_row(self, row):
        """Check if row looks like a header"""
        header_keywords = [
            'number', 'numero', 'id', 'title', 'titre', 'name', 'nom',
            'description', 'keywords', 'mots', 'rarity', 'rarete'
        ]

        row_lower = [str(cell).lower().strip() for cell in row]

        # Check if any cell matches header keywords
        for cell in row_lower:
            for keyword in header_keywords:
                if keyword in cell:
                    return True

        # Check if first column looks like a number (probably data, not header)
        if row and row[0]:
            try:
                int(str(row[0]).strip())
                return False  # First column is a number, probably data
            except ValueError:
                pass

        return False

    def preview_data(self, file_path, file_info):
        """Preview the data"""
        self.stdout.write(f"\n{'=' * 60}")
        self.stdout.write("DATA PREVIEW (first 10 rows)")
        self.stdout.write('=' * 60)

        columns = file_info['columns']
        self.stdout.write(f"\nColumns: {columns}")

        with open(file_path, 'r', encoding=file_info['encoding']) as f:
            reader = csv.reader(f, delimiter=file_info['delimiter'])

            if file_info['has_header']:
                next(reader)  # Skip header

            for i, row in enumerate(reader):
                if i >= 10:
                    break

                self.stdout.write(f"\nRow {i + 1}:")
                for j, (col, val) in enumerate(zip(columns, row)):
                    val_preview = str(val)[:50] + '...' if len(str(val)) > 50 else val
                    self.stdout.write(f"  {col}: {val_preview}")

        self.stdout.write(f"\n{'=' * 60}")
        self.stdout.write("COLUMN MAPPING SUGGESTION:")
        self.stdout.write('=' * 60)

        mapping = self.suggest_column_mapping(columns)
        for field, col in mapping.items():
            self.stdout.write(f"  {field} <- {col}")

    def suggest_column_mapping(self, columns):
        """Suggest mapping from CSV columns to model fields"""
        columns_lower = [str(c).lower().strip() for c in columns]

        mapping = {}

        # Number field
        for pattern in ['number', 'numero', 'num', 'id', 'ref', 'code']:
            for i, col in enumerate(columns_lower):
                if pattern in col:
                    mapping['number'] = columns[i]
                    break
            if 'number' in mapping:
                break

        # Title field
        for pattern in ['title', 'titre', 'name', 'nom', 'label', 'libelle']:
            for i, col in enumerate(columns_lower):
                if pattern in col:
                    mapping['title'] = columns[i]
                    break
            if 'title' in mapping:
                break

        # Description field
        for pattern in ['description', 'desc', 'detail']:
            for i, col in enumerate(columns_lower):
                if pattern in col:
                    mapping['description'] = columns[i]
                    break
            if 'description' in mapping:
                break

        # Keywords field
        for pattern in ['keyword', 'mot', 'tag', 'label']:
            for i, col in enumerate(columns_lower):
                if pattern in col and col not in mapping.values():
                    mapping['keywords'] = columns[i]
                    break
            if 'keywords' in mapping:
                break

        # Rarity field
        for pattern in ['rarity', 'rarete', 'rare']:
            for i, col in enumerate(columns_lower):
                if pattern in col:
                    mapping['rarity'] = columns[i]
                    break
            if 'rarity' in mapping:
                break

        # If no mapping found, use positional
        if not mapping:
            if len(columns) >= 1:
                mapping['number'] = columns[0]
            if len(columns) >= 2:
                mapping['title'] = columns[1]
            if len(columns) >= 3:
                mapping['description'] = columns[2]
            if len(columns) >= 4:
                mapping['keywords'] = columns[3]

        return mapping

    def import_data(self, file_path, file_info, options):
        """Import the data"""
        columns = file_info['columns']
        mapping = self.suggest_column_mapping(columns)

        self.stdout.write(f"\nUsing column mapping:")
        for field, col in mapping.items():
            self.stdout.write(f"  {field} <- {col}")

        # Create column index map
        col_indices = {col: i for i, col in enumerate(columns)}

        created = 0
        updated = 0
        errors = 0

        with open(file_path, 'r', encoding=file_info['encoding']) as f:
            reader = csv.reader(f, delimiter=file_info['delimiter'])

            if file_info['has_header']:
                next(reader)  # Skip header

            rows = list(reader)

            if options.get('limit'):
                rows = rows[:options['limit']]

            self.stdout.write(f"\nProcessing {len(rows)} rows...")

            with transaction.atomic():
                for i, row in enumerate(rows):
                    try:
                        # Extract values using mapping
                        def get_value(field):
                            col_name = mapping.get(field)
                            if col_name and col_name in col_indices:
                                idx = col_indices[col_name]
                                if idx < len(row):
                                    return str(row[idx]).strip()
                            return ''

                        number = get_value('number')
                        title = get_value('title')

                        # Skip if no number
                        if not number:
                            # Try first column as number
                            if row:
                                number = str(row[0]).strip()

                        # Skip if still no number or title
                        if not number:
                            errors += 1
                            continue

                        if not title:
                            # Try second column as title
                            if len(row) > 1:
                                title = str(row[1]).strip()
                            else:
                                title = f"Carte Postale {number}"

                        # Clean number (remove non-numeric prefix if needed)
                        number_clean = ''.join(filter(str.isdigit, str(number)))
                        if number_clean:
                            number = number_clean.zfill(6)  # Pad to 6 digits

                        description = get_value('description')
                        keywords = get_value('keywords')
                        rarity = self.map_rarity(get_value('rarity'))

                        if options.get('dry_run'):
                            self.stdout.write(f"[DRY RUN] {number}: {title[:50]}")
                            created += 1
                            continue

                        postcard, is_new = Postcard.objects.update_or_create(
                            number=number,
                            defaults={
                                'title': title[:500],  # Limit title length
                                'description': description,
                                'keywords': keywords,
                                'rarity': rarity,
                            }
                        )

                        if is_new:
                            created += 1
                        else:
                            updated += 1

                        if (i + 1) % 200 == 0:
                            self.stdout.write(f"  Progress: {i + 1}/{len(rows)}")

                    except Exception as e:
                        errors += 1
                        if errors < 10:
                            self.stdout.write(self.style.WARNING(
                                f"  Row {i + 1} error: {e}"
                            ))

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(f"✓ Created: {created}"))
        self.stdout.write(self.style.SUCCESS(f"✓ Updated: {updated}"))
        if errors:
            self.stdout.write(self.style.WARNING(f"✗ Errors: {errors}"))

    def map_rarity(self, value):
        """Map rarity string to model choice"""
        if not value:
            return 'common'

        value = str(value).lower().strip()

        mapping = {
            'common': 'common', 'commune': 'common', 'c': 'common', '0': 'common', '1': 'common',
            'rare': 'rare', 'r': 'rare', '2': 'rare',
            'very_rare': 'very_rare', 'very rare': 'very_rare', 'tres_rare': 'very_rare',
            'très rare': 'very_rare', 'tres rare': 'very_rare', 'vr': 'very_rare', '3': 'very_rare',
        }

        return mapping.get(value, 'common')
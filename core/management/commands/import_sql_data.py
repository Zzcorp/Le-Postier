# core/management/commands/import_sql_data.py
"""
Import postcards from SQL dump or CSV
Usage: python manage.py import_sql_data --file /path/to/data.csv
"""

import csv
import json
from django.core.management.base import BaseCommand
from django.db import connection, transaction
from core.models import Postcard, Theme
import re


class Command(BaseCommand):
    help = 'Import postcards from SQL dump or CSV file'

    def add_arguments(self, parser):
        parser.add_argument('--file', type=str, required=True, help='Path to SQL or CSV file')
        parser.add_argument('--format', choices=['sql', 'csv', 'auto'], default='auto', help='File format')
        parser.add_argument('--clear', action='store_true', help='Clear existing data first')
        parser.add_argument('--dry-run', action='store_true', help='Test without saving')
        parser.add_argument('--limit', type=int, help='Limit number of records')

    def handle(self, *args, **options):
        file_path = options['file']
        file_format = options['format']

        # Auto-detect format
        if file_format == 'auto':
            if file_path.endswith('.sql'):
                file_format = 'sql'
            else:
                file_format = 'csv'

        self.stdout.write(f"Importing from {file_path} (format: {file_format})")

        if options['clear'] and not options['dry_run']:
            self.stdout.write("Clearing existing postcards...")
            Postcard.objects.all().delete()

        if file_format == 'sql':
            self.import_sql(file_path, options)
        else:
            self.import_csv(file_path, options)

    def import_sql(self, file_path, options):
        """Parse SQL INSERT statements and create postcards"""
        self.stdout.write("Parsing SQL file...")

        try:
            with open(file_path, 'r', encoding='utf-8-sig') as f:
                content = f.read()
        except UnicodeDecodeError:
            with open(file_path, 'r', encoding='latin-1') as f:
                content = f.read()

        # Find INSERT statements for postcards table
        # Pattern for: INSERT INTO `postcards` VALUES (...)
        insert_pattern = re.compile(
            r"INSERT INTO [`'\"]?(\w*postcard\w*)[`'\"]?\s*(?:\([^)]+\))?\s*VALUES\s*\((.+?)\);",
            re.IGNORECASE | re.DOTALL
        )

        matches = insert_pattern.findall(content)
        self.stdout.write(f"Found {len(matches)} INSERT statements")

        if not matches:
            # Try simpler pattern for individual inserts
            simple_pattern = re.compile(
                r"INSERT INTO [`'\"]?\w*postcard\w*[`'\"]?\s*VALUES\s*\((.+?)\);",
                re.IGNORECASE
            )
            values_only = simple_pattern.findall(content)
            self.stdout.write(f"Found {len(values_only)} values with simple pattern")

            # Parse values
            postcards_data = []
            for values_str in values_only:
                try:
                    parsed = self.parse_sql_values(values_str)
                    if parsed:
                        postcards_data.append(parsed)
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f"Parse error: {e}"))
        else:
            postcards_data = []
            for table_name, values_str in matches:
                try:
                    # Handle multiple value sets in one INSERT
                    value_sets = self.split_value_sets(values_str)
                    for vs in value_sets:
                        parsed = self.parse_sql_values(vs)
                        if parsed:
                            postcards_data.append(parsed)
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f"Parse error: {e}"))

        self.stdout.write(f"Parsed {len(postcards_data)} postcards")

        # Create postcards
        self.create_postcards(postcards_data, options)

    def parse_sql_values(self, values_str):
        """Parse a SQL VALUES string into a dictionary"""
        # Remove outer parentheses if present
        values_str = values_str.strip()
        if values_str.startswith('('):
            values_str = values_str[1:]
        if values_str.endswith(')'):
            values_str = values_str[:-1]

        # Split by comma, respecting quoted strings
        values = []
        current = []
        in_quotes = False
        quote_char = None
        escape_next = False

        for char in values_str:
            if escape_next:
                current.append(char)
                escape_next = False
                continue

            if char == '\\':
                escape_next = True
                continue

            if char in ["'", '"'] and not in_quotes:
                in_quotes = True
                quote_char = char
                continue
            elif char == quote_char and in_quotes:
                in_quotes = False
                quote_char = None
                continue

            if char == ',' and not in_quotes:
                values.append(''.join(current).strip())
                current = []
            else:
                current.append(char)

        values.append(''.join(current).strip())

        # Map to postcard fields (adjust indices based on your SQL schema)
        # Common schema: id, number, title, description, keywords, rarity, ...
        if len(values) >= 3:
            return {
                'number': self.clean_value(values[1] if len(values) > 1 else values[0]),
                'title': self.clean_value(values[2] if len(values) > 2 else ''),
                'description': self.clean_value(values[3] if len(values) > 3 else ''),
                'keywords': self.clean_value(values[4] if len(values) > 4 else ''),
                'rarity': self.map_rarity(values[5] if len(values) > 5 else 'common'),
            }
        return None

    def clean_value(self, val):
        """Clean a SQL value"""
        if val.upper() == 'NULL':
            return ''
        # Remove quotes
        val = val.strip().strip("'\"")
        # Unescape
        val = val.replace("\\'", "'").replace('\\"', '"')
        return val

    def split_value_sets(self, values_str):
        """Split multiple value sets: (a,b), (c,d) into separate sets"""
        sets = []
        depth = 0
        current = []

        for char in values_str:
            if char == '(':
                depth += 1
                if depth == 1:
                    continue
            elif char == ')':
                depth -= 1
                if depth == 0:
                    sets.append(''.join(current))
                    current = []
                    continue

            if depth > 0:
                current.append(char)

        return sets if sets else [values_str]

    def map_rarity(self, val):
        """Map rarity value"""
        val = self.clean_value(val).lower()
        mapping = {
            'common': 'common', 'commune': 'common', 'c': 'common', '0': 'common',
            'rare': 'rare', 'r': 'rare', '1': 'rare',
            'very_rare': 'very_rare', 'very rare': 'very_rare', 'tres_rare': 'very_rare',
            'très rare': 'very_rare', 'vr': 'very_rare', '2': 'very_rare',
        }
        return mapping.get(val, 'common')

    def import_csv(self, file_path, options):
        """Import from CSV file"""
        self.stdout.write("Reading CSV file...")

        postcards_data = []

        # Try different encodings
        for encoding in ['utf-8-sig', 'utf-8', 'latin-1', 'cp1252']:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    # Detect delimiter
                    sample = f.read(2048)
                    f.seek(0)

                    delimiter = ';' if sample.count(';') > sample.count(',') else ','

                    reader = csv.DictReader(f, delimiter=delimiter)

                    for row in reader:
                        # Map columns (handle various column names)
                        number = (row.get('number') or row.get('Number') or
                                  row.get('numero') or row.get('Numero') or
                                  row.get('id') or row.get('ID') or '')

                        title = (row.get('title') or row.get('Title') or
                                 row.get('titre') or row.get('Titre') or
                                 row.get('name') or row.get('Name') or '')

                        if number and title:
                            postcards_data.append({
                                'number': str(number).strip(),
                                'title': str(title).strip(),
                                'description': row.get('description', row.get('Description', '')),
                                'keywords': row.get('keywords', row.get('Keywords', row.get('mots_cles', ''))),
                                'rarity': self.map_rarity(row.get('rarity', row.get('rarete', 'common'))),
                            })

                        if options.get('limit') and len(postcards_data) >= options['limit']:
                            break

                    self.stdout.write(f"Read {len(postcards_data)} postcards (encoding: {encoding})")
                    break

            except UnicodeDecodeError:
                continue
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"Error with {encoding}: {e}"))
                continue

        self.create_postcards(postcards_data, options)

    def create_postcards(self, postcards_data, options):
        """Create postcard records in database"""
        dry_run = options.get('dry_run', False)
        limit = options.get('limit')

        if limit:
            postcards_data = postcards_data[:limit]

        created = 0
        updated = 0
        errors = 0

        self.stdout.write(f"\nCreating {len(postcards_data)} postcards...")

        with transaction.atomic():
            for i, data in enumerate(postcards_data):
                try:
                    if dry_run:
                        self.stdout.write(f"[DRY RUN] {data['number']}: {data['title'][:50]}")
                        created += 1
                        continue

                    postcard, is_new = Postcard.objects.update_or_create(
                        number=data['number'],
                        defaults={
                            'title': data['title'],
                            'description': data.get('description', ''),
                            'keywords': data.get('keywords', ''),
                            'rarity': data.get('rarity', 'common'),
                        }
                    )

                    if is_new:
                        created += 1
                    else:
                        updated += 1

                    if (i + 1) % 200 == 0:
                        self.stdout.write(f"  Progress: {i + 1}/{len(postcards_data)}")

                except Exception as e:
                    errors += 1
                    if errors < 10:
                        self.stdout.write(self.style.WARNING(f"  Error: {data.get('number')}: {e}"))

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(f"✓ Created: {created}"))
        self.stdout.write(self.style.SUCCESS(f"✓ Updated: {updated}"))
        if errors:
            self.stdout.write(self.style.WARNING(f"✗ Errors: {errors}"))
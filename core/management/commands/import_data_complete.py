# core/management/commands/import_data_complete.py
"""
Complete data import from CSV or SQL
Handles multiple formats and encodings
"""

import csv
import re
import os
from pathlib import Path
from django.core.management.base import BaseCommand
from django.db import transaction
from core.models import Postcard


class Command(BaseCommand):
    help = 'Import postcards from CSV or SQL file'

    def add_arguments(self, parser):
        parser.add_argument('file', type=str, help='Path to CSV or SQL file')
        parser.add_argument('--clear', action='store_true', help='Clear existing data first')
        parser.add_argument('--dry-run', action='store_true', help='Preview without saving')
        parser.add_argument('--limit', type=int, help='Limit number of records')
        parser.add_argument('--update', action='store_true', help='Update existing records')

    def handle(self, *args, **options):
        file_path = Path(options['file'])

        if not file_path.exists():
            self.stdout.write(self.style.ERROR(f"File not found: {file_path}"))
            return

        self.stdout.write(f"\n{'=' * 60}")
        self.stdout.write(f"Importing from: {file_path}")
        self.stdout.write(f"{'=' * 60}")

        # Determine file type
        if file_path.suffix.lower() == '.sql':
            data = self.parse_sql_file(file_path)
        else:
            data = self.parse_csv_file(file_path)

        if not data:
            self.stdout.write(self.style.ERROR("No data found to import"))
            return

        self.stdout.write(f"\nFound {len(data)} records to import")

        # Apply limit
        if options.get('limit'):
            data = data[:options['limit']]
            self.stdout.write(f"Limited to {len(data)} records")

        # Preview first few records
        self.stdout.write("\nPreview (first 3 records):")
        for i, record in enumerate(data[:3]):
            self.stdout.write(f"  {i + 1}. {record.get('number', 'N/A')}: {record.get('title', 'N/A')[:50]}")

        if options['dry_run']:
            self.stdout.write(self.style.WARNING("\n[DRY RUN] No changes made"))
            return

        # Clear if requested
        if options['clear']:
            count = Postcard.objects.count()
            Postcard.objects.all().delete()
            self.stdout.write(f"\nCleared {count} existing postcards")

        # Import data
        self.import_postcards(data, options.get('update', False))

    def parse_csv_file(self, file_path):
        """Parse CSV file with auto-detection"""
        encodings = ['utf-8-sig', 'utf-8', 'latin-1', 'cp1252', 'iso-8859-1']

        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    # Read sample to detect format
                    sample = f.read(4096)
                    f.seek(0)

                    # Detect delimiter
                    if sample.count(';') > sample.count(','):
                        delimiter = ';'
                    elif sample.count('\t') > sample.count(','):
                        delimiter = '\t'
                    else:
                        delimiter = ','

                    self.stdout.write(f"  Detected: encoding={encoding}, delimiter='{delimiter}'")

                    reader = csv.DictReader(f, delimiter=delimiter)

                    records = []
                    for row in reader:
                        record = self.map_csv_row(row)
                        if record:
                            records.append(record)

                    if records:
                        return records

            except (UnicodeDecodeError, UnicodeError):
                continue
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"  Error with {encoding}: {e}"))

        return []

    def map_csv_row(self, row):
        """Map CSV row to postcard fields"""
        # Try different column name patterns
        number = (
                row.get('number') or row.get('Number') or row.get('numero') or
                row.get('Numero') or row.get('id') or row.get('ID') or
                row.get('num') or row.get('ref') or row.get('code') or ''
        )

        title = (
                row.get('title') or row.get('Title') or row.get('titre') or
                row.get('Titre') or row.get('label') or row.get('Label') or
                row.get('name') or row.get('Name') or row.get('nom') or ''
        )

        # If number/title not found, try positional
        if not number or not title:
            values = list(row.values())
            if len(values) >= 2:
                if not number:
                    number = str(values[0]).strip()
                if not title:
                    title = str(values[1]).strip()

        if not number:
            return None

        # Clean and format number
        number = str(number).strip()
        number_digits = ''.join(filter(str.isdigit, number))
        if number_digits:
            number = number_digits.zfill(6)

        description = (
                row.get('description') or row.get('Description') or
                row.get('desc') or ''
        )

        keywords = (
                row.get('keywords') or row.get('Keywords') or
                row.get('mots_cles') or row.get('mots_clefs') or
                row.get('mots-cles') or row.get('tags') or ''
        )

        rarity = self.map_rarity(
            row.get('rarity') or row.get('rarete') or row.get('Rarity') or 'common'
        )

        return {
            'number': number,
            'title': title if title else f"Carte Postale N° {number}",
            'description': str(description).strip(),
            'keywords': str(keywords).strip(),
            'rarity': rarity,
        }

    def parse_sql_file(self, file_path):
        """Parse SQL dump file"""
        self.stdout.write("  Parsing SQL file...")

        # Try different encodings
        content = None
        for encoding in ['utf-8-sig', 'utf-8', 'latin-1', 'cp1252']:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    content = f.read()
                self.stdout.write(f"  Using encoding: {encoding}")
                break
            except UnicodeDecodeError:
                continue

        if not content:
            return []

        # Find INSERT statements
        records = []

        # Pattern 1: Standard INSERT INTO ... VALUES
        insert_pattern = re.compile(
            r"INSERT\s+INTO\s+[`'\"]?[\w_]+[`'\"]?\s*(?:\([^)]+\))?\s*VALUES\s*(.+?);",
            re.IGNORECASE | re.DOTALL
        )

        matches = insert_pattern.findall(content)
        self.stdout.write(f"  Found {len(matches)} INSERT statements")

        for match in matches:
            # Extract individual value sets
            value_sets = self.extract_value_sets(match)
            for vs in value_sets:
                record = self.parse_sql_values(vs)
                if record:
                    records.append(record)

        return records

    def extract_value_sets(self, values_str):
        """Extract individual value sets from VALUES clause"""
        sets = []
        current = []
        paren_depth = 0
        in_string = False
        string_char = None
        escape_next = False

        for char in values_str:
            if escape_next:
                current.append(char)
                escape_next = False
                continue

            if char == '\\':
                escape_next = True
                current.append(char)
                continue

            if char in ("'", '"') and not in_string:
                in_string = True
                string_char = char
                current.append(char)
            elif char == string_char and in_string:
                in_string = False
                string_char = None
                current.append(char)
            elif char == '(' and not in_string:
                paren_depth += 1
                if paren_depth == 1:
                    current = []
                    continue
                current.append(char)
            elif char == ')' and not in_string:
                paren_depth -= 1
                if paren_depth == 0:
                    sets.append(''.join(current))
                    current = []
                    continue
                current.append(char)
            else:
                current.append(char)

        return sets if sets else [values_str]

    def parse_sql_values(self, values_str):
        """Parse a single SQL VALUES set"""
        # Split by comma, respecting quotes
        values = []
        current = []
        in_string = False
        string_char = None
        escape_next = False

        for char in values_str:
            if escape_next:
                current.append(char)
                escape_next = False
                continue

            if char == '\\':
                escape_next = True
                continue

            if char in ("'", '"') and not in_string:
                in_string = True
                string_char = char
            elif char == string_char and in_string:
                in_string = False
                string_char = None
            elif char == ',' and not in_string:
                values.append(''.join(current).strip())
                current = []
                continue

            current.append(char)

        if current:
            values.append(''.join(current).strip())

        # Clean values
        cleaned = []
        for v in values:
            v = v.strip()
            if v.upper() == 'NULL':
                v = ''
            elif v.startswith("'") and v.endswith("'"):
                v = v[1:-1]
            elif v.startswith('"') and v.endswith('"'):
                v = v[1:-1]
            # Unescape
            v = v.replace("\\'", "'").replace('\\"', '"').replace('\\n', '\n')
            cleaned.append(v)

        if len(cleaned) < 2:
            return None

        # Map to fields - adjust indices based on your SQL schema
        # Common: id(0), label/title(1), mots_clefs(2), ..., rarete(17?), ..., description(41?)
        try:
            number = cleaned[0] if cleaned[0] else ''
            title = cleaned[1] if len(cleaned) > 1 else ''
            keywords = cleaned[2] if len(cleaned) > 2 else ''
            description = cleaned[41] if len(cleaned) > 41 else ''
            rarity_str = cleaned[17] if len(cleaned) > 17 else 'common'

            # Format number
            number = str(number).strip()
            number_digits = ''.join(filter(str.isdigit, number))
            if number_digits:
                number = number_digits.zfill(6)

            return {
                'number': number,
                'title': title if title else f"Carte Postale N° {number}",
                'description': description,
                'keywords': keywords,
                'rarity': self.map_rarity(rarity_str),
            }
        except Exception:
            return None

    def map_rarity(self, value):
        """Map rarity string to model choice"""
        if not value:
            return 'common'

        value = str(value).lower().strip()

        mapping = {
            'common': 'common', 'commune': 'common', 'c': 'common',
            '0': 'common', '1': 'common',
            'rare': 'rare', 'r': 'rare', '2': 'rare',
            'very_rare': 'very_rare', 'very rare': 'very_rare',
            'tres_rare': 'very_rare', 'très rare': 'very_rare',
            'tres rare': 'very_rare', 'vr': 'very_rare', '3': 'very_rare',
        }

        return mapping.get(value, 'common')

    def import_postcards(self, data, update_existing=False):
        """Import postcards to database"""
        created = 0
        updated = 0
        errors = 0

        self.stdout.write(f"\nImporting {len(data)} postcards...")

        with transaction.atomic():
            for i, record in enumerate(data):
                try:
                    if update_existing:
                        postcard, is_new = Postcard.objects.update_or_create(
                            number=record['number'],
                            defaults={
                                'title': record['title'][:500],
                                'description': record['description'],
                                'keywords': record['keywords'],
                                'rarity': record['rarity'],
                            }
                        )
                        if is_new:
                            created += 1
                        else:
                            updated += 1
                    else:
                        postcard, is_new = Postcard.objects.get_or_create(
                            number=record['number'],
                            defaults={
                                'title': record['title'][:500],
                                'description': record['description'],
                                'keywords': record['keywords'],
                                'rarity': record['rarity'],
                            }
                        )
                        if is_new:
                            created += 1
                        else:
                            updated += 1

                    if (i + 1) % 200 == 0:
                        self.stdout.write(f"  Progress: {i + 1}/{len(data)}")

                except Exception as e:
                    errors += 1
                    if errors < 10:
                        self.stdout.write(self.style.WARNING(
                            f"  Error on {record.get('number')}: {e}"
                        ))

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(f"✓ Created: {created}"))
        self.stdout.write(self.style.SUCCESS(f"✓ Updated: {updated}"))
        if errors:
            self.stdout.write(self.style.WARNING(f"✗ Errors: {errors}"))

        # Final count
        total = Postcard.objects.count()
        self.stdout.write(f"\nTotal postcards in database: {total}")
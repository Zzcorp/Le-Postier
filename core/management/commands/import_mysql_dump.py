# core/management/commands/import_mysql_dump.py
"""
Import postcards from MySQL dump file into Django PostgreSQL database.
Parses MySQL INSERT statements and creates Postcard objects.

Usage: python manage.py import_mysql_dump /tmp/dump.sql
"""

import re
import os
from django.core.management.base import BaseCommand
from core.models import Postcard


class Command(BaseCommand):
    help = 'Import postcards from MySQL dump file'

    def add_arguments(self, parser):
        parser.add_argument('dump_file', type=str, help='Path to MySQL dump file')
        parser.add_argument('--dry-run', action='store_true', help='Test without saving')
        parser.add_argument('--limit', type=int, help='Limit number of records to import')
        parser.add_argument('--clear', action='store_true', help='Clear existing postcards first')

    def handle(self, *args, **options):
        dump_file = options['dump_file']
        dry_run = options['dry_run']
        limit = options.get('limit')
        clear_existing = options['clear']

        if not os.path.exists(dump_file):
            self.stdout.write(self.style.ERROR(f'File not found: {dump_file}'))
            return

        self.stdout.write(f'Reading MySQL dump from: {dump_file}')
        self.stdout.write(f'Dry run: {dry_run}')

        # Clear existing if requested
        if clear_existing and not dry_run:
            self.stdout.write('Clearing existing postcards...')
            count = Postcard.objects.count()
            Postcard.objects.all().delete()
            self.stdout.write(f'  Deleted {count} existing postcards')

        # Parse the dump file
        postcards_data = self.parse_mysql_dump(dump_file, limit)

        self.stdout.write(f'\nFound {len(postcards_data)} postcard records')

        if not postcards_data:
            self.stdout.write(self.style.WARNING('No data found to import'))
            return

        # Import postcards
        created = 0
        updated = 0
        errors = 0

        for i, data in enumerate(postcards_data):
            try:
                result = self.import_postcard(data, dry_run)
                if result == 'created':
                    created += 1
                elif result == 'updated':
                    updated += 1

                if (i + 1) % 100 == 0:
                    self.stdout.write(f'  Progress: {i + 1}/{len(postcards_data)}')

            except Exception as e:
                errors += 1
                if errors < 10:
                    self.stdout.write(self.style.WARNING(f'  Error on record {i + 1}: {e}'))

        # Summary
        self.stdout.write('\n' + '=' * 60)
        if dry_run:
            self.stdout.write(self.style.WARNING('[DRY RUN - No changes made]'))
        self.stdout.write(self.style.SUCCESS(
            f'Created: {created} | Updated: {updated} | Errors: {errors}'
        ))
        self.stdout.write('=' * 60)

        # Show sample of what was imported
        if not dry_run and created > 0:
            self.stdout.write('\nSample of imported postcards:')
            for p in Postcard.objects.all()[:5]:
                self.stdout.write(f'  {p.number}: {p.title[:50]}...')

    def parse_mysql_dump(self, dump_file, limit=None):
        """Parse MySQL dump file and extract postcard data"""
        postcards = []

        # Column mapping from MySQL to our model
        # Based on: id, label, mots_clefs, type, catégorie, prix_achat, date_acquisition,
        # donateur, date_modif, édition, nom, interne, année, statut, tampon, état_général,
        # qualité_photo, rareté, interêt, pivée, note_admin, note_visiteur, pos_x, pos_y,
        # angle_photo, pos_x_photo, pos_y_photo, adresse_nom, adresse_1, adresse_2,
        # adresse_ville, adresse_pays, valeur, précédent, suivant, pays, région, fleuve,
        # pk, rive, sens, description, remarques, message

        column_indices = {
            'id': 0,
            'label': 1,          # -> title
            'mots_clefs': 2,     # -> keywords
            'rareté': 17,        # -> rarity
            'description': 41,   # -> description
        }

        with open(dump_file, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()

        # Find all INSERT statements for the postcards table
        # Pattern to match: INSERT INTO `db_cp_16_02_2024` (...) VALUES (data);
        insert_pattern = re.compile(
            r"INSERT INTO `db_cp_16_02_2024`[^V]*VALUES\s*\((.+?)\);",
            re.DOTALL | re.IGNORECASE
        )

        matches = insert_pattern.findall(content)
        self.stdout.write(f'  Found {len(matches)} INSERT statements')

        if not matches:
            # Try alternative parsing - line by line for VALUES
            self.stdout.write('  Trying alternative parsing method...')
            postcards = self.parse_values_directly(content, limit)
            return postcards

        for match in matches:
            # Each match contains the VALUES part, possibly multiple rows
            # Split by ),( to get individual rows
            rows = self.split_values(match)

            for row in rows:
                try:
                    data = self.parse_row(row, column_indices)
                    if data:
                        postcards.append(data)

                        if limit and len(postcards) >= limit:
                            return postcards
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f'  Failed to parse row: {e}'))

        return postcards

    def parse_values_directly(self, content, limit=None):
        """Alternative parsing method - extract VALUES directly"""
        postcards = []

        # Find all VALUES (...) patterns
        # This regex captures everything between VALUES and the closing );
        values_pattern = re.compile(
            r"VALUES\s*\((.+?)\)(?:,\s*\(|;)",
            re.DOTALL
        )

        # Also try to find individual value rows
        row_pattern = re.compile(
            r"\((\d+),\s*'([^']*)',\s*'([^']*)'",  # id, label, mots_clefs start
            re.DOTALL
        )

        # Find lines containing VALUES
        lines = content.split('\n')
        current_values = []
        in_values = False

        for line in lines:
            if 'VALUES' in line:
                in_values = True
                # Get everything after VALUES
                idx = line.find('VALUES')
                current_values.append(line[idx + 6:])
            elif in_values:
                if line.strip().endswith(';'):
                    current_values.append(line)
                    in_values = False
                    # Process collected values
                    full_values = ' '.join(current_values)
                    rows = self.extract_rows_from_values(full_values)
                    for row in rows:
                        if row:
                            postcards.append(row)
                            if limit and len(postcards) >= limit:
                                return postcards
                    current_values = []
                else:
                    current_values.append(line)

        return postcards

    def extract_rows_from_values(self, values_str):
        """Extract individual rows from a VALUES string"""
        rows = []

        # Remove leading/trailing whitespace and the final semicolon
        values_str = values_str.strip().rstrip(';').strip()

        # Split by '),(' but be careful with nested parentheses and quotes
        current_row = []
        paren_depth = 0
        in_string = False
        escape_next = False
        row_start = -1

        i = 0
        while i < len(values_str):
            char = values_str[i]

            if escape_next:
                escape_next = False
                i += 1
                continue

            if char == '\\':
                escape_next = True
                i += 1
                continue

            if char == "'" and not in_string:
                in_string = True
            elif char == "'" and in_string:
                in_string = False
            elif char == '(' and not in_string:
                if paren_depth == 0:
                    row_start = i + 1
                paren_depth += 1
            elif char == ')' and not in_string:
                paren_depth -= 1
                if paren_depth == 0 and row_start >= 0:
                    row_content = values_str[row_start:i]
                    parsed = self.parse_single_row(row_content)
                    if parsed:
                        rows.append(parsed)
                    row_start = -1

            i += 1

        return rows

    def parse_single_row(self, row_str):
        """Parse a single row of VALUES into a dictionary"""
        # Split by comma, respecting quoted strings
        values = []
        current = []
        in_string = False
        escape_next = False

        for char in row_str:
            if escape_next:
                current.append(char)
                escape_next = False
                continue

            if char == '\\':
                escape_next = True
                current.append(char)
                continue

            if char == "'" and not in_string:
                in_string = True
                current.append(char)
            elif char == "'" and in_string:
                in_string = False
                current.append(char)
            elif char == ',' and not in_string:
                values.append(''.join(current).strip())
                current = []
            else:
                current.append(char)

        if current:
            values.append(''.join(current).strip())

        if len(values) < 3:
            return None

        # Clean values - remove surrounding quotes
        def clean_value(v):
            v = v.strip()
            if v.startswith("'") and v.endswith("'"):
                v = v[1:-1]
            elif v == 'NULL':
                v = ''
            # Unescape
            v = v.replace("\\'", "'").replace("\\n", "\n").replace("\\r", "")
            return v

        try:
            # Map to our fields
            # Index: 0=id, 1=label, 2=mots_clefs, ... 17=rareté, ... 41=description
            postcard_id = clean_value(values[0])
            label = clean_value(values[1]) if len(values) > 1 else ''
            mots_clefs = clean_value(values[2]) if len(values) > 2 else ''
            rarete = clean_value(values[17]) if len(values) > 17 else ''
            description = clean_value(values[41]) if len(values) > 41 else ''

            # Format the number with leading zeros (6 digits)
            try:
                number = str(int(postcard_id)).zfill(6)
            except:
                number = postcard_id.zfill(6)

            # Map rarity
            rarity_map = {
                'commune': 'common',
                'common': 'common',
                'c': 'common',
                '': 'common',
                'rare': 'rare',
                'r': 'rare',
                'très rare': 'very_rare',
                'tres rare': 'very_rare',
                'very_rare': 'very_rare',
                'tr': 'very_rare',
            }
            rarity = rarity_map.get(rarete.lower().strip(), 'common')

            return {
                'number': number,
                'title': label or f'Carte Postale N° {number}',
                'keywords': mots_clefs,
                'description': description,
                'rarity': rarity,
            }

        except Exception as e:
            return None

    def split_values(self, values_str):
        """Split VALUES string into individual rows"""
        # This handles the case where multiple rows are in one INSERT
        rows = []
        current = []
        paren_depth = 0
        in_string = False

        for i, char in enumerate(values_str):
            if char == "'" and (i == 0 or values_str[i-1] != '\\'):
                in_string = not in_string

            if not in_string:
                if char == '(':
                    paren_depth += 1
                    if paren_depth == 1:
                        current = []
                        continue
                elif char == ')':
                    paren_depth -= 1
                    if paren_depth == 0:
                        rows.append(''.join(current))
                        continue

            if paren_depth > 0:
                current.append(char)

        return rows

    def parse_row(self, row_str, column_indices):
        """Parse a single VALUES row string into a dictionary"""
        return self.parse_single_row(row_str)

    def import_postcard(self, data, dry_run=False):
        """Import a single postcard record"""
        number = data['number']
        title = data['title']
        keywords = data.get('keywords', '')
        description = data.get('description', '')
        rarity = data.get('rarity', 'common')

        if dry_run:
            self.stdout.write(f'  [DRY RUN] Would import: {number} - {title[:40]}')
            return 'created'

        postcard, created = Postcard.objects.update_or_create(
            number=number,
            defaults={
                'title': title,
                'keywords': keywords,
                'description': description,
                'rarity': rarity,
            }
        )

        return 'created' if created else 'updated'
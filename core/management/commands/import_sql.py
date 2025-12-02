from django.core.management.base import BaseCommand
from core.models import Postcard, Theme
import re


class Command(BaseCommand):
    help = 'Import postcards from MySQL SQL dump'

    def add_arguments(self, parser):
        parser.add_argument('--sql', type=str, required=True, help='Path to SQL file')
        parser.add_argument('--test', action='store_true', help='Test with 10 items only')
        parser.add_argument('--show-structure', action='store_true', help='Show SQL structure')

    def handle(self, *args, **options):
        sql_file = options['sql']
        test_mode = options.get('test', False)
        show_structure = options.get('show_structure', False)

        self.stdout.write('📋 Reading SQL file...')

        with open(sql_file, 'r', encoding='utf-8', errors='ignore') as f:
            sql_content = f.read()

        if show_structure:
            self.show_structure(sql_content)
            return

        # Parse the SQL
        records = self.parse_sql(sql_content)

        self.stdout.write(f'📦 Found {len(records)} records')

        if len(records) == 0:
            self.stdout.write(self.style.ERROR('No records found!'))
            return

        if test_mode:
            records = records[:10]
            self.stdout.write('🧪 Test mode: processing first 10 records')

        # Import records
        count = 0
        for record in records:
            if self.import_record(record):
                count += 1

        self.stdout.write(self.style.SUCCESS(f'\n✅ Imported {count} postcards'))
        self.print_summary()

    def show_structure(self, sql_content):
        """Show SQL file structure"""
        lines = sql_content.split('\n')

        self.stdout.write('\n📄 First 30 lines of SQL file:')
        self.stdout.write('=' * 60)
        for i, line in enumerate(lines[:30]):
            self.stdout.write(f'{i + 1:3}: {line[:100]}')

        # Find tables
        self.stdout.write('\n📋 Tables found:')
        tables = re.findall(r'CREATE TABLE `(\w+)`', sql_content, re.IGNORECASE)
        for t in tables:
            self.stdout.write(f'  - {t}')

        # Count inserts
        self.stdout.write('\n📥 INSERT statements found:')
        inserts = re.findall(r'INSERT INTO `(\w+)`', sql_content, re.IGNORECASE)
        from collections import Counter
        for table, count in Counter(inserts).items():
            self.stdout.write(f'  - {table}: {count} inserts')

        # Show structure
        create_match = re.search(r'CREATE TABLE `\w+` \((.*?)\) ENGINE', sql_content, re.DOTALL)
        if create_match:
            self.stdout.write('\n📋 Table structure:')
            for line in create_match.group(1).split('\n'):
                line = line.strip()
                if line and '`' in line:
                    self.stdout.write(f'  {line[:80]}')

    def parse_sql(self, sql_content):
        """Parse INSERT statements from SQL dump"""
        records = []

        # Find all INSERT statements for our table
        # Pattern for: INSERT INTO `table` (`cols`) VALUES (val1), (val2), ...;

        insert_pattern = r"INSERT INTO `db_cp_16_02_2024` \(`([^`]+(?:`, `[^`]+)*)`\) VALUES\s*(.+?);"
        matches = re.findall(insert_pattern, sql_content, re.DOTALL | re.IGNORECASE)

        for columns_str, values_str in matches:
            # Parse column names
            columns = [c.strip().strip('`') for c in columns_str.split('`, `')]

            # Parse value sets - handle (val1, val2), (val3, val4), ...
            value_sets = self.extract_value_sets(values_str)

            for values in value_sets:
                if len(values) == len(columns):
                    record = dict(zip(columns, values))
                    records.append(record)
                else:
                    self.stdout.write(f'⚠️  Column mismatch: {len(columns)} cols vs {len(values)} vals')

        return records

    def extract_value_sets(self, values_str):
        """Extract individual value tuples from VALUES clause"""
        value_sets = []

        # Split by ), ( but be careful with nested parentheses and quotes
        current_set = []
        current_value = []
        in_quotes = False
        quote_char = None
        paren_depth = 0
        escape_next = False

        for char in values_str:
            if escape_next:
                current_value.append(char)
                escape_next = False
                continue

            if char == '\\':
                escape_next = True
                current_value.append(char)
                continue

            if char in ("'", '"') and not in_quotes:
                in_quotes = True
                quote_char = char
                current_value.append(char)
            elif char == quote_char and in_quotes:
                in_quotes = False
                quote_char = None
                current_value.append(char)
            elif char == '(' and not in_quotes:
                paren_depth += 1
                if paren_depth == 1:
                    current_value = []
                    continue
                current_value.append(char)
            elif char == ')' and not in_quotes:
                paren_depth -= 1
                if paren_depth == 0:
                    # End of value set
                    if current_value:
                        current_set.append(self.clean_value(''.join(current_value)))
                    if current_set:
                        value_sets.append(current_set)
                    current_set = []
                    current_value = []
                    continue
                current_value.append(char)
            elif char == ',' and not in_quotes and paren_depth == 1:
                # Separator between values in a set
                current_set.append(self.clean_value(''.join(current_value)))
                current_value = []
            else:
                current_value.append(char)

        return value_sets

    def clean_value(self, value):
        """Clean a SQL value"""
        if not value:
            return ''

        value = value.strip()

        if value.upper() == 'NULL':
            return ''

        # Remove surrounding quotes
        if len(value) >= 2:
            if (value[0] == "'" and value[-1] == "'") or (value[0] == '"' and value[-1] == '"'):
                value = value[1:-1]

        # Unescape
        value = value.replace("\\'", "'")
        value = value.replace('\\"', '"')
        value = value.replace('\\\\', '\\')
        value = value.replace('\\n', '\n')
        value = value.replace('\\r', '')

        return value

    def import_record(self, record):
        """Import a single postcard record"""
        try:
            # Map your SQL columns to Django model
            # Your columns: id, label, mots_clefs, type, catégorie, ..., rareté, ..., description

            number = str(record.get('id', '0')).strip().zfill(4)
            title = record.get('label', '') or f'Carte Postale {number}'
            keywords = record.get('mots_clefs', '') or ''
            description = record.get('description', '') or ''
            rarity_raw = record.get('rareté', '') or 'commune'

            # Clean title (replace backslashes with quotes)
            title = title.replace('\\', '"')

            # Map rarity
            rarity_map = {
                'commune': 'common',
                'common': 'common',
                'courante': 'common',
                'rare': 'rare',
                'très rare': 'very_rare',
                'tres rare': 'very_rare',
                'très-rare': 'very_rare',
                'very_rare': 'very_rare',
                'exceptionnelle': 'very_rare',
            }
            rarity = rarity_map.get(rarity_raw.lower().strip(), 'common')

            # Create or update postcard
            postcard, created = Postcard.objects.update_or_create(
                number=number,
                defaults={
                    'title': title[:500],
                    'description': description[:1000],
                    'keywords': keywords[:1000],
                    'rarity': rarity,
                }
            )

            status = '✅ Created' if created else '🔄 Updated'
            self.stdout.write(f'{status} {number}: {title[:50]}...')

            return True

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error: {e}'))
            self.stdout.write(self.style.ERROR(f'   Record: {record}'))
            return False

    def print_summary(self):
        """Print import summary"""
        total = Postcard.objects.count()
        common = Postcard.objects.filter(rarity='common').count()
        rare = Postcard.objects.filter(rarity='rare').count()
        very_rare = Postcard.objects.filter(rarity='very_rare').count()

        self.stdout.write(self.style.SUCCESS('\n' + '=' * 50))
        self.stdout.write(self.style.SUCCESS('📊 IMPORT SUMMARY'))
        self.stdout.write(self.style.SUCCESS('=' * 50))
        self.stdout.write(f'Total postcards:  {total}')
        self.stdout.write(f'  - Common:       {common}')
        self.stdout.write(f'  - Rare:         {rare}')
        self.stdout.write(f'  - Very Rare:    {very_rare}')
from django.core.management.base import BaseCommand
from core.models import Postcard, Theme

# Handle MySQL import
try:
    import MySQLdb
except ImportError:
    import pymysql

    pymysql.install_as_MySQLdb()
    import pymysql as MySQLdb

    MySQLdb.cursors = pymysql.cursors


class Command(BaseCommand):
    help = 'Import directly from MySQL database'

    def add_arguments(self, parser):
        parser.add_argument('--test', action='store_true', help='Test with 10 items only')
        parser.add_argument('--list-tables', action='store_true', help='List all tables')

    def handle(self, *args, **options):
        test_mode = options.get('test', False)
        list_tables = options.get('list_tables', False)

        self.stdout.write('🔌 Connecting to MySQL database...')

        try:
            import pymysql

            # Connect to your MySQL
            db = pymysql.connect(
                host='samatheynb.mysql.db',
                user='samatheynb',
                password='NoiretBlanc10',
                database='samatheynb',
                charset='utf8mb4',
                cursorclass=pymysql.cursors.DictCursor
            )

            self.stdout.write('✅ Connected!')

            cursor = db.cursor()

            # List all tables
            cursor.execute("SHOW TABLES")
            tables = cursor.fetchall()

            self.stdout.write('\n📋 Available tables:')
            table_names = []
            for table in tables:
                name = list(table.values())[0]
                table_names.append(name)
                self.stdout.write(f"  - {name}")

            if list_tables:
                # Show structure of each table
                for name in table_names:
                    self.stdout.write(f'\n📋 Structure of {name}:')
                    cursor.execute(f"DESCRIBE `{name}`")
                    cols = cursor.fetchall()
                    for col in cols:
                        self.stdout.write(f"    {col['Field']} ({col['Type']})")

                    # Show row count
                    cursor.execute(f"SELECT COUNT(*) as cnt FROM `{name}`")
                    count = cursor.fetchone()['cnt']
                    self.stdout.write(f"    → {count} rows")

                cursor.close()
                db.close()
                return

            # Ask which table to import
            self.stdout.write('\n')
            table_name = input("Enter table name to import: ").strip()

            if not table_name:
                self.stdout.write(self.style.ERROR('No table name provided'))
                return

            # Get columns
            cursor.execute(f"DESCRIBE `{table_name}`")
            columns = cursor.fetchall()

            self.stdout.write(f'\n📋 Columns in {table_name}:')
            col_names = []
            for col in columns:
                col_names.append(col['Field'])
                self.stdout.write(f"  - {col['Field']} ({col['Type']})")

            # Map columns
            self.stdout.write('\n🔗 Column mapping (press Enter to skip):')

            number_col = input(f"  Number column [{col_names}]: ").strip()
            title_col = input(f"  Title column [{col_names}]: ").strip()
            desc_col = input(f"  Description column (optional): ").strip()
            keywords_col = input(f"  Keywords column (optional): ").strip()
            rarity_col = input(f"  Rarity column (optional): ").strip()

            if not number_col or not title_col:
                self.stdout.write(self.style.ERROR('Number and Title columns are required'))
                return

            # Get data
            limit = ' LIMIT 10' if test_mode else ''
            cursor.execute(f"SELECT * FROM `{table_name}`{limit}")

            records = cursor.fetchall()
            self.stdout.write(f'\n📦 Found {len(records)} records')

            # Import each record
            count = 0
            for record in records:
                try:
                    number = str(record.get(number_col, '0')).strip().zfill(4)
                    title = str(record.get(title_col, '')).replace('\\', '"')
                    description = str(record.get(desc_col, '')) if desc_col else ''
                    keywords = str(record.get(keywords_col, '')) if keywords_col else ''
                    rarity_raw = str(record.get(rarity_col, 'commune')) if rarity_col else 'commune'

                    # Map rarity
                    rarity_map = {
                        'commune': 'common',
                        'rare': 'rare',
                        'très rare': 'very_rare',
                        'tres rare': 'very_rare',
                    }
                    rarity = rarity_map.get(rarity_raw.lower().strip(), 'common')

                    postcard, created = Postcard.objects.update_or_create(
                        number=number,
                        defaults={
                            'title': title[:500] if title else f'Carte Postale {number}',
                            'description': description[:1000],
                            'keywords': keywords[:1000],
                            'rarity': rarity,
                        }
                    )

                    status = '✅' if created else '🔄'
                    self.stdout.write(f'{status} {number}: {title[:40]}...')
                    count += 1

                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'❌ Error: {e}'))

            cursor.close()
            db.close()

            self.stdout.write(self.style.SUCCESS(f'\n✅ Imported {count} postcards'))
            self.stdout.write(f'Total in database: {Postcard.objects.count()}')

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Connection Error: {e}'))
            import traceback
            traceback.print_exc()
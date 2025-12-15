# core/management/commands/import_from_sql.py
"""
Import from SQL dump file
"""

import ftplib
import tempfile
import subprocess
from django.core.management.base import BaseCommand
from django.conf import settings


class Command(BaseCommand):
    help = 'Import database from SQL dump'

    def add_arguments(self, parser):
        parser.add_argument('--sql-file', type=str, help='Path to SQL file')
        parser.add_argument('--ftp-host', type=str, help='Download from FTP')
        parser.add_argument('--ftp-user', type=str)
        parser.add_argument('--ftp-pass', type=str)
        parser.add_argument('--ftp-path', type=str, default='/backup.sql')

    def handle(self, *args, **options):
        sql_file = options.get('sql_file')

        # Download from FTP if specified
        if options.get('ftp_host'):
            self.stdout.write('Downloading SQL from FTP...')
            sql_file = self.download_from_ftp(
                options['ftp_host'],
                options['ftp_user'],
                options['ftp_pass'],
                options['ftp_path']
            )

        if not sql_file:
            self.stdout.write(self.style.ERROR('No SQL file specified'))
            return

        # Import SQL
        self.stdout.write(f'Importing from {sql_file}...')

        db_settings = settings.DATABASES['default']

        if db_settings['ENGINE'] == 'django.db.backends.postgresql':
            self.import_postgresql(sql_file, db_settings)
        elif db_settings['ENGINE'] == 'django.db.backends.sqlite3':
            self.import_sqlite(sql_file, db_settings)
        else:
            self.stdout.write(self.style.ERROR(f"Unsupported database: {db_settings['ENGINE']}"))

    def download_from_ftp(self, host, user, password, path):
        """Download SQL file from FTP"""
        ftp = ftplib.FTP()
        ftp.connect(host, 21)
        ftp.login(user, password)

        with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.sql') as tmp:
            ftp.retrbinary(f'RETR {path}', tmp.write)
            tmp_path = tmp.name

        ftp.quit()
        return tmp_path

    def import_postgresql(self, sql_file, db_settings):
        """Import into PostgreSQL"""
        cmd = [
            'psql',
            '-h', db_settings['HOST'],
            '-U', db_settings['USER'],
            '-d', db_settings['NAME'],
            '-f', sql_file
        ]

        env = {'PGPASSWORD': db_settings['PASSWORD']}

        result = subprocess.run(cmd, env=env, capture_output=True, text=True)

        if result.returncode == 0:
            self.stdout.write(self.style.SUCCESS('✓ Import successful'))
        else:
            self.stdout.write(self.style.ERROR(f'Import failed: {result.stderr}'))

    def import_sqlite(self, sql_file, db_settings):
        """Import into SQLite"""
        cmd = ['sqlite3', db_settings['NAME'], f'.read {sql_file}']
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0:
            self.stdout.write(self.style.SUCCESS('✓ Import successful'))
        else:
            self.stdout.write(self.style.ERROR(f'Import failed: {result.stderr}'))
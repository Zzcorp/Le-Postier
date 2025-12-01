from django.core.management.base import BaseCommand
from django.core.files import File
from django.core.files.temp import NamedTemporaryFile
from core.models import Postcard
import ftplib
import os
import tempfile
import MySQLdb  # or import pymysql
from urllib.request import urlopen

class Command(BaseCommand):
    help = 'Import postcards from OVH FTP server'

    def add_arguments(self, parser):
        parser.add_argument('--ftp-host', type=str, help='FTP host')
        parser.add_argument('--ftp-user', type=str, help='FTP username')
        parser.add_argument('--ftp-pass', type=str, help='FTP password')
        parser.add_argument('--db-host', type=str, help='MySQL host')
        parser.add_argument('--db-name', type=str, help='Database name')
        parser.add_argument('--db-user', type=str, help='Database user')
        parser.add_argument('--db-pass', type=str, help='Database password')

    def handle(self, *args, **options):
        # Method 1: Direct FTP Connection
        self.import_from_ftp(options)

        # Method 2: Import from existing MySQL database
        self.import_from_mysql(options)

    def import_from_ftp(self, options):
        """Import images directly from FTP"""
        ftp = ftplib.FTP(options['ftp_host'])
        ftp.login(options['ftp_user'], options['ftp_pass'])

        # Navigate to postcards directory
        ftp.cwd('/path/to/postcards')

        # Get list of files
        files = ftp.nlst()

        for filename in files:
            if filename.endswith(('.jpg', '.jpeg', '.png')):
                # Download to temporary file
                temp_file = tempfile.NamedTemporaryFile(delete=False)
                ftp.retrbinary(f'RETR {filename}', temp_file.write)
                temp_file.close()

                # Create postcard object
                with open(temp_file.name, 'rb') as f:
                    postcard_number = filename.split('_')[0]  # Adjust based on naming

                    # Check if postcard exists
                    postcard, created = Postcard.objects.get_or_create(
                        number=postcard_number,
                        defaults={'title': f'Carte {postcard_number}'}
                    )

                    # Save image
                    if 'recto' in filename or 'Grande' in filename:
                        postcard.front_image.save(filename, File(f))
                    elif 'verso' in filename or 'Dos' in filename:
                        postcard.back_image.save(filename, File(f))

                os.unlink(temp_file.name)

        ftp.quit()
        self.stdout.write(self.style.SUCCESS('Successfully imported from FTP'))

    def import_from_mysql(self, options):
        """Import from existing MySQL database"""
        # Connect to MySQL
        db = MySQLdb.connect(
            host=options['db_host'],
            user=options['db_user'],
            passwd=options['db_pass'],
            db=options['db_name'],
            charset='utf8mb4'
        )

        cursor = db.cursor()

        # Get postcards data
        cursor.execute("""
            SELECT number, title, description, keywords, rarity, 
                   front_image_path, back_image_path
            FROM postcards
        """)

        for row in cursor.fetchall():
            number, title, description, keywords, rarity, front_path, back_path = row

            # Clean title
            title = title.replace('\\', '"') if title else ''

            # Create postcard
            postcard, created = Postcard.objects.get_or_create(
                number=number,
                defaults={
                    'title': title,
                    'description': description or '',
                    'keywords': keywords or '',
                    'rarity': rarity or 'common'
                }
            )

            # Download images from URL if stored as URLs
            if front_path and front_path.startswith('http'):
                img_temp = NamedTemporaryFile(delete=True)
                img_temp.write(urlopen(front_path).read())
                img_temp.flush()
                postcard.front_image.save(f"{number}_front.jpg", File(img_temp))

            if back_path and back_path.startswith('http'):
                img_temp = NamedTemporaryFile(delete=True)
                img_temp.write(urlopen(back_path).read())
                img_temp.flush()
                postcard.back_image.save(f"{number}_back.jpg", File(img_temp))

        cursor.close()
        db.close()

        self.stdout.write(self.style.SUCCESS('Successfully imported from MySQL'))
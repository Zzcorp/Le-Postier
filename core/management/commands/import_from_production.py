import os
import ftplib
import MySQLdb
import ssl
from django.core.management.base import BaseCommand
from django.core.files import File
from django.core.files.temp import NamedTemporaryFile
from django.conf import settings
from core.models import Postcard, Theme, CustomUser
from PIL import Image
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Import postcards from OVH MySQL database and FTP server'

    def add_arguments(self, parser):
        parser.add_argument(
            '--test',
            action='store_true',
            help='Test mode - only import first 10 postcards'
        )
        parser.add_argument(
            '--skip-images',
            action='store_true',
            help='Skip image import, only import metadata'
        )
        parser.add_argument(
            '--skip-metadata',
            action='store_true',
            help='Skip metadata import, only import images'
        )

    def handle(self, *args, **options):
        self.test_mode = options.get('test', False)
        self.skip_images = options.get('skip_images', False)
        self.skip_metadata = options.get('skip_metadata', False)

        self.stdout.write(self.style.SUCCESS('Starting import process...'))

        if not self.skip_metadata:
            self.import_from_mysql()

        if not self.skip_images:
            self.import_images_from_ftp()

        self.organize_themes()
        self.generate_report()

        self.stdout.write(self.style.SUCCESS('Import completed successfully!'))

    def import_from_mysql(self):
        """Import postcard metadata from MySQL database"""
        self.stdout.write('Connecting to MySQL database...')

        try:
            # Connect to MySQL database
            connection = MySQLdb.connect(
                host='samatheynb.mysql.db',
                user='samatheynb',
                passwd='NoiretBlanc10',
                db='samatheynb',
                charset='utf8mb4',
                ssl_mode='REQUIRED',
                ssl={'ssl_disabled': False}
            )

            cursor = connection.cursor(MySQLdb.cursors.DictCursor)

            # Assuming your postcards are in a table - adjust table name as needed
            # You'll need to verify the actual table structure
            query = """
                SELECT 
                    numero as number,
                    titre as title,
                    description,
                    mots_cles as keywords,
                    rarete as rarity,
                    date_creation as created_date
                FROM cartes_postales
                ORDER BY numero
            """

            if self.test_mode:
                query += " LIMIT 10"

            cursor.execute(query)
            postcards_data = cursor.fetchall()

            self.stdout.write(f'Found {len(postcards_data)} postcards in database')

            for row in postcards_data:
                self.process_postcard_metadata(row)

            cursor.close()
            connection.close()

        except MySQLdb.Error as e:
            self.stdout.write(self.style.ERROR(f'MySQL Error: {e}'))
            # Try alternative connection method if SSL fails
            self.import_from_mysql_alternative()
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Unexpected error: {e}'))

    def import_from_mysql_alternative(self):
        """Alternative MySQL import without SSL"""
        try:
            connection = MySQLdb.connect(
                host='samatheynb.mysql.db',
                user='samatheynb',
                passwd='NoiretBlanc10',
                db='samatheynb',
                charset='utf8mb4'
            )

            cursor = connection.cursor()

            # Get table structure first
            cursor.execute("SHOW TABLES")
            tables = cursor.fetchall()
            self.stdout.write(f'Available tables: {tables}')

            # Find the postcards table - adjust based on actual table name
            postcard_table = None
            for table in tables:
                if 'postale' in table[0].lower() or 'carte' in table[0].lower():
                    postcard_table = table[0]
                    break

            if postcard_table:
                # Get column names
                cursor.execute(f"DESCRIBE {postcard_table}")
                columns = cursor.fetchall()
                self.stdout.write(f'Columns in {postcard_table}: {columns}')

                # Fetch data
                cursor.execute(f"SELECT * FROM {postcard_table}")
                postcards_data = cursor.fetchall()

                # Process data based on column structure
                for row in postcards_data:
                    self.process_postcard_row(row, columns)

            cursor.close()
            connection.close()

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Alternative connection failed: {e}'))

    def process_postcard_metadata(self, row):
        """Process a single postcard metadata row"""
        try:
            # Clean and prepare data
            number = str(row.get('number', '')).strip().zfill(4)  # Format as 0001, 0002, etc.
            title = row.get('title', f'Carte Postale {number}')

            # Clean title - replace backslashes with quotes
            if title:
                title = title.replace('\\', '"')

            # Determine rarity
            rarity_map = {
                'commune': 'common',
                'rare': 'rare',
                'très rare': 'very_rare',
                'tres rare': 'very_rare'
            }
            rarity = rarity_map.get(
                str(row.get('rarity', 'commune')).lower().strip(),
                'common'
            )

            # Create or update postcard
            postcard, created = Postcard.objects.update_or_create(
                number=number,
                defaults={
                    'title': title[:500],  # Ensure it fits in the field
                    'description': row.get('description', ''),
                    'keywords': row.get('keywords', ''),
                    'rarity': rarity,
                }
            )

            action = 'Created' if created else 'Updated'
            self.stdout.write(f'{action} postcard {number}: {title[:50]}...')

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error processing postcard {row}: {e}')
            )

    def import_images_from_ftp(self):
        """Import images from OVH FTP server"""
        self.stdout.write('Connecting to FTP server...')

        try:
            # Connect to FTP
            ftp = ftplib.FTP_TLS() if hasattr(ftplib, 'FTP_TLS') else ftplib.FTP()
            ftp.connect('ftp.cluster028.hosting.ovh.net', 21)
            ftp.login('your-ftp-username', 'your-ftp-password')  # Replace with actual credentials

            # Navigate to postcards directory
            ftp.cwd('/www/postcards/')  # Adjust path as needed

            # Get list of files
            files = []
            ftp.retrlines('LIST', lambda x: files.append(x.split()[-1]))

            self.stdout.write(f'Found {len(files)} files on FTP')

            # Process files
            processed = 0
            for filename in files:
                if self.test_mode and processed >= 10:
                    break

                if filename.lower().endswith(('.jpg', '.jpeg', '.png')):
                    if self.process_ftp_image(ftp, filename):
                        processed += 1

            ftp.quit()
            self.stdout.write(f'Processed {processed} images')

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'FTP Error: {e}'))

    def process_ftp_image(self, ftp, filename):
        """Process a single image from FTP"""
        try:
            # Parse filename to determine postcard number and image type
            # Expected formats: 
            # - 0001_Grande.jpg
            # - 0001_Dos.jpg
            # - 0001_Vignette.jpg
            # - 0001_Zoom.jpg

            base = filename.rsplit('.', 1)[0]  # Remove extension
            parts = base.split('_')

            if len(parts) < 2:
                return False

            number = parts[0].zfill(4)  # Ensure 4 digits
            image_type = parts[1].lower()

            # Try to find the postcard
            try:
                postcard = Postcard.objects.get(number=number)
            except Postcard.DoesNotExist:
                # Create postcard if it doesn't exist
                postcard = Postcard.objects.create(
                    number=number,
                    title=f'Carte Postale {number}'
                )
                self.stdout.write(f'Created new postcard for {number}')

            # Download image to temporary file
            temp_file = NamedTemporaryFile(delete=True, suffix='.jpg')
            ftp.retrbinary(f'RETR {filename}', temp_file.write)
            temp_file.seek(0)

            # Process and save based on type
            saved = False

            if 'vignette' in image_type:
                # Optimize vignette size
                img = self.optimize_image(temp_file, max_width=300, quality=85)
                postcard.vignette_image.save(f'{number}_vignette.jpg', img)
                saved = True
                self.stdout.write(f'✓ Vignette for {number}')

            elif 'grande' in image_type:
                # Optimize grande size
                img = self.optimize_image(temp_file, max_width=800, quality=90)
                postcard.grande_image.save(f'{number}_grande.jpg', img)
                saved = True
                self.stdout.write(f'✓ Grande for {number}')

            elif 'dos' in image_type:
                # Optimize dos size
                img = self.optimize_image(temp_file, max_width=800, quality=90)
                postcard.dos_image.save(f'{number}_dos.jpg', img)
                saved = True
                self.stdout.write(f'✓ Dos for {number}')

            elif 'zoom' in image_type:
                # Keep high quality for zoom
                img = self.optimize_image(temp_file, max_width=1600, quality=95)
                postcard.zoom_image.save(f'{number}_zoom.jpg', img)
                saved = True
                self.stdout.write(f'✓ Zoom for {number}')

            temp_file.close()
            return saved

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error processing {filename}: {e}')
            )
            return False

    def optimize_image(self, image_file, max_width=800, quality=90):
        """Optimize image size and quality"""
        try:
            img = Image.open(image_file)

            # Convert RGBA to RGB if necessary
            if img.mode in ('RGBA', 'LA', 'P'):
                rgb_img = Image.new('RGB', img.size, (255, 255, 255))
                rgb_img.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                img = rgb_img

            # Resize if too large
            if img.width > max_width:
                ratio = max_width / img.width
                new_height = int(img.height * ratio)
                img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)

            # Save to new temporary file
            output = NamedTemporaryFile(delete=True, suffix='.jpg')
            img.save(output, 'JPEG', quality=quality, optimize=True)
            output.seek(0)

            return File(output)

        except Exception as e:
            self.stdout.write(self.style.WARNING(f'Could not optimize image: {e}'))
            image_file.seek(0)
            return File(image_file)

    def organize_themes(self):
        """Create and organize themes"""
        themes_data = [
            ('Accident du pont de l\'archevêché', ['accident', 'archevêché']),
            ('Ascenseur', ['ascenseur']),
            ('Spa français', ['spa français']),
            ('Championnat du monde de natation', ['championnat', 'natation']),
            ('Bateau touriste', ['bateau', 'touriste']),
            ('Yacht "Le Druide"', ['yacht', 'druide']),
            ('Machine de Marly', ['machine', 'marly']),
            ('Système Gabet', ['système gabet', 'gabet']),
            ('Traversée de Paris à la nage', ['traversée', 'paris', 'nage']),
            ('Lebaudy', ['lebaudy']),
            ('Maison Pasquet', ['maison pasquet', 'pasquet']),
            ('Vieux garçon', ['vieux garçon']),
            ('Pénichienne', ['pénichienne']),
            ('Au rendez-vous de la marine', ['rendez-vous', 'marine']),
            ('Tanton', ['tanton']),
            ('Funiculaire', ['funiculaire']),
            ('Les bords de Seine', ['bords', 'seine']),
            ('Villennes', ['villennes']),
            ('Convert', ['convert']),
            ('Bords de Marne', ['bords', 'marne']),
            ('Fournaise', ['fournaise']),
            ('Jersey Farm', ['jersey farm']),
            ('Flottille de guerre', ['flottille', 'guerre']),
            ('Cafuts', ['cafuts']),
            ('Remorqueur "Electrolyse 3"', ['remorqueur', 'electrolyse']),
        ]

        for display_name, keywords in themes_data:
            theme, created = Theme.objects.get_or_create(
                display_name=display_name,
                defaults={
                    'name': display_name.lower().replace(' ', '_').replace('"', ''),
                    'order': len(Theme.objects.all())
                }
            )

            # Find matching postcards
            for keyword in keywords:
                postcards = Postcard.objects.filter(
                    models.Q(title__icontains=keyword) |
                    models.Q(keywords__icontains=keyword)
                )
                theme.postcards.add(*postcards)

            count = theme.postcards.count()
            self.stdout.write(f'Theme "{display_name}": {count} postcards')

    def generate_report(self):
        """Generate import report"""
        total_postcards = Postcard.objects.count()
        with_vignette = Postcard.objects.exclude(vignette_image='').count()
        with_grande = Postcard.objects.exclude(grande_image='').count()
        with_dos = Postcard.objects.exclude(dos_image='').count()
        with_zoom = Postcard.objects.exclude(zoom_image='').count()

        self.stdout.write(self.style.SUCCESS('\n=== IMPORT REPORT ==='))
        self.stdout.write(f'Total postcards: {total_postcards}')
        self.stdout.write(f'With vignette: {with_vignette}')
        self.stdout.write(f'With grande: {with_grande}')
        self.stdout.write(f'With dos: {with_dos}')
        self.stdout.write(f'With zoom: {with_zoom}')
        self.stdout.write(f'Themes created: {Theme.objects.count()}')
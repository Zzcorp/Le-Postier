from django.core.management.base import BaseCommand
from django.core.files import File
from django.core.files.temp import NamedTemporaryFile
from core.models import Postcard, Theme
from PIL import Image
import ftplib
import csv
import os


class Command(BaseCommand):
    help = 'Import postcards from CSV and FTP'

    def add_arguments(self, parser):
        parser.add_argument('--csv', type=str, help='Path to CSV file')
        parser.add_argument('--skip-images', action='store_true', help='Skip FTP images')
        parser.add_argument('--test', action='store_true', help='Test with 10 items only')

    def handle(self, *args, **options):
        csv_file = options.get('csv')
        skip_images = options.get('skip_images', False)
        test_mode = options.get('test', False)

        # Step 1: Import metadata from CSV
        if csv_file:
            self.stdout.write('📋 Importing metadata from CSV...')
            self.import_csv(csv_file, test_mode)

        # Step 2: Import images from FTP
        if not skip_images:
            self.stdout.write('📷 Importing images from FTP...')
            self.import_ftp_images(test_mode)

        # Step 3: Create themes
        self.stdout.write('🏷️  Creating themes...')
        self.create_themes()

        self.stdout.write(self.style.SUCCESS('✅ Import completed!'))
        self.print_summary()

    def import_csv(self, csv_path, test_mode):
        """Import postcard metadata from CSV"""
        count = 0

        with open(csv_path, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)

            for row in reader:
                if test_mode and count >= 10:
                    break

                try:
                    # Clean number (ensure 4 digits)
                    number = str(row.get('number', '')).strip().zfill(4)

                    # Clean title (replace backslashes)
                    title = row.get('title', f'Carte Postale {number}')
                    title = title.replace('\\', '"')

                    # Map rarity
                    rarity_map = {
                        'commune': 'common',
                        'common': 'common',
                        'rare': 'rare',
                        'très rare': 'very_rare',
                        'tres rare': 'very_rare',
                        'very_rare': 'very_rare',
                    }
                    rarity = rarity_map.get(
                        str(row.get('rarity', 'commune')).lower().strip(),
                        'common'
                    )

                    # Create or update postcard
                    postcard, created = Postcard.objects.update_or_create(
                        number=number,
                        defaults={
                            'title': title[:500],
                            'description': row.get('description', ''),
                            'keywords': row.get('keywords', ''),
                            'rarity': rarity,
                        }
                    )

                    status = '✅ Created' if created else '🔄 Updated'
                    self.stdout.write(f'{status} {number}: {title[:40]}...')
                    count += 1

                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'❌ Error on row {count}: {e}'))

        self.stdout.write(f'Imported {count} postcards')

    def import_ftp_images(self, test_mode):
        """Import images from FTP"""
        try:
            # Connect to FTP
            self.stdout.write('Connecting to FTP: ftp.cluster028.hosting.ovh.net...')
            ftp = ftplib.FTP('ftp.cluster028.hosting.ovh.net')
            ftp.login('samatheynb', 'NoiretBlanc10')

            # Try to find postcards directory
            directories = [
                '/www/postcards',
                '/www/images/postcards',
                '/postcards',
                '/www',
            ]

            found = False
            for directory in directories:
                try:
                    ftp.cwd(directory)
                    self.stdout.write(f'✅ Found directory: {directory}')
                    found = True
                    break
                except:
                    continue

            if not found:
                self.stdout.write('Current directory:')
                ftp.retrlines('LIST')
                self.stdout.write(self.style.WARNING('Please specify correct directory'))
                return

            # Get file list
            files = []
            ftp.retrlines('LIST', lambda x: files.append(x.split()[-1]))

            self.stdout.write(f'Found {len(files)} files')

            # Filter image files
            image_files = [f for f in files if f.lower().endswith(('.jpg', '.jpeg', '.png'))]

            if test_mode:
                image_files = image_files[:40]  # 10 postcards × 4 images each

            self.stdout.write(f'Processing {len(image_files)} image files...')

            # Process each file
            count = 0
            for filename in image_files:
                try:
                    if self.process_ftp_file(ftp, filename):
                        count += 1
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'❌ {filename}: {e}'))

            ftp.quit()
            self.stdout.write(f'Processed {count} images')

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'FTP Error: {e}'))

    def process_ftp_file(self, ftp, filename):
        """Process single FTP file"""
        # Expected formats:
        # 0001_Vignette.jpg
        # 0001_Grande.jpg
        # 0001_Dos.jpg
        # 0001_Zoom.jpg

        base = filename.rsplit('.', 1)[0]
        parts = base.split('_')

        if len(parts) < 2:
            return False

        number = parts[0].zfill(4)
        image_type = parts[1].lower()

        # Get or create postcard
        try:
            postcard = Postcard.objects.get(number=number)
        except Postcard.DoesNotExist:
            postcard = Postcard.objects.create(
                number=number,
                title=f'Carte Postale {number}'
            )

        # Download to temp file
        temp_file = NamedTemporaryFile(delete=False, suffix='.jpg')
        try:
            ftp.retrbinary(f'RETR {filename}', temp_file.write)
            temp_file.close()

            # Open and optimize image
            with open(temp_file.name, 'rb') as f:
                img = Image.open(f)

                # Convert RGBA to RGB
                if img.mode in ('RGBA', 'LA', 'P'):
                    rgb = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'RGBA':
                        rgb.paste(img, mask=img.split()[-1])
                    else:
                        rgb.paste(img)
                    img = rgb

                # Save optimized version
                optimized = NamedTemporaryFile(delete=False, suffix='.jpg')

                if 'vignette' in image_type:
                    # Small thumbnail
                    img.thumbnail((300, 200), Image.Resampling.LANCZOS)
                    img.save(optimized, 'JPEG', quality=85, optimize=True)
                    optimized.seek(0)
                    postcard.vignette_image.save(f'{number}_vignette.jpg', File(optimized))
                    self.stdout.write(f'  📸 Vignette: {number}')

                elif 'grande' in image_type:
                    # Medium size
                    img.thumbnail((800, 600), Image.Resampling.LANCZOS)
                    img.save(optimized, 'JPEG', quality=90, optimize=True)
                    optimized.seek(0)
                    postcard.grande_image.save(f'{number}_grande.jpg', File(optimized))
                    self.stdout.write(f'  📸 Grande: {number}')

                elif 'dos' in image_type:
                    # Back side
                    img.thumbnail((800, 600), Image.Resampling.LANCZOS)
                    img.save(optimized, 'JPEG', quality=90, optimize=True)
                    optimized.seek(0)
                    postcard.dos_image.save(f'{number}_dos.jpg', File(optimized))
                    self.stdout.write(f'  📸 Dos: {number}')

                elif 'zoom' in image_type:
                    # High resolution
                    if img.width > 1600:
                        img.thumbnail((1600, 1200), Image.Resampling.LANCZOS)
                    img.save(optimized, 'JPEG', quality=95, optimize=True)
                    optimized.seek(0)
                    postcard.zoom_image.save(f'{number}_zoom.jpg', File(optimized))
                    self.stdout.write(f'  📸 Zoom: {number}')

                optimized.close()
                os.unlink(optimized.name)

            return True

        finally:
            os.unlink(temp_file.name)

    def create_themes(self):
        """Create themes from keywords"""
        theme_data = [
            ('Accident du pont de l\'archevêché', ['accident', 'archevêché']),
            ('Ascenseur', ['ascenseur']),
            ('Bateau touriste', ['bateau', 'touriste']),
            ('Yacht Le Druide', ['yacht', 'druide']),
            ('Machine de Marly', ['machine', 'marly']),
            ('Bords de Seine', ['bords', 'seine']),
            ('Bords de Marne', ['marne']),
        ]

        for display_name, keywords in theme_data:
            theme, created = Theme.objects.get_or_create(
                display_name=display_name,
                defaults={
                    'name': display_name.lower().replace(' ', '_').replace("'", ''),
                }
            )

            # Find matching postcards
            from django.db.models import Q
            query = Q()
            for keyword in keywords:
                query |= Q(title__icontains=keyword)
                query |= Q(keywords__icontains=keyword)

            postcards = Postcard.objects.filter(query)
            theme.postcards.add(*postcards)

            count = theme.postcards.count()
            self.stdout.write(f'  🏷️  {display_name}: {count} postcards')

    def print_summary(self):
        """Print import summary"""
        total = Postcard.objects.count()
        with_vignette = Postcard.objects.exclude(vignette_image='').count()
        with_grande = Postcard.objects.exclude(grande_image='').count()
        with_dos = Postcard.objects.exclude(dos_image='').count()
        with_zoom = Postcard.objects.exclude(zoom_image='').count()

        self.stdout.write(self.style.SUCCESS('\n' + '=' * 50))
        self.stdout.write(self.style.SUCCESS('📊 IMPORT SUMMARY'))
        self.stdout.write(self.style.SUCCESS('=' * 50))
        self.stdout.write(f'Total postcards: {total}')
        self.stdout.write(f'With vignette:   {with_vignette}')
        self.stdout.write(f'With grande:     {with_grande}')
        self.stdout.write(f'With dos:        {with_dos}')
        self.stdout.write(f'With zoom:       {with_zoom}')
        self.stdout.write(f'Themes:          {Theme.objects.count()}')
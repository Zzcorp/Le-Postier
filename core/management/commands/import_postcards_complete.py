from django.core.management.base import BaseCommand
from django.core.files import File
from django.core.files.temp import NamedTemporaryFile
from core.models import Postcard, Theme
import ftplib
import os
import csv
from PIL import Image
from django.conf import settings
import requests


class Command(BaseCommand):
    help = 'Import postcards with proper organization'

    def add_arguments(self, parser):
        parser.add_argument(
            '--source',
            type=str,
            default='ftp',
            help='Source of images: ftp, local, or url'
        )
        parser.add_argument(
            '--csv-file',
            type=str,
            help='Path to CSV file with postcard metadata'
        )

    def handle(self, *args, **options):
        self.stdout.write('Starting postcard import...')

        # 1. Import metadata from CSV
        if options['csv_file']:
            self.import_metadata_from_csv(options['csv_file'])

        # 2. Import images based on source
        if options['source'] == 'ftp':
            self.import_from_ftp()
        elif options['source'] == 'local':
            self.import_from_local()

        # 3. Organize postcards by themes
        self.organize_themes()

        self.stdout.write(self.style.SUCCESS('Import completed successfully!'))

    def import_metadata_from_csv(self, csv_path):
        """Import postcard metadata from CSV"""
        with open(csv_path, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                postcard, created = Postcard.objects.update_or_create(
                    number=row['number'].zfill(3),  # Ensure 3 digits: 001, 002, etc.
                    defaults={
                        'title': row['title'].replace('\\', '"'),
                        'description': row.get('description', ''),
                        'keywords': row.get('keywords', ''),
                        'rarity': row.get('rarity', 'common'),
                    }
                )
                if created:
                    self.stdout.write(f'Created postcard {postcard.number}')
                else:
                    self.stdout.write(f'Updated postcard {postcard.number}')

    def import_from_ftp(self):
        """Import images from OVH FTP server"""
        ftp = ftplib.FTP(settings.FTP_HOST)
        ftp.login(settings.FTP_USER, settings.FTP_PASSWORD)
        ftp.cwd(settings.FTP_POSTCARDS_PATH)

        files = ftp.nlst()

        for filename in files:
            if filename.endswith(('.jpg', '.jpeg', '.png')):
                self.process_ftp_file(ftp, filename)

        ftp.quit()

    def process_ftp_file(self, ftp, filename):
        """Process and organize a single file from FTP"""
        # Expected filename format: 001_Type.jpg
        # Where Type is: Vignette, Grande, Dos, or Zoom

        try:
            # Parse filename
            base_name = filename.rsplit('.', 1)[0]  # Remove extension
            parts = base_name.split('_')

            if len(parts) >= 2:
                number = parts[0].zfill(3)  # Ensure 3 digits
                image_type = parts[1].lower()

                # Get or create postcard
                postcard, created = Postcard.objects.get_or_create(
                    number=number,
                    defaults={'title': f'Carte Postale {number}'}
                )

                # Download to temp file
                temp_file = NamedTemporaryFile(delete=True, suffix='.jpg')
                ftp.retrbinary(f'RETR {filename}', temp_file.write)
                temp_file.seek(0)

                # Process based on type
                if 'vignette' in image_type:
                    # Resize if needed for consistency
                    img = Image.open(temp_file)
                    if img.width > 300:  # Resize vignettes to max 300px width
                        img.thumbnail((300, 200), Image.Resampling.LANCZOS)
                        temp_file.seek(0)
                        img.save(temp_file, 'JPEG', quality=85)
                        temp_file.seek(0)

                    postcard.vignette_image.save(filename, File(temp_file))
                    self.stdout.write(f'✓ Vignette for {number}')

                elif 'grande' in image_type:
                    # Ensure reasonable size for web display
                    img = Image.open(temp_file)
                    if img.width > 800:  # Resize to max 800px width
                        img.thumbnail((800, 600), Image.Resampling.LANCZOS)
                        temp_file.seek(0)
                        img.save(temp_file, 'JPEG', quality=90)
                        temp_file.seek(0)

                    postcard.grande_image.save(filename, File(temp_file))
                    self.stdout.write(f'✓ Grande for {number}')

                elif 'dos' in image_type:
                    postcard.dos_image.save(filename, File(temp_file))
                    self.stdout.write(f'✓ Dos for {number}')

                elif 'zoom' in image_type:
                    # Keep zoom images at high resolution
                    postcard.zoom_image.save(filename, File(temp_file))
                    self.stdout.write(f'✓ Zoom for {number}')

                temp_file.close()

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error processing {filename}: {str(e)}')
            )

    def import_from_local(self):
        """Import from local directory structure"""
        base_path = input("Enter the base path to your postcards directory: ")

        # Expected structure:
        # base_path/
        #   ├── Vignette/
        #   ├── Grande/
        #   ├── Dos/
        #   └── Zoom/

        for image_type in ['Vignette', 'Grande', 'Dos', 'Zoom']:
            type_path = os.path.join(base_path, image_type)
            if os.path.exists(type_path):
                self.process_local_directory(type_path, image_type.lower())

    def process_local_directory(self, directory, image_type):
        """Process all images in a local directory"""
        for filename in os.listdir(directory):
            if filename.endswith(('.jpg', '.jpeg', '.png')):
                # Extract number from filename
                number = filename.split('_')[0].zfill(3)

                try:
                    postcard, created = Postcard.objects.get_or_create(
                        number=number,
                        defaults={'title': f'Carte Postale {number}'}
                    )

                    file_path = os.path.join(directory, filename)
                    with open(file_path, 'rb') as f:
                        if image_type == 'vignette':
                            postcard.vignette_image.save(filename, File(f))
                        elif image_type == 'grande':
                            postcard.grande_image.save(filename, File(f))
                        elif image_type == 'dos':
                            postcard.dos_image.save(filename, File(f))
                        elif image_type == 'zoom':
                            postcard.zoom_image.save(filename, File(f))

                    self.stdout.write(f'✓ {image_type.title()} for {number}')

                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'Error: {filename} - {str(e)}')
                    )

    def organize_themes(self):
        """Organize postcards into themes based on keywords"""
        theme_mappings = {
            'Accident du pont de l\'archevêché': ['accident', 'archevêché', 'pont'],
            'Ascenseur': ['ascenseur', 'élévateur'],
            'Spa français': ['spa', 'thermal', 'cure'],
            'Championnat du monde de natation': ['natation', 'championnat', 'piscine'],
            'Bateau touriste': ['touriste', 'excursion', 'promenade'],
            'Yacht "Le Druide"': ['yacht', 'druide', 'plaisance'],
            'Machine de Marly': ['marly', 'machine', 'hydraulique'],
            # Add more theme mappings
        }

        for theme_name, keywords in theme_mappings.items():
            theme, created = Theme.objects.get_or_create(
                display_name=theme_name,
                defaults={'name': theme_name.lower().replace(' ', '_')}
            )

            # Find postcards matching keywords
            for keyword in keywords:
                postcards = Postcard.objects.filter(
                    Q(title__icontains=keyword) |
                    Q(keywords__icontains=keyword) |
                    Q(description__icontains=keyword)
                )
                theme.postcards.add(*postcards)

            self.stdout.write(
                f'Theme "{theme_name}" has {theme.postcards.count()} postcards'
            )
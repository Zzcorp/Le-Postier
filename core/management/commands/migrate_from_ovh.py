# core/management/commands/migrate_from_ovh.py
"""
Download postcards data from OVH and populate Render database
Usage: python manage.py migrate_from_ovh --ftp-host=xxx --ftp-user=xxx --ftp-pass=xxx
"""

import os
import ftplib
import csv
import tempfile
from pathlib import Path
from django.core.management.base import BaseCommand
from django.conf import settings
from core.models import Postcard
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Migrate postcards from OVH FTP to Render'

    def add_arguments(self, parser):
        parser.add_argument('--ftp-host', type=str, required=True, help='OVH FTP host')
        parser.add_argument('--ftp-user', type=str, required=True, help='FTP username')
        parser.add_argument('--ftp-pass', type=str, required=True, help='FTP password')
        parser.add_argument('--ftp-path', type=str, default='/collection_cp', help='FTP base path')
        parser.add_argument('--csv-file', type=str, help='Path to CSV file on FTP')
        parser.add_argument('--generate-csv', action='store_true', help='Generate CSV from images')
        parser.add_argument('--limit', type=int, help='Limit number of postcards (for testing)')
        parser.add_argument('--skip-images', action='store_true', help='Skip image download')
        parser.add_argument('--skip-videos', action='store_true', help='Skip video download')
        parser.add_argument('--dry-run', action='store_true', help='Test without saving')
        parser.add_argument('--resume', action='store_true', help='Resume from last position')

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting OVH to Render migration...'))

        # Connect to FTP
        try:
            ftp = self.connect_ftp(
                options['ftp_host'],
                options['ftp_user'],
                options['ftp_pass']
            )
            self.stdout.write(self.style.SUCCESS('✓ Connected to FTP'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ FTP connection failed: {e}'))
            return

        try:
            # Step 1: Get postcards data (from CSV or generate from files)
            if options['generate_csv']:
                postcards_data = self.generate_csv_from_ftp(ftp, options)
            else:
                postcards_data = self.download_csv(ftp, options)

            if not postcards_data:
                self.stdout.write(self.style.WARNING('No CSV found, generating from FTP files...'))
                postcards_data = self.generate_csv_from_ftp(ftp, options)

            self.stdout.write(self.style.SUCCESS(f'✓ Found {len(postcards_data)} postcards'))

            # Step 2: Create/Update postcard records
            created, updated = self.create_postcards(postcards_data, options['dry_run'])
            self.stdout.write(self.style.SUCCESS(f'✓ Created: {created}, Updated: {updated}'))

            # Step 3: Download images
            if not options['skip_images']:
                self.download_images(ftp, postcards_data, options)

            # Step 4: Download videos
            if not options['skip_videos']:
                self.download_videos(ftp, postcards_data, options)

            # Step 5: Update flags
            self.stdout.write('\nUpdating postcard flags...')
            self.update_flags()

            self.stdout.write(self.style.SUCCESS('\n✓ Migration completed successfully!'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ Migration failed: {e}'))
            import traceback
            traceback.print_exc()
        finally:
            try:
                ftp.quit()
            except:
                pass

    def connect_ftp(self, host, user, password):
        """Connect to FTP server"""
        ftp = ftplib.FTP()
        ftp.connect(host, 21, timeout=30)
        ftp.login(user, password)
        ftp.set_pasv(True)
        return ftp

    def generate_csv_from_ftp(self, ftp, options):
        """Generate postcard list from FTP Vignette folder"""
        self.stdout.write('Generating postcard list from FTP files...')

        ftp_base = options['ftp_path']
        ftp_folder = f"{ftp_base}/cartes/Vignette"

        try:
            ftp.cwd(ftp_folder)
            files = ftp.nlst()

            # Filter valid image files
            valid_files = [
                f for f in files
                if f not in ['.', '..']
                   and any(f.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif'])
            ]

            self.stdout.write(f'  Found {len(valid_files)} image files')

            # Extract postcard numbers from filenames
            postcards = []
            for filename in valid_files:
                # Extract number (e.g., 000001.jpg -> 000001)
                number = os.path.splitext(filename)[0]

                # Generate title from number
                title = f"Carte Postale N° {number}"

                postcards.append({
                    'number': number,
                    'title': title,
                    'description': '',
                    'keywords': '',
                    'rarity': 'common'
                })

                if options.get('limit') and len(postcards) >= options['limit']:
                    break

            return postcards

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Failed to generate CSV: {e}'))
            return []

    def download_csv(self, ftp, options):
        """Download CSV file from FTP and parse it"""
        csv_path = options.get('csv_file') or f"{options['ftp_path']}/cartes/postcards.csv"

        self.stdout.write(f'Attempting to download CSV from {csv_path}...')

        try:
            # Download to temporary file
            with tempfile.NamedTemporaryFile(mode='wb', delete=False) as tmp:
                ftp.retrbinary(f'RETR {csv_path}', tmp.write)
                tmp_path = tmp.name

            # Parse CSV
            postcards = []
            with open(tmp_path, 'r', encoding='utf-8-sig') as csvfile:
                # Try to detect delimiter
                sample = csvfile.read(1024)
                csvfile.seek(0)

                delimiter = ',' if ',' in sample else ';'
                reader = csv.DictReader(csvfile, delimiter=delimiter)

                for row in reader:
                    postcards.append(row)
                    if options.get('limit') and len(postcards) >= options['limit']:
                        break

            os.unlink(tmp_path)
            return postcards

        except ftplib.error_perm as e:
            self.stdout.write(self.style.WARNING(f'CSV not found: {e}'))
            return []
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'Failed to download CSV: {e}'))
            return []

    def create_postcards(self, postcards_data, dry_run=False):
        """Create or update postcard records"""
        created = 0
        updated = 0

        for data in postcards_data:
            # Map CSV columns to model fields
            number = data.get('number') or data.get('Number') or data.get('numero')
            title = data.get('title') or data.get('Title') or data.get('titre')
            description = data.get('description') or data.get('Description') or ''
            keywords = data.get('keywords') or data.get('Keywords') or data.get('mots_cles') or ''
            rarity = self.map_rarity(data.get('rarity') or data.get('rarete') or 'common')

            if not number or not title:
                self.stdout.write(self.style.WARNING(f'Skipping incomplete record: {data}'))
                continue

            if dry_run:
                self.stdout.write(f'[DRY RUN] Would create: {number} - {title}')
                created += 1
                continue

            # Create or update
            try:
                postcard, is_created = Postcard.objects.update_or_create(
                    number=str(number).strip(),
                    defaults={
                        'title': title.strip(),
                        'description': description.strip(),
                        'keywords': keywords.strip(),
                        'rarity': rarity,
                    }
                )

                if is_created:
                    created += 1
                else:
                    updated += 1

                if (created + updated) % 100 == 0:
                    self.stdout.write(f'  Progress: {created + updated} postcards processed...')
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'Failed to create postcard {number}: {e}'))

        return created, updated

    def map_rarity(self, rarity_str):
        """Map rarity string to model choice"""
        rarity_map = {
            'commune': 'common',
            'common': 'common',
            'rare': 'rare',
            'tres_rare': 'very_rare',
            'très rare': 'very_rare',
            'very rare': 'very_rare',
            'very_rare': 'very_rare',
        }
        return rarity_map.get(str(rarity_str).lower().strip(), 'common')

    def download_images(self, ftp, postcards_data, options):
        """Download postcard images"""
        self.stdout.write('\nDownloading images...')

        folders = ['Vignette', 'Grande', 'Dos', 'Zoom']
        ftp_base = options['ftp_path']

        for folder in folders:
            self.stdout.write(f'\n  Processing {folder}...')

            # Create local directory
            local_dir = Path(settings.MEDIA_ROOT) / 'postcards' / folder
            local_dir.mkdir(parents=True, exist_ok=True)

            # Get list of files on FTP
            ftp_folder = f"{ftp_base}/cartes/{folder}"
            try:
                ftp.cwd(ftp_folder)
                files = ftp.nlst()

                # Filter out . and .. and non-image files
                valid_files = [
                    f for f in files
                    if f not in ['.', '..']
                       and any(f.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif'])
                ]

                self.stdout.write(f'    Found {len(valid_files)} valid files on FTP')
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'    Could not access {ftp_folder}: {e}'))
                continue

            # Download files
            downloaded = 0
            skipped = 0
            failed = 0

            for i, filename in enumerate(valid_files):
                local_file = local_dir / filename

                # Skip if already exists and is not empty
                if local_file.exists() and local_file.stat().st_size > 0:
                    skipped += 1
                    continue

                try:
                    with open(local_file, 'wb') as f:
                        ftp.retrbinary(f'RETR {filename}', f.write)
                    downloaded += 1

                    if downloaded % 50 == 0:
                        self.stdout.write(f'    Downloaded: {downloaded}, Skipped: {skipped}, Failed: {failed}')

                except Exception as e:
                    failed += 1
                    if failed < 5:  # Only show first few errors
                        self.stdout.write(self.style.WARNING(f'    Failed to download {filename}: {e}'))

                # Apply limit if specified
                if options.get('limit') and (downloaded + skipped) >= options['limit']:
                    break

            self.stdout.write(self.style.SUCCESS(
                f'    ✓ {folder}: Downloaded {downloaded}, Skipped {skipped}, Failed {failed}'
            ))

    def download_videos(self, ftp, postcards_data, options):
        """Download animated videos"""
        self.stdout.write('\nDownloading videos...')

        ftp_base = options['ftp_path']
        ftp_folder = f"{ftp_base}/cartes/animated_cp"

        # Create local directory
        local_dir = Path(settings.MEDIA_ROOT) / 'animated_cp'
        local_dir.mkdir(parents=True, exist_ok=True)

        try:
            ftp.cwd(ftp_folder)
            files = ftp.nlst()

            # Filter valid video files
            valid_files = [
                f for f in files
                if f not in ['.', '..']
                   and f.lower().endswith(('.mp4', '.webm'))
            ]

            self.stdout.write(f'  Found {len(valid_files)} video files on FTP')
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'  Could not access {ftp_folder}: {e}'))
            return

        downloaded = 0
        skipped = 0
        failed = 0

        for filename in valid_files:
            local_file = local_dir / filename

            # Skip if exists
            if local_file.exists() and local_file.stat().st_size > 0:
                skipped += 1
                continue

            try:
                self.stdout.write(f'  Downloading {filename}... ', ending='')
                with open(local_file, 'wb') as f:
                    ftp.retrbinary(f'RETR {filename}', f.write)
                downloaded += 1
                self.stdout.write(self.style.SUCCESS('✓'))
            except Exception as e:
                failed += 1
                self.stdout.write(self.style.ERROR(f'✗ {e}'))

            if options.get('limit') and (downloaded + skipped) >= options['limit']:
                break

        self.stdout.write(self.style.SUCCESS(
            f'  ✓ Videos: Downloaded {downloaded}, Skipped {skipped}, Failed {failed}'
        ))

    def update_flags(self):
        """Update has_images and has_animation flags"""
        postcards = Postcard.objects.all()
        updated = 0

        for postcard in postcards:
            try:
                postcard.update_image_flags()
                updated += 1

                if updated % 100 == 0:
                    self.stdout.write(f'  Updated flags for {updated} postcards...')
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'  Failed to update flags for {postcard.number}: {e}'))

        self.stdout.write(self.style.SUCCESS(f'  ✓ Updated {updated} postcards'))
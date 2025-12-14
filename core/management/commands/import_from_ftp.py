# core/management/commands/import_from_ftp.py
"""
Management command to download postcard images from FTP server
and populate the database.
"""

import os
import ftplib
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from core.models import Postcard


class Command(BaseCommand):
    help = 'Download postcard images from OVH FTP server and create database entries'

    def add_arguments(self, parser):
        parser.add_argument(
            '--host',
            type=str,
            default='ftp.cluster010.hosting.ovh.net',
            help='FTP host address'
        )
        parser.add_argument(
            '--user',
            type=str,
            required=True,
            help='FTP username'
        )
        parser.add_argument(
            '--password',
            type=str,
            required=True,
            help='FTP password'
        )
        parser.add_argument(
            '--remote-path',
            type=str,
            default='/collection_cp/cartes',
            help='Remote base path on FTP server (default: /www/collection_cp/cartes)'
        )
        parser.add_argument(
            '--folder',
            type=str,
            choices=['Vignette', 'Grande', 'Dos', 'Zoom', 'animated_cp', 'all'],
            default='all',
            help='Which folder to download (default: all)'
        )
        parser.add_argument(
            '--start',
            type=int,
            default=1,
            help='Start number (default: 1)'
        )
        parser.add_argument(
            '--end',
            type=int,
            default=2000,
            help='End number (default: 2000)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be downloaded without actually downloading'
        )
        parser.add_argument(
            '--list-only',
            action='store_true',
            help='Only list files on FTP server, do not download'
        )
        parser.add_argument(
            '--create-db-entries',
            action='store_true',
            help='Create database entries for downloaded files'
        )
        parser.add_argument(
            '--skip-existing',
            action='store_true',
            default=True,
            help='Skip files that already exist locally (default: True)'
        )

    def handle(self, *args, **options):
        self.host = options['host']
        self.user = options['user']
        self.password = options['password']
        self.remote_path = options['remote_path']
        self.dry_run = options['dry_run']
        self.skip_existing = options['skip_existing']

        # Determine folders to process
        if options['folder'] == 'all':
            self.folders = ['Vignette', 'Grande', 'Dos', 'Zoom', 'animated_cp']
        else:
            self.folders = [options['folder']]

        self.start_num = options['start']
        self.end_num = options['end']

        # Connect to FTP
        try:
            self.stdout.write(f'Connecting to FTP server: {self.host}')
            self.ftp = ftplib.FTP(self.host, timeout=30)
            self.ftp.login(self.user, self.password)
            self.stdout.write(self.style.SUCCESS(f'Connected successfully!'))
            self.stdout.write(f'Current directory: {self.ftp.pwd()}')
        except ftplib.all_errors as e:
            raise CommandError(f'FTP connection failed: {e}')

        try:
            if options['list_only']:
                self.list_ftp_files()
            else:
                self.download_files()

                if options['create_db_entries']:
                    self.create_database_entries()
        finally:
            self.ftp.quit()
            self.stdout.write('FTP connection closed.')

    def list_ftp_files(self):
        """List files available on FTP server."""
        self.stdout.write(f'\n{"=" * 60}')
        self.stdout.write('FILES ON FTP SERVER')
        self.stdout.write(f'{"=" * 60}')

        for folder in self.folders:
            if folder == 'animated_cp':
                remote_folder = f'{self.remote_path}/animated_cp'
            else:
                remote_folder = f'{self.remote_path}/{folder}'

            self.stdout.write(f'\n--- {folder} ---')
            try:
                self.ftp.cwd(remote_folder)
                files = self.ftp.nlst()
                self.stdout.write(f'Found {len(files)} files')

                # Show first 10 files as sample
                for f in sorted(files)[:10]:
                    self.stdout.write(f'  {f}')
                if len(files) > 10:
                    self.stdout.write(f'  ... and {len(files) - 10} more')

            except ftplib.error_perm as e:
                self.stdout.write(self.style.WARNING(f'Cannot access {remote_folder}: {e}'))

    def download_files(self):
        """Download files from FTP server."""
        media_root = Path(settings.MEDIA_ROOT)
        total_downloaded = 0
        total_skipped = 0
        total_errors = 0

        for folder in self.folders:
            self.stdout.write(f'\n{"─" * 60}')
            self.stdout.write(f'Processing: {folder}')
            self.stdout.write(f'{"─" * 60}')

            # Set up paths
            if folder == 'animated_cp':
                remote_folder = f'{self.remote_path}/animated_cp'
                local_folder = media_root / 'animated_cp'
                extensions = ['.mp4', '.webm', '.MP4', '.WEBM']
            else:
                remote_folder = f'{self.remote_path}/{folder}'
                local_folder = media_root / 'postcards' / folder
                extensions = ['.jpg', '.jpeg', '.png', '.gif', '.JPG', '.JPEG', '.PNG', '.GIF']

            # Create local directory
            local_folder.mkdir(parents=True, exist_ok=True)

            # Try to change to remote directory
            try:
                self.ftp.cwd(remote_folder)
                self.stdout.write(f'Changed to: {remote_folder}')
            except ftplib.error_perm as e:
                self.stdout.write(self.style.WARNING(f'Cannot access {remote_folder}: {e}'))
                continue

            # Get list of files
            try:
                remote_files = self.ftp.nlst()
            except ftplib.error_perm:
                remote_files = []

            self.stdout.write(f'Found {len(remote_files)} files on server')

            # Download files
            downloaded = 0
            skipped = 0
            errors = 0

            for num in range(self.start_num, self.end_num + 1):
                padded = str(num).zfill(6)

                for ext in extensions:
                    filename = f'{padded}{ext}'

                    # Check if file exists on server
                    if filename not in remote_files and filename.lower() not in [f.lower() for f in remote_files]:
                        continue

                    # Find actual filename (case-insensitive)
                    actual_filename = filename
                    for rf in remote_files:
                        if rf.lower() == filename.lower():
                            actual_filename = rf
                            break

                    local_path = local_folder / actual_filename

                    # Skip if exists
                    if self.skip_existing and local_path.exists():
                        skipped += 1
                        continue

                    if self.dry_run:
                        self.stdout.write(f'Would download: {actual_filename}')
                        downloaded += 1
                    else:
                        try:
                            with open(local_path, 'wb') as f:
                                self.ftp.retrbinary(f'RETR {actual_filename}', f.write)
                            downloaded += 1

                            # Progress indicator
                            if downloaded % 50 == 0:
                                self.stdout.write(f'  Downloaded {downloaded} files...')

                        except ftplib.all_errors as e:
                            errors += 1
                            if errors <= 5:  # Only show first 5 errors
                                self.stdout.write(self.style.ERROR(f'Error downloading {actual_filename}: {e}'))

                    break  # Found the file, move to next number

                # Progress indicator
                if num % 200 == 0:
                    self.stdout.write(f'  Progress: {num}/{self.end_num}')

            self.stdout.write(f'  Downloaded: {downloaded}, Skipped: {skipped}, Errors: {errors}')
            total_downloaded += downloaded
            total_skipped += skipped
            total_errors += errors

        self.stdout.write(f'\n{"=" * 60}')
        self.stdout.write(self.style.SUCCESS(
            f'TOTAL: Downloaded {total_downloaded}, Skipped {total_skipped}, Errors {total_errors}'
        ))

    def create_database_entries(self):
        """Create database entries for downloaded files."""
        self.stdout.write(f'\n{"=" * 60}')
        self.stdout.write('CREATING DATABASE ENTRIES')
        self.stdout.write(f'{"=" * 60}')

        media_root = Path(settings.MEDIA_ROOT)
        vignette_dir = media_root / 'postcards' / 'Vignette'

        if not vignette_dir.exists():
            self.stdout.write(self.style.WARNING('Vignette directory not found'))
            return

        created = 0
        updated = 0

        # Get all image files from Vignette folder
        image_extensions = {'.jpg', '.jpeg', '.png', '.gif'}

        for file_path in vignette_dir.iterdir():
            if file_path.suffix.lower() not in image_extensions:
                continue

            # Extract number from filename
            number = file_path.stem

            if not number.isdigit():
                continue

            # Pad to 6 digits
            number = number.zfill(6)

            if self.dry_run:
                self.stdout.write(f'Would create/update: {number}')
                continue

            # Create or update postcard
            postcard, is_created = Postcard.objects.get_or_create(
                number=number,
                defaults={
                    'title': f'Carte postale {number}',
                    'keywords': '',
                    'description': '',
                    'rarity': 'common',
                }
            )

            # Update flags
            postcard.has_images = postcard.check_has_vignette()
            postcard.has_animation = postcard.check_has_animation()
            postcard.save(update_fields=['has_images', 'has_animation'])

            if is_created:
                created += 1
            else:
                updated += 1

        self.stdout.write(self.style.SUCCESS(f'Created {created}, Updated {updated} postcards'))
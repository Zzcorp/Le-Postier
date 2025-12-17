# core/management/commands/sync_from_ovh.py
"""
Management command to sync images from OVH FTP server to Render persistent disk.
Run with: python manage.py sync_from_ovh
"""

from django.core.management.base import BaseCommand
from django.conf import settings
from pathlib import Path
import ftplib
import os
from decouple import config


class Command(BaseCommand):
    help = 'Sync postcard images from OVH FTP server to local media storage'

    def add_arguments(self, parser):
        parser.add_argument(
            '--folder',
            type=str,
            default='all',
            help='Specific folder to sync: Vignette, Grande, Dos, Zoom, animated_cp, or all'
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=0,
            help='Limit number of files to download per folder (0 = no limit)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be downloaded without actually downloading'
        )
        parser.add_argument(
            '--skip-existing',
            action='store_true',
            default=True,
            help='Skip files that already exist locally'
        )

    def handle(self, *args, **options):
        # FTP Configuration - get from environment variables
        FTP_HOST = config('OVH_FTP_HOST', default='')
        FTP_USER = config('OVH_FTP_USER', default='')
        FTP_PASS = config('OVH_FTP_PASS', default='')
        FTP_BASE_PATH = config('OVH_FTP_PATH', default='/collection_cp/cartes')

        if not all([FTP_HOST, FTP_USER, FTP_PASS]):
            self.stderr.write(self.style.ERROR(
                'Missing FTP credentials. Set OVH_FTP_HOST, OVH_FTP_USER, OVH_FTP_PASS environment variables.'
            ))
            return

        # Local paths
        media_root = Path(settings.MEDIA_ROOT)

        # Folder mapping: FTP folder -> Local folder
        folder_mapping = {
            'Vignette': media_root / 'postcards' / 'Vignette',
            'Grande': media_root / 'postcards' / 'Grande',
            'Dos': media_root / 'postcards' / 'Dos',
            'Zoom': media_root / 'postcards' / 'Zoom',
        }

        # Animated videos folder
        animated_mapping = {
            'animated_cp': media_root / 'animated_cp',
        }

        selected_folder = options['folder']
        limit = options['limit']
        dry_run = options['dry_run']
        skip_existing = options['skip_existing']

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No files will be downloaded'))

        try:
            self.stdout.write(f'Connecting to FTP server {FTP_HOST}...')
            ftp = ftplib.FTP(FTP_HOST, timeout=30)
            ftp.login(FTP_USER, FTP_PASS)
            self.stdout.write(self.style.SUCCESS(f'Connected to {FTP_HOST}'))

            # Sync postcard images
            if selected_folder == 'all' or selected_folder in folder_mapping:
                folders_to_sync = folder_mapping if selected_folder == 'all' else {
                    selected_folder: folder_mapping[selected_folder]}

                for ftp_folder, local_folder in folders_to_sync.items():
                    self.sync_folder(
                        ftp,
                        f'{FTP_BASE_PATH}/{ftp_folder}',
                        local_folder,
                        ftp_folder,
                        limit,
                        dry_run,
                        skip_existing
                    )

            # Sync animated videos
            if selected_folder == 'all' or selected_folder == 'animated_cp':
                # Animated videos might be in a different path
                animated_ftp_path = config('OVH_FTP_ANIMATED_PATH', default='/collection_cp/cartes/animated_cp')

                for ftp_folder, local_folder in animated_mapping.items():
                    self.sync_folder(
                        ftp,
                        animated_ftp_path,
                        local_folder,
                        ftp_folder,
                        limit,
                        dry_run,
                        skip_existing
                    )

            ftp.quit()
            self.stdout.write(self.style.SUCCESS('Sync completed!'))

        except ftplib.error_perm as e:
            self.stderr.write(self.style.ERROR(f'FTP permission error: {e}'))
        except ftplib.error_temp as e:
            self.stderr.write(self.style.ERROR(f'FTP temporary error: {e}'))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'Error: {e}'))

    def sync_folder(self, ftp, remote_path, local_path, folder_name, limit, dry_run, skip_existing):
        """Sync a single folder from FTP to local storage"""
        self.stdout.write(f'\n{"=" * 60}')
        self.stdout.write(f'Syncing {folder_name}...')
        self.stdout.write(f'  Remote: {remote_path}')
        self.stdout.write(f'  Local:  {local_path}')

        # Create local directory if it doesn't exist
        if not dry_run:
            local_path.mkdir(parents=True, exist_ok=True)

        try:
            ftp.cwd(remote_path)
        except ftplib.error_perm:
            self.stderr.write(self.style.WARNING(f'  Could not access {remote_path} - skipping'))
            return

        # Get list of files
        try:
            files = ftp.nlst()
        except ftplib.error_perm:
            self.stderr.write(self.style.WARNING(f'  Could not list files in {remote_path} - skipping'))
            return

        # Filter for image/video files
        valid_extensions = (
        '.jpg', '.jpeg', '.png', '.gif', '.mp4', '.webm', '.JPG', '.JPEG', '.PNG', '.GIF', '.MP4', '.WEBM')
        files = [f for f in files if f.lower().endswith(valid_extensions) or f.endswith(valid_extensions)]

        self.stdout.write(f'  Found {len(files)} files')

        if limit > 0:
            files = files[:limit]
            self.stdout.write(f'  Limited to {limit} files')

        downloaded = 0
        skipped = 0
        errors = 0

        for i, filename in enumerate(files, 1):
            local_file = local_path / filename

            if skip_existing and local_file.exists():
                skipped += 1
                continue

            if dry_run:
                self.stdout.write(f'  [{i}/{len(files)}] Would download: {filename}')
                downloaded += 1
            else:
                try:
                    self.stdout.write(f'  [{i}/{len(files)}] Downloading: {filename}', ending='')
                    with open(local_file, 'wb') as f:
                        ftp.retrbinary(f'RETR {filename}', f.write)
                    self.stdout.write(self.style.SUCCESS(' ✓'))
                    downloaded += 1
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f' ✗ Error: {e}'))
                    errors += 1

        self.stdout.write(f'\n  Summary for {folder_name}:')
        self.stdout.write(f'    Downloaded: {downloaded}')
        self.stdout.write(f'    Skipped (existing): {skipped}')
        self.stdout.write(f'    Errors: {errors}')
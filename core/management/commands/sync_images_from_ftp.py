# core/management/commands/sync_images_from_ftp.py
"""
Sync images from OVH FTP to Render's persistent disk
Usage: python manage.py sync_images_from_ftp --ftp-host=xxx --ftp-user=xxx --ftp-pass=xxx
"""

import ftplib
import os
from pathlib import Path
from django.core.management.base import BaseCommand
from django.conf import settings
import time


class Command(BaseCommand):
    help = 'Sync images from OVH FTP to local media directory'

    def add_arguments(self, parser):
        parser.add_argument('--ftp-host', type=str, required=True)
        parser.add_argument('--ftp-user', type=str, required=True)
        parser.add_argument('--ftp-pass', type=str, required=True)
        parser.add_argument('--ftp-path', type=str, default='/collection_cp/cartes')
        parser.add_argument('--folders', type=str, default='Vignette,Grande,Dos,Zoom,animated_cp',
                            help='Comma-separated folders to sync')
        parser.add_argument('--limit', type=int, help='Limit files per folder')
        parser.add_argument('--skip-existing', action='store_true', default=True)
        parser.add_argument('--resume', action='store_true', help='Resume from last file')

    def handle(self, *args, **options):
        media_root = Path(settings.MEDIA_ROOT)

        self.stdout.write(f"Media root: {media_root}")
        self.stdout.write(f"FTP host: {options['ftp_host']}")

        # Connect to FTP
        ftp = self.connect_ftp(options['ftp_host'], options['ftp_user'], options['ftp_pass'])

        if not ftp:
            return

        try:
            folders = options['folders'].split(',')

            for folder in folders:
                folder = folder.strip()
                self.sync_folder(ftp, folder, options, media_root)

            self.stdout.write(self.style.SUCCESS("\n✓ Sync completed!"))

        finally:
            try:
                ftp.quit()
            except:
                pass

    def connect_ftp(self, host, user, password):
        """Connect to FTP with retry"""
        for attempt in range(3):
            try:
                ftp = ftplib.FTP()
                ftp.connect(host, 21, timeout=60)
                ftp.login(user, password)
                ftp.set_pasv(True)
                self.stdout.write(self.style.SUCCESS("✓ Connected to FTP"))
                return ftp
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"Connection attempt {attempt + 1} failed: {e}"))
                time.sleep(5)

        self.stdout.write(self.style.ERROR("✗ Could not connect to FTP"))
        return None

    def sync_folder(self, ftp, folder_name, options, media_root):
        """Sync a single folder"""
        self.stdout.write(f"\n{'=' * 50}")
        self.stdout.write(f"Syncing: {folder_name}")
        self.stdout.write('=' * 50)

        # Determine paths
        if folder_name == 'animated_cp':
            ftp_path = f"{options['ftp_path']}/animated_cp"
            local_path = media_root / 'animated_cp'
            extensions = {'.mp4', '.webm', '.MP4', '.WEBM'}
        else:
            ftp_path = f"{options['ftp_path']}/{folder_name}"
            local_path = media_root / 'postcards' / folder_name
            extensions = {'.jpg', '.jpeg', '.png', '.gif', '.JPG', '.JPEG', '.PNG', '.GIF'}

        # Create local directory
        local_path.mkdir(parents=True, exist_ok=True)

        # Get FTP file list
        try:
            ftp.cwd(ftp_path)
            ftp_files = ftp.nlst()
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"Could not access {ftp_path}: {e}"))
            return

        # Filter valid files
        valid_files = [
            f for f in ftp_files
            if f not in ['.', '..'] and any(f.endswith(ext) for ext in extensions)
        ]

        self.stdout.write(f"Found {len(valid_files)} files on FTP")

        # Get existing local files
        existing = {f.name for f in local_path.iterdir() if f.is_file()}
        self.stdout.write(f"Existing local files: {len(existing)}")

        # Apply limit
        if options.get('limit'):
            valid_files = valid_files[:options['limit']]

        # Sync files
        downloaded = 0
        skipped = 0
        failed = 0

        for i, filename in enumerate(valid_files):
            local_file = local_path / filename

            # Skip existing
            if options.get('skip_existing') and filename in existing:
                # Also check file size
                if local_file.exists() and local_file.stat().st_size > 100:
                    skipped += 1
                    continue

            # Download
            try:
                with open(local_file, 'wb') as f:
                    ftp.retrbinary(f'RETR {filename}', f.write)
                downloaded += 1

                if downloaded % 50 == 0:
                    self.stdout.write(f"  Downloaded: {downloaded}, Skipped: {skipped}")

            except Exception as e:
                failed += 1
                if failed < 5:
                    self.stdout.write(self.style.WARNING(f"  Failed: {filename}: {e}"))

                # Try to reconnect if connection lost
                if 'connection' in str(e).lower() or 'timeout' in str(e).lower():
                    self.stdout.write("  Reconnecting...")
                    time.sleep(2)
                    try:
                        ftp.quit()
                    except:
                        pass
                    ftp = self.connect_ftp(
                        options['ftp_host'],
                        options['ftp_user'],
                        options['ftp_pass']
                    )
                    if ftp:
                        try:
                            ftp.cwd(ftp_path)
                        except:
                            pass

        self.stdout.write(self.style.SUCCESS(
            f"✓ {folder_name}: Downloaded {downloaded}, Skipped {skipped}, Failed {failed}"
        ))
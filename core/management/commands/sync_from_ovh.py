# core/management/commands/sync_from_ovh.py
"""
Sync images from OVH FTP server to Render persistent disk.
This downloads images directly from OVH to Render.
"""

import os
import ftplib
from pathlib import Path
from django.core.management.base import BaseCommand
from django.conf import settings
from core.models import Postcard
import time


class Command(BaseCommand):
    help = 'Sync images from OVH FTP to Render persistent disk'

    def add_arguments(self, parser):
        parser.add_argument('--ftp-host', type=str, required=True, help='OVH FTP hostname')
        parser.add_argument('--ftp-user', type=str, required=True, help='FTP username')
        parser.add_argument('--ftp-pass', type=str, required=True, help='FTP password')
        parser.add_argument('--ftp-path', type=str, default='/collection_cp/cartes',
                            help='Base path on FTP server')
        parser.add_argument('--limit', type=int, help='Limit number of files per folder')
        parser.add_argument('--folder', type=str, choices=['Vignette', 'Grande', 'Dos', 'Zoom', 'animated_cp', 'all'],
                            default='all', help='Which folder to sync')
        parser.add_argument('--dry-run', action='store_true', help='List files without downloading')
        parser.add_argument('--skip-existing', action='store_true', default=True,
                            help='Skip files that already exist locally')

    def handle(self, *args, **options):
        self.stdout.write("=" * 70)
        self.stdout.write("OVH FTP to Render Sync")
        self.stdout.write("=" * 70)

        ftp_host = options['ftp_host']
        ftp_user = options['ftp_user']
        ftp_pass = options['ftp_pass']
        ftp_base_path = options['ftp_path']
        limit = options.get('limit')
        folder_choice = options['folder']
        dry_run = options['dry_run']
        skip_existing = options['skip_existing']

        # Connect to FTP
        self.stdout.write(f"\nConnecting to FTP: {ftp_host}...")
        try:
            ftp = ftplib.FTP(ftp_host, timeout=30)
            ftp.login(ftp_user, ftp_pass)
            ftp.set_pasv(True)
            self.stdout.write(self.style.SUCCESS("✓ Connected to FTP"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"✗ FTP connection failed: {e}"))
            return

        # Define folder mappings
        folder_mappings = {
            'Vignette': {'ftp': f'{ftp_base_path}/Vignette', 'local': 'postcards/Vignette'},
            'Grande': {'ftp': f'{ftp_base_path}/Grande', 'local': 'postcards/Grande'},
            'Dos': {'ftp': f'{ftp_base_path}/Dos', 'local': 'postcards/Dos'},
            'Zoom': {'ftp': f'{ftp_base_path}/Zoom', 'local': 'postcards/Zoom'},
            'animated_cp': {'ftp': f'{ftp_base_path}/../animated_cp', 'local': 'animated_cp'},
        }

        # Determine which folders to sync
        if folder_choice == 'all':
            folders_to_sync = list(folder_mappings.keys())
        else:
            folders_to_sync = [folder_choice]

        media_root = Path(settings.MEDIA_ROOT)
        total_downloaded = 0
        total_skipped = 0
        total_errors = 0

        for folder_name in folders_to_sync:
            folder_config = folder_mappings[folder_name]
            ftp_path = folder_config['ftp']
            local_path = media_root / folder_config['local']

            self.stdout.write(f"\n{'=' * 50}")
            self.stdout.write(f"Syncing: {folder_name}")
            self.stdout.write(f"  FTP: {ftp_path}")
            self.stdout.write(f"  Local: {local_path}")

            # Create local directory
            local_path.mkdir(parents=True, exist_ok=True)

            # List files on FTP
            try:
                ftp.cwd(ftp_path)
                files = []
                ftp.retrlines('NLST', files.append)

                # Filter image/video files
                if folder_name == 'animated_cp':
                    valid_extensions = {'.mp4', '.webm', '.MP4', '.WEBM'}
                else:
                    valid_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.JPG', '.JPEG', '.PNG', '.GIF'}

                files = [f for f in files if any(f.endswith(ext) for ext in valid_extensions)]

                self.stdout.write(f"  Found {len(files)} files on FTP")

                if limit:
                    files = files[:limit]
                    self.stdout.write(f"  Limited to {len(files)} files")

            except Exception as e:
                self.stdout.write(self.style.WARNING(f"  ✗ Could not access {ftp_path}: {e}"))
                continue

            if dry_run:
                self.stdout.write(f"  [DRY RUN] Would download: {len(files)} files")
                if files[:5]:
                    self.stdout.write(f"  Sample files: {', '.join(files[:5])}")
                continue

            # Download files
            downloaded = 0
            skipped = 0
            errors = 0

            for i, filename in enumerate(files):
                local_file = local_path / filename

                # Skip existing files
                if skip_existing and local_file.exists():
                    skipped += 1
                    continue

                try:
                    with open(local_file, 'wb') as f:
                        ftp.retrbinary(f'RETR {filename}', f.write)
                    downloaded += 1

                    if downloaded % 50 == 0:
                        self.stdout.write(f"  Progress: {downloaded} downloaded, {skipped} skipped...")

                except Exception as e:
                    errors += 1
                    if errors < 10:
                        self.stdout.write(self.style.WARNING(f"  Error downloading {filename}: {e}"))

                # Small delay to avoid overwhelming the FTP server
                if downloaded % 100 == 0:
                    time.sleep(0.5)

            self.stdout.write(f"  ✓ Downloaded: {downloaded}")
            self.stdout.write(f"  ⊘ Skipped: {skipped}")
            if errors:
                self.stdout.write(self.style.WARNING(f"  ✗ Errors: {errors}"))

            total_downloaded += downloaded
            total_skipped += skipped
            total_errors += errors

        # Close FTP connection
        try:
            ftp.quit()
        except:
            pass

        # Summary
        self.stdout.write(f"\n{'=' * 70}")
        self.stdout.write("SYNC COMPLETE")
        self.stdout.write("=" * 70)
        self.stdout.write(f"Total downloaded: {total_downloaded}")
        self.stdout.write(f"Total skipped: {total_skipped}")
        self.stdout.write(f"Total errors: {total_errors}")

        # Verify local files
        self.stdout.write(f"\nVerifying local files:")
        for folder_name, config in folder_mappings.items():
            local_path = media_root / config['local']
            if local_path.exists():
                count = len(list(local_path.glob('*.*')))
                self.stdout.write(f"  {folder_name}: {count} files")
            else:

                self.stdout.write(f"  {folder_name}: NOT FOUND")

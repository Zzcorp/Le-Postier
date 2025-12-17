# core/management/commands/sync_from_ovh.py
"""
Sync images from OVH FTP server to Render persistent disk.
Downloads images and saves them to MEDIA_ROOT.
"""

import ftplib
import os
from pathlib import Path
from django.core.management.base import BaseCommand
from django.conf import settings
from concurrent.futures import ThreadPoolExecutor
import time


class Command(BaseCommand):
    help = 'Sync postcard images from OVH FTP to local storage'

    def add_arguments(self, parser):
        parser.add_argument('--ftp-host', type=str, required=True, help='FTP host')
        parser.add_argument('--ftp-user', type=str, required=True, help='FTP username')
        parser.add_argument('--ftp-pass', type=str, required=True, help='FTP password')
        parser.add_argument('--ftp-path', type=str, default='/collection_cp/cartes',
                            help='Base path on FTP server')
        parser.add_argument('--animated-path', type=str, default='/collection_cp/animated_cp',
                            help='Animated videos path on FTP')
        parser.add_argument('--folders', type=str, default='Vignette,Grande,Dos,Zoom',
                            help='Comma-separated folder names to sync')
        parser.add_argument('--limit', type=int, help='Limit number of files per folder')
        parser.add_argument('--skip-existing', action='store_true', default=True,
                            help='Skip files that already exist locally')
        parser.add_argument('--include-animated', action='store_true',
                            help='Also sync animated videos')
        parser.add_argument('--dry-run', action='store_true',
                            help='List files without downloading')

    def handle(self, *args, **options):
        self.stdout.write("=" * 60)
        self.stdout.write("OVH FTP to Render Sync")
        self.stdout.write("=" * 60)

        # Verify MEDIA_ROOT
        media_root = Path(settings.MEDIA_ROOT)
        self.stdout.write(f"\nMEDIA_ROOT: {media_root}")
        self.stdout.write(f"Exists: {media_root.exists()}")

        if not media_root.exists():
            self.stdout.write(self.style.WARNING("Creating MEDIA_ROOT..."))
            media_root.mkdir(parents=True, exist_ok=True)

        # Connect to FTP
        self.stdout.write(f"\nConnecting to FTP: {options['ftp_host']}...")

        try:
            ftp = ftplib.FTP(options['ftp_host'], timeout=30)
            ftp.login(options['ftp_user'], options['ftp_pass'])
            ftp.set_pasv(True)
            self.stdout.write(self.style.SUCCESS("✓ Connected to FTP"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"✗ FTP connection failed: {e}"))
            return

        # Process each folder
        folders = options['folders'].split(',')
        total_downloaded = 0
        total_skipped = 0
        total_errors = 0

        for folder in folders:
            folder = folder.strip()
            self.stdout.write(f"\n{'=' * 40}")
            self.stdout.write(f"Processing folder: {folder}")
            self.stdout.write('=' * 40)

            ftp_folder = f"{options['ftp_path']}/{folder}"
            local_folder = media_root / 'postcards' / folder

            # Create local folder
            local_folder.mkdir(parents=True, exist_ok=True)

            result = self.sync_folder(
                ftp,
                ftp_folder,
                local_folder,
                options['limit'],
                options['skip_existing'],
                options['dry_run']
            )

            total_downloaded += result['downloaded']
            total_skipped += result['skipped']
            total_errors += result['errors']

        # Sync animated videos if requested
        if options['include_animated']:
            self.stdout.write(f"\n{'=' * 40}")
            self.stdout.write("Processing animated videos")
            self.stdout.write('=' * 40)

            local_animated = media_root / 'animated_cp'
            local_animated.mkdir(parents=True, exist_ok=True)

            result = self.sync_folder(
                ftp,
                options['animated_path'],
                local_animated,
                options['limit'],
                options['skip_existing'],
                options['dry_run'],
                extensions=['.mp4', '.webm', '.MP4', '.WEBM']
            )

            total_downloaded += result['downloaded']
            total_skipped += result['skipped']
            total_errors += result['errors']

        # Close FTP
        try:
            ftp.quit()
        except:
            pass

        # Summary
        self.stdout.write(f"\n{'=' * 60}")
        self.stdout.write("SYNC COMPLETE")
        self.stdout.write('=' * 60)
        self.stdout.write(self.style.SUCCESS(f"Downloaded: {total_downloaded}"))
        self.stdout.write(f"Skipped (existing): {total_skipped}")
        if total_errors:
            self.stdout.write(self.style.WARNING(f"Errors: {total_errors}"))

        # Verify
        self.verify_sync(media_root)

    def sync_folder(self, ftp, ftp_path, local_path, limit=None, skip_existing=True,
                    dry_run=False, extensions=None):
        """Sync a single folder from FTP to local storage."""

        if extensions is None:
            extensions = ['.jpg', '.jpeg', '.png', '.gif', '.JPG', '.JPEG', '.PNG', '.GIF']

        result = {'downloaded': 0, 'skipped': 0, 'errors': 0}

        try:
            ftp.cwd(ftp_path)
            self.stdout.write(f"  FTP path: {ftp_path}")
        except ftplib.error_perm as e:
            self.stdout.write(self.style.ERROR(f"  ✗ Cannot access FTP path: {e}"))
            return result

        # List files
        try:
            files = ftp.nlst()
            # Filter by extension
            files = [f for f in files if any(f.endswith(ext) for ext in extensions)]
            self.stdout.write(f"  Found {len(files)} files on FTP")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  ✗ Cannot list files: {e}"))
            return result

        if limit:
            files = files[:limit]
            self.stdout.write(f"  Limited to {limit} files")

        # Download files
        for i, filename in enumerate(files):
            local_file = local_path / filename

            # Skip if exists
            if skip_existing and local_file.exists():
                result['skipped'] += 1
                continue

            if dry_run:
                self.stdout.write(f"  [DRY RUN] Would download: {filename}")
                result['downloaded'] += 1
                continue

            try:
                with open(local_file, 'wb') as f:
                    ftp.retrbinary(f'RETR {filename}', f.write)
                result['downloaded'] += 1

                if (i + 1) % 50 == 0:
                    self.stdout.write(f"  Progress: {i + 1}/{len(files)}")

            except Exception as e:
                result['errors'] += 1
                if result['errors'] < 5:
                    self.stdout.write(self.style.WARNING(f"  ✗ Error downloading {filename}: {e}"))

        self.stdout.write(f"  ✓ Downloaded: {result['downloaded']}, Skipped: {result['skipped']}")
        return result

    def verify_sync(self, media_root):
        """Verify the sync by checking local files."""
        self.stdout.write("\nVerification:")

        for folder in ['Vignette', 'Grande', 'Dos', 'Zoom']:
            folder_path = media_root / 'postcards' / folder
            if folder_path.exists():
                count = len(list(folder_path.glob('*.*')))
                size = sum(f.stat().st_size for f in folder_path.glob('*.*')) / (1024 * 1024)
                self.stdout.write(f"  {folder}: {count} files ({size:.2f} MB)")
            else:
                self.stdout.write(f"  {folder}: NOT FOUND")

        animated_path = media_root / 'animated_cp'
        if animated_path.exists():
            count = len(list(animated_path.glob('*.*')))
            size = sum(f.stat().st_size for f in animated_path.glob('*.*')) / (1024 * 1024)
            self.stdout.write(f"  animated_cp: {count} files ({size:.2f} MB)")
# core/management/commands/upload_media.py
"""
Management command to upload media files from a source directory or URL.
Supports uploading from local directories, FTP, or HTTP sources.
"""

import os
import shutil
import requests
from pathlib import Path
from urllib.parse import urljoin
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings


class Command(BaseCommand):
    help = 'Upload media files to the MEDIA_ROOT directory'

    def add_arguments(self, parser):
        parser.add_argument(
            '--source',
            type=str,
            help='Source directory or base URL for media files'
        )
        parser.add_argument(
            '--type',
            choices=['local', 'http', 'ftp'],
            default='local',
            help='Type of source (local directory, http URL, or ftp)'
        )
        parser.add_argument(
            '--folder',
            type=str,
            choices=['Vignette', 'Grande', 'Dos', 'Zoom', 'animated_cp', 'all'],
            default='all',
            help='Which folder to upload (default: all)'
        )
        parser.add_argument(
            '--start',
            type=int,
            default=1,
            help='Start number for downloading (e.g., 1 for 000001)'
        )
        parser.add_argument(
            '--end',
            type=int,
            default=2000,
            help='End number for downloading (e.g., 2000 for 002000)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be uploaded without making changes'
        )

    def handle(self, *args, **options):
        source = options['source']
        source_type = options['type']
        folder = options['folder']
        dry_run = options['dry_run']

        if not source:
            raise CommandError('Please specify --source')

        media_root = Path(settings.MEDIA_ROOT)

        # Determine which folders to process
        if folder == 'all':
            folders = ['Vignette', 'Grande', 'Dos', 'Zoom', 'animated_cp']
        else:
            folders = [folder]

        total_copied = 0

        for folder_name in folders:
            if folder_name == 'animated_cp':
                dest_dir = media_root / 'animated_cp'
            else:
                dest_dir = media_root / 'postcards' / folder_name

            dest_dir.mkdir(parents=True, exist_ok=True)

            if source_type == 'local':
                copied = self.copy_from_local(source, folder_name, dest_dir, dry_run)
            elif source_type == 'http':
                copied = self.download_from_http(
                    source, folder_name, dest_dir,
                    options['start'], options['end'], dry_run
                )
            else:
                self.stdout.write(self.style.WARNING(f'FTP not implemented yet'))
                continue

            total_copied += copied
            self.stdout.write(f'{folder_name}: {copied} files')

        self.stdout.write(self.style.SUCCESS(f'Total: {total_copied} files processed'))

    def copy_from_local(self, source_base, folder_name, dest_dir, dry_run):
        """Copy files from local directory."""
        if folder_name == 'animated_cp':
            source_dir = Path(source_base) / 'animated_cp'
        else:
            source_dir = Path(source_base) / folder_name

        if not source_dir.exists():
            self.stdout.write(self.style.WARNING(f'Source not found: {source_dir}'))
            return 0

        copied = 0
        for file_path in source_dir.iterdir():
            if file_path.is_file():
                dest_path = dest_dir / file_path.name

                if dry_run:
                    self.stdout.write(f'Would copy: {file_path} -> {dest_path}')
                else:
                    shutil.copy2(file_path, dest_path)

                copied += 1

        return copied

    def download_from_http(self, base_url, folder_name, dest_dir, start, end, dry_run):
        """Download files from HTTP source."""
        downloaded = 0
        extensions = ['.jpg', '.jpeg', '.png', '.gif']

        if folder_name == 'animated_cp':
            extensions = ['.mp4', '.webm']

        for num in range(start, end + 1):
            padded = str(num).zfill(6)

            for ext in extensions:
                if folder_name == 'animated_cp':
                    url = f"{base_url.rstrip('/')}/animated_cp/{padded}{ext}"
                else:
                    url = f"{base_url.rstrip('/')}/{folder_name}/{padded}{ext}"

                dest_path = dest_dir / f"{padded}{ext}"

                if dest_path.exists():
                    continue

                if dry_run:
                    self.stdout.write(f'Would download: {url}')
                    downloaded += 1
                    break

                try:
                    response = requests.head(url, timeout=5)
                    if response.status_code == 200:
                        self.stdout.write(f'Downloading: {url}')
                        response = requests.get(url, timeout=30, stream=True)
                        with open(dest_path, 'wb') as f:
                            for chunk in response.iter_content(chunk_size=8192):
                                f.write(chunk)
                        downloaded += 1
                        break  # Found the file, move to next number
                except requests.RequestException:
                    continue

            # Progress indicator
            if num % 100 == 0:
                self.stdout.write(f'Progress: {num}/{end}')

        return downloaded
# core/management/commands/sync_from_ovh.py
"""
Complete FTP sync from OVH to Render persistent disk.
Downloads all postcard images and videos.
"""

from django.core.management.base import BaseCommand
from django.conf import settings
from pathlib import Path
import ftplib
import os
import time
import socket


def get_media_root():
    """Get the correct media root path - always use persistent disk on Render"""
    if os.environ.get('RENDER', 'false').lower() == 'true' or Path('/var/data').exists():
        return Path('/var/data/media')
    return Path(settings.MEDIA_ROOT)


class Command(BaseCommand):
    help = 'Sync all postcard images and videos from OVH FTP server to persistent disk'

    def add_arguments(self, parser):
        parser.add_argument('--ftp-host', type=str, help='FTP host')
        parser.add_argument('--ftp-user', type=str, help='FTP username')
        parser.add_argument('--ftp-pass', type=str, help='FTP password')
        parser.add_argument('--ftp-path', type=str, default='/collection_cp/cartes',
                            help='Base path on FTP server for postcard images')
        parser.add_argument('--animated-path', type=str, default='/collection_cp/cartes/animated_cp',
                            help='Path on FTP server for animated videos')
        parser.add_argument('--folders', type=str, default='Vignette,Grande,Dos,Zoom',
                            help='Comma-separated list of folders to sync')
        parser.add_argument('--include-animated', action='store_true', default=True,
                            help='Also sync animated videos')
        parser.add_argument('--skip-existing', action='store_true', default=True,
                            help='Skip files that already exist locally')
        parser.add_argument('--limit', type=int, default=0,
                            help='Limit files per folder (0 = no limit)')
        parser.add_argument('--dry-run', action='store_true',
                            help='Show what would be downloaded without downloading')
        parser.add_argument('--verbose', action='store_true',
                            help='Show detailed progress')
        parser.add_argument('--timeout', type=int, default=60,
                            help='FTP timeout in seconds')
        parser.add_argument('--retry', type=int, default=3,
                            help='Number of retries for failed downloads')

    def handle(self, *args, **options):
        # Get FTP credentials
        ftp_host = options.get('ftp_host') or os.environ.get('OVH_FTP_HOST', '')
        ftp_user = options.get('ftp_user') or os.environ.get('OVH_FTP_USER', '')
        ftp_pass = options.get('ftp_pass') or os.environ.get('OVH_FTP_PASS', '')

        if not all([ftp_host, ftp_user, ftp_pass]):
            self.stderr.write(self.style.ERROR(
                'Missing FTP credentials!\n'
                'Set via arguments or environment variables:\n'
                '  OVH_FTP_HOST, OVH_FTP_USER, OVH_FTP_PASS'
            ))
            return

        ftp_path = options['ftp_path']
        animated_path = options['animated_path']
        folders = [f.strip() for f in options['folders'].split(',')]
        include_animated = options['include_animated']
        skip_existing = options['skip_existing']
        limit = options['limit']
        dry_run = options['dry_run']
        verbose = options['verbose']
        timeout = options['timeout']
        retry_count = options['retry']

        # CRITICAL: Get the correct media root (persistent disk)
        media_root = get_media_root()

        self.stdout.write(f"\n{'=' * 70}")
        self.stdout.write(f"OVH FTP to Render Persistent Disk Sync")
        self.stdout.write(f"{'=' * 70}")
        self.stdout.write(f"FTP Host: {ftp_host}")
        self.stdout.write(f"FTP Path: {ftp_path}")
        self.stdout.write(f"RENDER env: {os.environ.get('RENDER', 'not set')}")
        self.stdout.write(f"/var/data exists: {Path('/var/data').exists()}")
        self.stdout.write(self.style.SUCCESS(f"Local Media Root: {media_root}"))
        self.stdout.write(f"Media Root exists: {media_root.exists()}")
        self.stdout.write(f"Folders to sync: {folders}")
        self.stdout.write(f"Include Animated: {include_animated}")
        self.stdout.write(f"Skip Existing: {skip_existing}")
        if limit:
            self.stdout.write(f"Limit per folder: {limit}")
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN MODE - No files will be downloaded"))
        self.stdout.write(f"{'=' * 70}\n")

        # Ensure local directories exist
        if not dry_run:
            self.create_directories(media_root, folders, include_animated)

        # Connect to FTP
        ftp = None
        try:
            self.stdout.write(f"Connecting to {ftp_host}...")
            ftp = ftplib.FTP(timeout=timeout)
            ftp.connect(ftp_host)
            ftp.login(ftp_user, ftp_pass)
            ftp.set_pasv(True)  # Use passive mode
            self.stdout.write(self.style.SUCCESS(f"✓ Connected successfully"))

            # Show FTP welcome message
            if verbose:
                self.stdout.write(f"  Server: {ftp.getwelcome()}")

            total_stats = {'downloaded': 0, 'skipped': 0, 'errors': 0, 'bytes': 0}

            # Sync each postcard folder
            for folder in folders:
                remote_path = f"{ftp_path}/{folder}"
                local_path = media_root / 'postcards' / folder

                stats = self.sync_folder(
                    ftp, remote_path, local_path, folder,
                    limit, dry_run, skip_existing, verbose, retry_count
                )

                for key in total_stats:
                    total_stats[key] += stats.get(key, 0)

            # Sync animated videos
            if include_animated:
                local_animated = media_root / 'animated_cp'
                stats = self.sync_folder(
                    ftp, animated_path, local_animated, 'animated_cp',
                    limit, dry_run, skip_existing, verbose, retry_count,
                    extensions=('.mp4', '.webm', '.MP4', '.WEBM')
                )
                for key in total_stats:
                    total_stats[key] += stats.get(key, 0)

            # Final summary
            self.stdout.write(f"\n{'=' * 70}")
            self.stdout.write(self.style.SUCCESS("SYNC COMPLETE"))
            self.stdout.write(f"{'=' * 70}")
            self.stdout.write(f"Total Downloaded: {total_stats['downloaded']}")
            self.stdout.write(f"Total Skipped: {total_stats['skipped']}")
            self.stdout.write(f"Total Errors: {total_stats['errors']}")
            size_mb = total_stats['bytes'] / (1024 * 1024)
            self.stdout.write(f"Total Size: {size_mb:.2f} MB")
            self.stdout.write(f"Files saved to: {media_root}")
            self.stdout.write(f"{'=' * 70}\n")

        except ftplib.all_errors as e:
            self.stderr.write(self.style.ERROR(f"FTP Error: {e}"))
            return
        except socket.timeout as e:
            self.stderr.write(self.style.ERROR(f"Connection timeout: {e}"))
            return
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Error: {e}"))
            import traceback
            traceback.print_exc()
            return
        finally:
            if ftp:
                try:
                    ftp.quit()
                except:
                    pass

    def create_directories(self, media_root, folders, include_animated):
        """Create all necessary local directories"""
        self.stdout.write("Creating local directories on persistent disk...")

        # Ensure media root exists
        media_root.mkdir(parents=True)
        self.stdout.write(f"  ✓ {media_root}")

        for folder in folders:
            path = media_root / 'postcards' / folder
            path.mkdir(parents=True, exist_ok=True)
            self.stdout.write(f"  ✓ {path}")

        if include_animated:
            path = media_root / 'animated_cp'
            path.mkdir(parents=True, exist_ok=True)
            self.stdout.write(f"  ✓ {path}")

        # Also create signatures folder
        sig_path = media_root / 'signatures'
        sig_path.mkdir(parents=True, exist_ok=True)
        self.stdout.write(f"  ✓ {sig_path}")
        self.stdout.write("")

    def sync_folder(self, ftp, remote_path, local_path, folder_name,
                    limit, dry_run, skip_existing, verbose, retry_count,
                    extensions=('.jpg', '.jpeg', '.png', '.gif', '.JPG', '.JPEG', '.PNG', '.GIF')):
        """Sync a single folder from FTP"""

        stats = {'downloaded': 0, 'skipped': 0, 'errors': 0, 'bytes': 0}

        self.stdout.write(f"\n{'─' * 60}")
        self.stdout.write(f"Syncing: {folder_name}")
        self.stdout.write(f"  Remote: {remote_path}")
        self.stdout.write(f"  Local: {local_path}")

        # Ensure local path exists
        local_path.mkdir(parents=True, exist_ok=True)

        # Try to change to remote directory
        try:
            ftp.cwd(remote_path)
        except ftplib.error_perm as e:
            self.stderr.write(self.style.WARNING(f"  ✗ Cannot access {remote_path}: {e}"))
            return stats

        # List files
        file_list = []
        try:
            # Try MLSD first (more reliable)
            for name, facts in ftp.mlsd():
                if facts.get('type') == 'file':
                    if any(name.lower().endswith(ext.lower()) for ext in extensions):
                        file_list.append(name)
        except:
            # Fallback to NLST
            try:
                all_files = ftp.nlst()
                file_list = [f for f in all_files
                             if any(f.lower().endswith(ext.lower()) for ext in extensions)]
            except ftplib.error_perm as e:
                self.stderr.write(self.style.WARNING(f"  ✗ Cannot list files: {e}"))
                return stats

        self.stdout.write(f"  Found {len(file_list)} files")

        if limit > 0 and len(file_list) > limit:
            file_list = file_list[:limit]
            self.stdout.write(f"  Limited to {limit} files")

        if not file_list:
            return stats

        # Download files
        for i, filename in enumerate(file_list, 1):
            local_file = local_path / filename

            # Skip existing
            if skip_existing and local_file.exists() and local_file.stat().st_size > 0:
                stats['skipped'] += 1
                if verbose:
                    self.stdout.write(f"    [{i}/{len(file_list)}] Skip: {filename}")
                continue

            if dry_run:
                self.stdout.write(f"    [{i}/{len(file_list)}] Would download: {filename}")
                stats['downloaded'] += 1
                continue

            # Download file with retry
            success = False
            for attempt in range(retry_count):
                try:
                    if verbose or i % 100 == 0 or i == len(file_list):
                        self.stdout.write(f"    [{i}/{len(file_list)}] Downloading: {filename}", ending='')

                    with open(local_file, 'wb') as f:
                        ftp.retrbinary(f'RETR {filename}', f.write)

                    file_size = local_file.stat().st_size
                    stats['bytes'] += file_size
                    stats['downloaded'] += 1
                    success = True

                    if verbose or i % 100 == 0 or i == len(file_list):
                        self.stdout.write(self.style.SUCCESS(f" ✓ ({file_size / 1024:.1f} KB)"))
                    break

                except Exception as e:
                    if attempt < retry_count - 1:
                        time.sleep(1)
                    else:
                        stats['errors'] += 1
                        self.stdout.write(self.style.ERROR(f" ✗ {e}"))
                        if local_file.exists():
                            local_file.unlink()

        self.stdout.write(f"  Summary: {stats['downloaded']} downloaded, "
                          f"{stats['skipped']} skipped, {stats['errors']} errors")


        return stats

# core/management/commands/render_setup.py
"""
One command to set up everything on Render after deployment.
Run: python manage.py render_setup --csv /path/to/data.csv
"""

from django.core.management.base import BaseCommand
from django.core.management import call_command
from pathlib import Path
import os


class Command(BaseCommand):
    help = 'Complete Render setup - creates dirs, syncs from OVH, imports CSV, updates flags'

    def add_arguments(self, parser):
        parser.add_argument('--csv', type=str, required=True, help='Path to CSV file')
        parser.add_argument('--limit', type=int, default=0, help='Limit for testing (0=no limit)')
        parser.add_argument('--skip-sync', action='store_true', help='Skip FTP sync')

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("\n" + "=" * 70))
        self.stdout.write(self.style.SUCCESS("RENDER COMPLETE SETUP"))
        self.stdout.write(self.style.SUCCESS("=" * 70))

        # Check environment
        is_render = os.environ.get('RENDER', 'false').lower() == 'true'
        persistent_exists = Path('/var/data').exists()

        self.stdout.write(f"\nEnvironment Check:")
        self.stdout.write(f"  RENDER env: {is_render}")
        self.stdout.write(f"  /var/data exists: {persistent_exists}")

        if persistent_exists:
            media_root = Path('/var/data/media')
        else:
            media_root = Path('media')

        self.stdout.write(f"  Media root: {media_root}")

        # Step 1: Check FTP credentials
        ftp_host = os.environ.get('OVH_FTP_HOST')
        ftp_user = os.environ.get('OVH_FTP_USER')
        ftp_pass = os.environ.get('OVH_FTP_PASS')

        self.stdout.write(f"\nFTP Credentials:")
        self.stdout.write(f"  OVH_FTP_HOST: {'SET' if ftp_host else 'NOT SET'}")
        self.stdout.write(f"  OVH_FTP_USER: {'SET' if ftp_user else 'NOT SET'}")
        self.stdout.write(f"  OVH_FTP_PASS: {'SET' if ftp_pass else 'NOT SET'}")

        # Step 2: Create directories
        self.stdout.write(self.style.HTTP_INFO("\n[1/4] Creating directories..."))
        directories = [
            media_root / 'postcards' / 'Vignette',
            media_root / 'postcards' / 'Grande',
            media_root / 'postcards' / 'Dos',
            media_root / 'postcards' / 'Zoom',
            media_root / 'animated_cp',
            media_root / 'signatures',
        ]
        for d in directories:
            d.mkdir(parents=True, exist_ok=True)
            self.stdout.write(f"  ✓ {d}")

        # Step 3: Sync from OVH
        if not options['skip_sync'] and all([ftp_host, ftp_user, ftp_pass]):
            self.stdout.write(self.style.HTTP_INFO("\n[2/4] Syncing from OVH FTP..."))
            sync_kwargs = {
                'ftp_host': ftp_host,
                'ftp_user': ftp_user,
                'ftp_pass': ftp_pass,
                'include_animated': True,
                'skip_existing': True,
            }
            if options['limit']:
                sync_kwargs['limit'] = options['limit']
            call_command('sync_from_ovh', **sync_kwargs)
        else:
            self.stdout.write(self.style.WARNING("\n[2/4] Skipping FTP sync (no credentials or --skip-sync)"))

        # Step 4: Import CSV
        csv_path = options['csv']
        if csv_path and Path(csv_path).exists():
            self.stdout.write(self.style.HTTP_INFO(f"\n[3/4] Importing CSV: {csv_path}"))
            import_kwargs = {'update': True}
            if options['limit']:
                import_kwargs['limit'] = options['limit']
            call_command('import_csv', csv_path, **import_kwargs)
        else:
            self.stdout.write(self.style.WARNING(f"\n[3/4] CSV file not found: {csv_path}"))

        # Step 5: Update flags
        self.stdout.write(self.style.HTTP_INFO("\n[4/4] Updating postcard flags..."))
        call_command('update_flags')

        # Summary
        self.stdout.write(self.style.SUCCESS("\n" + "=" * 70))
        self.stdout.write(self.style.SUCCESS("SETUP COMPLETE!"))
        self.stdout.write(self.style.SUCCESS("=" * 70))

        # Show final status
        call_command('check_media')
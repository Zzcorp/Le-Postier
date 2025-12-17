# core/management/commands/full_setup.py
"""
Complete setup command - runs all necessary setup steps.
"""

from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.conf import settings
from pathlib import Path
import os


class Command(BaseCommand):
    help = 'Complete setup: sync images, import CSV, update flags'

    def add_arguments(self, parser):
        parser.add_argument('--csv', type=str, help='Path to CSV file for import')
        parser.add_argument('--ftp-host', type=str, help='FTP host')
        parser.add_argument('--ftp-user', type=str, help='FTP username')
        parser.add_argument('--ftp-pass', type=str, help='FTP password')
        parser.add_argument('--skip-sync', action='store_true',
                            help='Skip FTP sync')
        parser.add_argument('--skip-import', action='store_true',
                            help='Skip CSV import')
        parser.add_argument('--limit', type=int, default=0,
                            help='Limit files/rows for testing')

    def handle(self, *args, **options):
        self.stdout.write(f"\n{'=' * 70}")
        self.stdout.write("LE POSTIER - COMPLETE SETUP")
        self.stdout.write(f"{'=' * 70}\n")

        # Step 1: Sync from FTP
        if not options['skip_sync']:
            self.stdout.write(self.style.HTTP_INFO("STEP 1: Syncing images from OVH FTP..."))

            ftp_host = options.get('ftp_host') or os.environ.get('OVH_FTP_HOST')
            ftp_user = options.get('ftp_user') or os.environ.get('OVH_FTP_USER')
            ftp_pass = options.get('ftp_pass') or os.environ.get('OVH_FTP_PASS')

            if all([ftp_host, ftp_user, ftp_pass]):
                call_command(
                    'sync_from_ovh',
                    ftp_host=ftp_host,
                    ftp_user=ftp_user,
                    ftp_pass=ftp_pass,
                    include_animated=True,
                    skip_existing=True,
                    limit=options['limit'] if options['limit'] else 0,
                )
            else:
                self.stdout.write(self.style.WARNING(
                    "  Skipping FTP sync - credentials not provided\n"
                    "  Set: OVH_FTP_HOST, OVH_FTP_USER, OVH_FTP_PASS"
                ))
        else:
            self.stdout.write("STEP 1: Skipped FTP sync")

        # Step 2: Import CSV
        if not options['skip_import'] and options.get('csv'):
            self.stdout.write(self.style.HTTP_INFO("\nSTEP 2: Importing CSV data..."))

            call_command(
                'import_csv',
                options['csv'],
                update=True,
                limit=options['limit'] if options['limit'] else 0,
            )
        elif options.get('csv'):
            self.stdout.write("\nSTEP 2: Skipped CSV import")
        else:
            self.stdout.write("\nSTEP 2: No CSV file provided, skipping import")

        # Step 3: Update flags
        self.stdout.write(self.style.HTTP_INFO("\nSTEP 3: Updating postcard flags..."))
        call_command('update_flags')

        # Step 4: Create admin if needed
        self.stdout.write(self.style.HTTP_INFO("\nSTEP 4: Ensuring admin user exists..."))
        call_command('create_admin')

        # Final summary
        self.stdout.write(f"\n{'=' * 70}")
        self.stdout.write(self.style.SUCCESS("SETUP COMPLETE!"))
        self.stdout.write(f"{'=' * 70}")

        # Show status
        from core.models import Postcard
        total = Postcard.objects.count()
        with_images = Postcard.objects.filter(has_images=True).count()

        self.stdout.write(f"\nDatabase Status:")
        self.stdout.write(f"  Total postcards: {total}")
        self.stdout.write(f"  With images: {with_images}")

        media_root = Path(settings.MEDIA_ROOT)
        self.stdout.write(f"\nMedia Status:")
        for folder in ['Vignette', 'Grande', 'Dos', 'Zoom']:
            path = media_root / 'postcards' / folder
            if path.exists():
                count = len(list(path.glob('*.*')))
                self.stdout.write(f"  {folder}: {count} files")

        animated_path = media_root / 'animated_cp'
        if animated_path.exists():
            count = len(list(animated_path.glob('*.*')))
            self.stdout.write(f"  Animated: {count} files")

        self.stdout.write(f"\n{'=' * 70}\n")
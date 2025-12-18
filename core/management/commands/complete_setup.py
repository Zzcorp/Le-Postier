# core/management/commands/complete_setup.py
"""
Complete setup command - runs all steps in order:
1. Sync images from OVH FTP
2. Populate DB from images
3. Import CSV metadata
4. Update flags

Usage:
  python manage.py complete_setup --csv /path/to/data.csv
"""

from django.core.management.base import BaseCommand
from django.core.management import call_command
from pathlib import Path
import os


def get_media_root():
    """Get the correct media root path"""
    if os.environ.get('RENDER', 'false').lower() == 'true' or Path('/var/data').exists():
        return Path('/var/data/media')
    from django.conf import settings
    return Path(settings.MEDIA_ROOT)


class Command(BaseCommand):
    help = 'Complete setup: sync from OVH, populate DB, import CSV, update flags'

    def add_arguments(self, parser):
        parser.add_argument('--csv', type=str, help='Path to CSV file for metadata import')
        parser.add_argument('--skip-sync', action='store_true', help='Skip FTP sync')
        parser.add_argument('--skip-populate', action='store_true', help='Skip DB population from images')
        parser.add_argument('--skip-csv', action='store_true', help='Skip CSV import')
        parser.add_argument('--limit', type=int, default=0, help='Limit files for testing')
        parser.add_argument('--dry-run', action='store_true', help='Preview without changes')

    def handle(self, *args, **options):
        media_root = get_media_root()

        self.stdout.write(self.style.SUCCESS(f"\n{'=' * 70}"))
        self.stdout.write(self.style.SUCCESS("LE POSTIER - COMPLETE SETUP"))
        self.stdout.write(self.style.SUCCESS(f"{'=' * 70}"))
        self.stdout.write(f"Environment: {'Render' if os.environ.get('RENDER') else 'Local'}")
        self.stdout.write(f"Media Root: {media_root}")
        self.stdout.write(f"{'=' * 70}\n")

        # Step 0: Create directories
        self.stdout.write(self.style.HTTP_INFO("[STEP 0] Creating directories..."))
        self.create_directories(media_root)

        # Step 1: Sync from OVH FTP
        if not options['skip_sync']:
            self.stdout.write(self.style.HTTP_INFO("\n[STEP 1] Syncing from OVH FTP..."))

            ftp_host = os.environ.get('OVH_FTP_HOST')
            ftp_user = os.environ.get('OVH_FTP_USER')
            ftp_pass = os.environ.get('OVH_FTP_PASS')

            if all([ftp_host, ftp_user, ftp_pass]):
                sync_args = {
                    'ftp_host': ftp_host,
                    'ftp_user': ftp_user,
                    'ftp_pass': ftp_pass,
                    'include_animated': True,
                    'skip_existing': True,
                }
                if options['limit']:
                    sync_args['limit'] = options['limit']
                if options['dry_run']:
                    sync_args['dry_run'] = True

                call_command('sync_from_ovh', **sync_args)
            else:
                self.stdout.write(self.style.WARNING(
                    "  Skipping FTP sync - credentials not set\n"
                    "  Set: OVH_FTP_HOST, OVH_FTP_USER, OVH_FTP_PASS"
                ))
        else:
            self.stdout.write("\n[STEP 1] Skipped FTP sync (--skip-sync)")

        # Step 2: Populate DB from images
        if not options['skip_populate']:
            self.stdout.write(self.style.HTTP_INFO("\n[STEP 2] Populating database from images..."))

            populate_args = {'update': True}
            if options['dry_run']:
                populate_args['dry_run'] = True

            call_command('populate_from_images', **populate_args)
        else:
            self.stdout.write("\n[STEP 2] Skipped DB population (--skip-populate)")

        # Step 3: Import CSV metadata
        csv_path = options.get('csv')
        if not options['skip_csv'] and csv_path:
            self.stdout.write(self.style.HTTP_INFO(f"\n[STEP 3] Importing CSV metadata: {csv_path}"))

            if Path(csv_path).exists():
                import_args = {
                    'update': True,
                    'create_missing': True,
                }
                if options['limit']:
                    import_args['limit'] = options['limit']
                if options['dry_run']:
                    import_args['dry_run'] = True

                call_command('import_csv', csv_path, **import_args)
            else:
                self.stdout.write(self.style.ERROR(f"  CSV file not found: {csv_path}"))
        elif not csv_path:
            self.stdout.write("\n[STEP 3] Skipped CSV import (no --csv provided)")
        else:
            self.stdout.write("\n[STEP 3] Skipped CSV import (--skip-csv)")

        # Step 4: Update flags
        if not options['dry_run']:
            self.stdout.write(self.style.HTTP_INFO("\n[STEP 4] Updating postcard flags..."))
            call_command('update_flags')

        # Step 5: Create admin user
        if not options['dry_run']:
            self.stdout.write(self.style.HTTP_INFO("\n[STEP 5] Ensuring admin user exists..."))
            call_command('create_admin')

        # Final summary
        self.stdout.write(f"\n{'=' * 70}")
        self.stdout.write(self.style.SUCCESS("SETUP COMPLETE!"))
        self.stdout.write(f"{'=' * 70}")

        # Show status
        self.show_status(media_root)

    def create_directories(self, media_root):
        """Create all necessary directories"""
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

    def show_status(self, media_root):
        """Show current status"""
        from core.models import Postcard

        self.stdout.write("\nDatabase Status:")
        total = Postcard.objects.count()
        with_images = Postcard.objects.filter(has_images=True).count()
        self.stdout.write(f"  Total postcards: {total}")
        self.stdout.write(f"  With images: {with_images}")

        self.stdout.write(f"\nMedia Files ({media_root}):")
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
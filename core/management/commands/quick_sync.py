# core/management/commands/quick_sync.py
"""
Quick sync - downloads first N images to test
"""
from django.core.management.base import BaseCommand
from django.core.management import call_command
import os


class Command(BaseCommand):
    help = 'Quick sync test - downloads first 100 images'

    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=100)
        parser.add_argument('--full', action='store_true', help='Full sync (no limit)')

    def handle(self, *args, **options):
        ftp_host = os.environ.get('OVH_FTP_HOST')
        ftp_user = os.environ.get('OVH_FTP_USER')
        ftp_pass = os.environ.get('OVH_FTP_PASS')

        if not all([ftp_host, ftp_user, ftp_pass]):
            self.stdout.write(self.style.ERROR(
                "Missing FTP credentials! Set OVH_FTP_HOST, OVH_FTP_USER, OVH_FTP_PASS"
            ))
            return

        limit = None if options['full'] else options['limit']

        call_command(
            'sync_from_ovh',
            ftp_host=ftp_host,
            ftp_user=ftp_user,
            ftp_pass=ftp_pass,
            limit=limit,
            include_animated=True,
        )
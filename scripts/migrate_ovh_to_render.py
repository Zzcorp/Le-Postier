#!/usr/bin/env python
"""
Complete migration from OVH to Render
Run this on Render after deployment
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'le_postier.settings')
django.setup()

from django.core.management import call_command


def main():
    print("=" * 60)
    print("OVH to Render Migration Script")
    print("=" * 60)

    # Get FTP credentials from environment
    ftp_host = os.environ.get('OVH_FTP_HOST')
    ftp_user = os.environ.get('OVH_FTP_USER')
    ftp_pass = os.environ.get('OVH_FTP_PASS')

    if not all([ftp_host, ftp_user, ftp_pass]):
        print("ERROR: FTP credentials not found in environment")
        print("Please set: OVH_FTP_HOST, OVH_FTP_USER, OVH_FTP_PASS")
        sys.exit(1)

    # Test run first (10 postcards)
    print("\n1. Running test migration (10 postcards)...")
    call_command(
        'migrate_from_ovh',
        ftp_host=ftp_host,
        ftp_user=ftp_user,
        ftp_pass=ftp_pass,
        limit=10,
        dry_run=False
    )

    response = input("\nTest successful. Continue with full migration? (yes/no): ")
    if response.lower() != 'yes':
        print("Migration cancelled.")
        return

    # Full migration
    print("\n2. Running full migration...")
    call_command(
        'migrate_from_ovh',
        ftp_host=ftp_host,
        ftp_user=ftp_user,
        ftp_pass=ftp_pass
    )

    # Update flags
    print("\n3. Updating postcard flags...")
    call_command('update_postcard_flags')

    print("\n" + "=" * 60)
    print("Migration Complete!")
    print("=" * 60)


if __name__ == '__main__':
    main()
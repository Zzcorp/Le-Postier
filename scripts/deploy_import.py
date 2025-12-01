#!/usr/bin/env python
"""
Safe deployment import script
Run this after deployment to import all data
"""

import os
import sys
import django
from django.core.management import call_command

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'le_postier.settings_production')
django.setup()


def main():
    print("Starting safe import process...")

    # Step 1: Test connection
    print("\n1. Testing database connection...")
    from django.db import connection
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
        print("✓ Database connection successful")

    # Step 2: Create backup point
    print("\n2. Creating backup point...")
    from core.models import Postcard
    initial_count = Postcard.objects.count()
    print(f"Current postcards in database: {initial_count}")

    # Step 3: Import in test mode first
    print("\n3. Running test import (first 10 items)...")
    call_command('import_from_production', test=True)

    # Step 4: Verify test import
    test_count = Postcard.objects.count()
    if test_count > initial_count:
        print(f"✓ Test import successful. Added {test_count - initial_count} postcards")

        # Step 5: Ask for confirmation
        response = input("\nProceed with full import? (yes/no): ")
        if response.lower() == 'yes':
            print("\n4. Running full import...")
            call_command('import_from_production')

            final_count = Postcard.objects.count()
            print(f"\n✓ Import complete! Total postcards: {final_count}")
        else:
            print("Import cancelled.")
    else:
        print("✗ Test import failed. No postcards added.")


if __name__ == "__main__":
    main()
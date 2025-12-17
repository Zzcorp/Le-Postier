#!/usr/bin/env python
"""
Setup script for Render deployment.
Run from Django shell or as management command.
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'le_postier.settings')

import django

django.setup()

from django.conf import settings
from core.models import Postcard, Theme, CustomUser


def setup_directories():
    """Create all necessary directories"""
    print("Setting up directories...")

    media_root = Path(settings.MEDIA_ROOT)

    directories = [
        media_root / 'postcards' / 'Vignette',
        media_root / 'postcards' / 'Grande',
        media_root / 'postcards' / 'Dos',
        media_root / 'postcards' / 'Zoom',
        media_root / 'animated_cp',
        media_root / 'signatures',
    ]

    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
        print(f"  ✓ {directory}")

    print("Directories setup complete!\n")


def create_default_themes():
    """Create default themes"""
    print("Creating default themes...")

    themes = [
        ('seine', 'Seine', 1),
        ('marne', 'Marne', 2),
        ('bateau', 'Bateaux', 3),
        ('peniche', 'Péniches', 4),
        ('navigation', 'Navigation', 5),
        ('paris', 'Paris', 6),
        ('pont', 'Ponts', 7),
        ('ecluse', 'Écluses', 8),
        ('port', 'Ports', 9),
        ('quai', 'Quais', 10),
    ]

    for name, display_name, order in themes:
        theme, created = Theme.objects.get_or_create(
            name=name,
            defaults={'display_name': display_name, 'order': order}
        )
        status = "created" if created else "exists"
        print(f"  {status}: {display_name}")

    print("Themes setup complete!\n")


def check_media_status():
    """Check status of media files"""
    print("Checking media status...")

    media_root = Path(settings.MEDIA_ROOT)

    folders = {
        'Vignette': media_root / 'postcards' / 'Vignette',
        'Grande': media_root / 'postcards' / 'Grande',
        'Dos': media_root / 'postcards' / 'Dos',
        'Zoom': media_root / 'postcards' / 'Zoom',
        'Animated': media_root / 'animated_cp',
    }

    for name, path in folders.items():
        if path.exists():
            files = list(path.glob('*.*'))
            print(f"  {name}: {len(files)} files")
        else:
            print(f"  {name}: NOT FOUND")

    print()


def check_database_status():
    """Check database status"""
    print("Checking database status...")

    postcard_count = Postcard.objects.count()
    with_images = Postcard.objects.filter(has_images=True).count()
    theme_count = Theme.objects.count()
    user_count = CustomUser.objects.count()

    print(f"  Postcards: {postcard_count}")
    print(f"  With images: {with_images}")
    print(f"  Themes: {theme_count}")
    print(f"  Users: {user_count}")
    print()


def main():
    print("=" * 60)
    print("Le Postier - Render Setup Script")
    print("=" * 60)
    print()

    setup_directories()
    create_default_themes()
    check_media_status()
    check_database_status()

    print("=" * 60)
    print("Setup complete!")
    print()
    print("Next steps:")
    print("1. Set OVH FTP environment variables:")
    print("   OVH_FTP_HOST, OVH_FTP_USER, OVH_FTP_PASS")
    print()
    print("2. Run: python manage.py sync_from_ovh")
    print("3. Run: python manage.py import_postcards_csv your_data.csv")
    print("   OR: python manage.py quick_populate")
    print()
    print("4. Run: python manage.py create_admin")
    print("=" * 60)


if __name__ == '__main__':
    main()
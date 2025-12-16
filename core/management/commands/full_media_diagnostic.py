# core/management/commands/full_media_diagnostic.py
"""
Complete diagnostic of media files and database state
"""

from django.core.management.base import BaseCommand
from django.conf import settings
from pathlib import Path
from core.models import Postcard
import os


class Command(BaseCommand):
    help = 'Complete diagnostic of media files and database'

    def add_arguments(self, parser):
        parser.add_argument('--fix', action='store_true', help='Attempt to fix issues')
        parser.add_argument('--verbose', action='store_true', help='Show detailed output')

    def handle(self, *args, **options):
        self.stdout.write("=" * 70)
        self.stdout.write("FULL MEDIA DIAGNOSTIC REPORT")
        self.stdout.write("=" * 70)

        issues = []

        # 1. Check MEDIA_ROOT
        media_root = Path(settings.MEDIA_ROOT)
        self.stdout.write(f"\n📁 MEDIA CONFIGURATION")
        self.stdout.write(f"   MEDIA_ROOT: {media_root}")
        self.stdout.write(f"   MEDIA_URL: {settings.MEDIA_URL}")
        self.stdout.write(f"   Exists: {media_root.exists()}")

        if not media_root.exists():
            issues.append("MEDIA_ROOT directory does not exist")
            self.stdout.write(self.style.ERROR("   ❌ MEDIA_ROOT does not exist!"))
            if options['fix']:
                media_root.mkdir(parents=True, exist_ok=True)
                self.stdout.write(self.style.SUCCESS("   ✓ Created MEDIA_ROOT"))

        # 2. Check folder structure
        self.stdout.write(f"\n📂 FOLDER STRUCTURE")
        expected_folders = [
            media_root / 'postcards' / 'Vignette',
            media_root / 'postcards' / 'Grande',
            media_root / 'postcards' / 'Dos',
            media_root / 'postcards' / 'Zoom',
            media_root / 'animated_cp',
            media_root / 'signatures',
        ]

        for folder in expected_folders:
            if folder.exists():
                file_count = len(list(folder.glob('*.*')))
                size = sum(f.stat().st_size for f in folder.glob('*.*') if f.is_file())
                size_mb = size / (1024 * 1024)
                self.stdout.write(f"   ✓ {folder.relative_to(media_root)}: {file_count} files ({size_mb:.2f} MB)")
            else:
                issues.append(f"Missing folder: {folder}")
                self.stdout.write(self.style.WARNING(f"   ❌ {folder.relative_to(media_root)}: NOT FOUND"))
                if options['fix']:
                    folder.mkdir(parents=True, exist_ok=True)
                    self.stdout.write(self.style.SUCCESS(f"      ✓ Created folder"))

        # 3. Analyze image files
        self.stdout.write(f"\n🖼️ IMAGE FILES ANALYSIS")

        vignette_folder = media_root / 'postcards' / 'Vignette'
        if vignette_folder.exists():
            vignettes = list(vignette_folder.glob('*.*'))
            image_extensions = {'.jpg', '.jpeg', '.png', '.gif'}
            valid_images = [f for f in vignettes if f.suffix.lower() in image_extensions]

            self.stdout.write(f"   Total files in Vignette: {len(vignettes)}")
            self.stdout.write(f"   Valid image files: {len(valid_images)}")

            if valid_images:
                # Extract numbers from filenames
                numbers_in_files = set()
                for f in valid_images:
                    num = ''.join(filter(str.isdigit, f.stem))
                    if num:
                        numbers_in_files.add(num.zfill(6))

                self.stdout.write(f"   Unique postcard numbers found: {len(numbers_in_files)}")

                if options['verbose'] and valid_images[:5]:
                    self.stdout.write(f"   Sample files: {', '.join(f.name for f in valid_images[:5])}")

        # 4. Database analysis
        self.stdout.write(f"\n🗄️ DATABASE ANALYSIS")

        total_postcards = Postcard.objects.count()
        self.stdout.write(f"   Total postcards in DB: {total_postcards}")

        if total_postcards == 0:
            issues.append("No postcards in database")
            self.stdout.write(self.style.ERROR("   ❌ Database is empty!"))
        else:
            # Check which postcards have images
            postcards = list(Postcard.objects.all()[:1000])  # Sample
            with_vignette = 0
            with_grande = 0
            with_animation = 0

            for p in postcards:
                if p.get_vignette_url():
                    with_vignette += 1
                if p.get_grande_url():
                    with_grande += 1
                if p.get_animated_urls():
                    with_animation += 1

            self.stdout.write(f"   Postcards with vignettes (sample 1000): {with_vignette}")
            self.stdout.write(f"   Postcards with grande images: {with_grande}")
            self.stdout.write(f"   Postcards with animations: {with_animation}")

            if with_vignette == 0 and total_postcards > 0 and vignette_folder.exists() and len(valid_images) > 0:
                issues.append("Postcards exist but images not found - possible number mismatch")
                self.stdout.write(
                    self.style.WARNING("   ⚠️ Postcards exist but no images found - checking number format..."))

                # Debug first few postcards
                sample_postcards = Postcard.objects.all()[:5]
                for p in sample_postcards:
                    padded = p.get_padded_number()
                    self.stdout.write(f"      DB: {p.number} -> padded: {padded}")

                    # Check if file exists
                    for ext in ['.jpg', '.jpeg', '.png', '.JPG', '.JPEG', '.PNG']:
                        check_path = vignette_folder / f"{padded}{ext}"
                        if check_path.exists():
                            self.stdout.write(f"         ✓ Found: {check_path.name}")
                            break
                    else:
                        self.stdout.write(f"         ❌ Not found for {padded}")

                        # Try to find similar files
                        similar = [f for f in valid_images if p.number in f.stem or padded in f.stem]
                        if similar:
                            self.stdout.write(f"         Possible matches: {[f.name for f in similar[:3]]}")

        # 5. Check animated videos
        self.stdout.write(f"\n🎬 ANIMATED VIDEOS ANALYSIS")
        animated_folder = media_root / 'animated_cp'
        if animated_folder.exists():
            videos = list(animated_folder.glob('*.mp4')) + list(animated_folder.glob('*.webm'))
            self.stdout.write(f"   Total video files: {len(videos)}")

            if videos and options['verbose']:
                self.stdout.write(f"   Sample videos: {', '.join(v.name for v in videos[:5])}")

        # 6. Summary
        self.stdout.write(f"\n{'=' * 70}")
        self.stdout.write("SUMMARY")
        self.stdout.write("=" * 70)

        if issues:
            self.stdout.write(self.style.WARNING(f"\n⚠️ Found {len(issues)} issues:"))
            for i, issue in enumerate(issues, 1):
                self.stdout.write(f"   {i}. {issue}")
        else:
            self.stdout.write(self.style.SUCCESS("\n✓ No critical issues found"))

        # 7. Recommendations
        self.stdout.write(f"\n📋 RECOMMENDATIONS")

        if total_postcards == 0:
            self.stdout.write("   1. Import postcard data from CSV/SQL")
            self.stdout.write("      Run: python manage.py import_csv_flexible /path/to/data.csv")

        if vignette_folder.exists() and len(valid_images) == 0:
            self.stdout.write("   2. Upload images to the server")
            self.stdout.write("      Images should be in: {media_root}/postcards/Vignette/")

        if total_postcards > 0 and with_vignette == 0 and len(valid_images) > 0:
            self.stdout.write("   3. Image filenames may not match postcard numbers")
            self.stdout.write("      Ensure files are named: 000001.jpg, 000002.jpg, etc.")

        self.stdout.write("")
# core/management/commands/diagnose_media.py
from django.core.management.base import BaseCommand
from django.conf import settings
from pathlib import Path
from core.models import Postcard
import os


class Command(BaseCommand):
    help = 'Diagnose media files and database state'

    def handle(self, *args, **options):
        self.stdout.write("=" * 60)
        self.stdout.write("MEDIA DIAGNOSIS REPORT")
        self.stdout.write("=" * 60)

        # 1. Check MEDIA_ROOT configuration
        media_root = Path(settings.MEDIA_ROOT)
        self.stdout.write(f"\n📁 MEDIA_ROOT: {media_root}")
        self.stdout.write(f"   Exists: {media_root.exists()}")

        if media_root.exists():
            # Check disk space
            import shutil
            total, used, free = shutil.disk_usage(media_root)
            self.stdout.write(f"   Disk Total: {total / (1024 ** 3):.2f} GB")
            self.stdout.write(f"   Disk Used: {used / (1024 ** 3):.2f} GB")
            self.stdout.write(f"   Disk Free: {free / (1024 ** 3):.2f} GB")

        # 2. Check postcards folders
        self.stdout.write(f"\n📂 POSTCARD IMAGE FOLDERS:")
        folders = ['Vignette', 'Grande', 'Dos', 'Zoom']
        folder_counts = {}

        for folder in folders:
            folder_path = media_root / 'postcards' / folder
            if folder_path.exists():
                files = list(folder_path.glob('*.*'))
                image_files = [f for f in files if f.suffix.lower() in ['.jpg', '.jpeg', '.png', '.gif']]
                folder_counts[folder] = len(image_files)

                # Calculate size
                total_size = sum(f.stat().st_size for f in image_files) if image_files else 0
                size_mb = total_size / (1024 * 1024)

                self.stdout.write(f"   {folder}: {len(image_files)} files ({size_mb:.2f} MB)")

                # Show sample files
                if image_files[:3]:
                    self.stdout.write(f"      Sample: {', '.join(f.name for f in image_files[:3])}")
            else:
                folder_counts[folder] = 0
                self.stdout.write(f"   {folder}: ❌ NOT FOUND")

        # 3. Check animated folder
        self.stdout.write(f"\n🎬 ANIMATED VIDEOS:")
        animated_path = media_root / 'animated_cp'
        if animated_path.exists():
            videos = list(animated_path.glob('*.mp4')) + list(animated_path.glob('*.webm'))
            total_size = sum(f.stat().st_size for f in videos) if videos else 0
            size_mb = total_size / (1024 * 1024)
            self.stdout.write(f"   animated_cp: {len(videos)} files ({size_mb:.2f} MB)")
            if videos[:3]:
                self.stdout.write(f"      Sample: {', '.join(f.name for f in videos[:3])}")
        else:
            self.stdout.write(f"   animated_cp: ❌ NOT FOUND")

        # 4. Check database
        self.stdout.write(f"\n🗄️ DATABASE:")
        total_postcards = Postcard.objects.count()
        self.stdout.write(f"   Total Postcards in DB: {total_postcards}")

        if total_postcards > 0:
            # Sample postcards
            samples = Postcard.objects.all()[:5]
            self.stdout.write(f"   Sample postcards:")
            for p in samples:
                vignette = p.get_vignette_url()
                has_img = "✓" if vignette else "✗"
                self.stdout.write(f"      {p.number}: {p.title[:40]}... [{has_img}]")

            # Count with images
            with_images = sum(1 for p in Postcard.objects.all()[:500] if p.check_has_vignette())
            self.stdout.write(f"   Postcards with vignettes (sample 500): {with_images}")

        # 5. Test URL generation
        self.stdout.write(f"\n🔗 URL CONFIGURATION:")
        self.stdout.write(f"   MEDIA_URL: {settings.MEDIA_URL}")

        # Test a specific postcard
        test_postcard = Postcard.objects.first()
        if test_postcard:
            self.stdout.write(f"\n   Testing postcard {test_postcard.number}:")
            self.stdout.write(f"      Padded number: {test_postcard.get_padded_number()}")
            self.stdout.write(f"      Vignette URL: {test_postcard.get_vignette_url() or 'NOT FOUND'}")
            self.stdout.write(f"      Grande URL: {test_postcard.get_grande_url() or 'NOT FOUND'}")
            self.stdout.write(f"      Animated URLs: {test_postcard.get_animated_urls() or 'NONE'}")

        self.stdout.write("\n" + "=" * 60)
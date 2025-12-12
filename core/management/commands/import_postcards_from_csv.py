# core/management/commands/import_postcards_from_csv.py
"""
Import postcards from a CSV file.
Expected CSV format: number,title,description,keywords,rarity

Also scans local media folder to verify which postcards have images.
"""

from django.core.management.base import BaseCommand
from django.conf import settings
from core.models import Postcard
from pathlib import Path
import csv


class Command(BaseCommand):
    help = 'Import postcards from CSV file and/or scan local media folder'

    def add_arguments(self, parser):
        parser.add_argument(
            '--csv',
            type=str,
            help='Path to CSV file to import'
        )
        parser.add_argument(
            '--scan-only',
            action='store_true',
            help='Only scan media folder without importing from CSV'
        )
        parser.add_argument(
            '--create-from-images',
            action='store_true',
            help='Create postcard entries for all images found in media folder'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without making changes'
        )

    def handle(self, *args, **options):
        self.stdout.write('=' * 70)
        self.stdout.write('POSTCARD IMPORT & SCAN UTILITY')
        self.stdout.write('=' * 70)

        media_root = Path(settings.MEDIA_ROOT)
        postcards_dir = media_root / 'postcards'
        animated_dir = media_root / 'animated_cp'

        # Step 1: Scan existing images
        self.stdout.write('\n📂 Scanning media folders...')

        image_numbers = self.scan_image_folders(postcards_dir)
        video_numbers = self.scan_video_folder(animated_dir)

        self.stdout.write(f'\n📊 SCAN RESULTS:')
        self.stdout.write(f'   Vignette images: {len(image_numbers.get("Vignette", set()))}')
        self.stdout.write(f'   Grande images: {len(image_numbers.get("Grande", set()))}')
        self.stdout.write(f'   Dos images: {len(image_numbers.get("Dos", set()))}')
        self.stdout.write(f'   Zoom images: {len(image_numbers.get("Zoom", set()))}')
        self.stdout.write(f'   Animated videos: {len(video_numbers)}')

        # Step 2: Import from CSV if provided
        if options['csv']:
            self.import_from_csv(options['csv'], options['dry_run'])

        # Step 3: Create entries from images if requested
        if options['create_from_images']:
            self.create_from_images(image_numbers, options['dry_run'])

        # Step 4: Show summary
        self.show_summary()

    def scan_image_folders(self, postcards_dir):
        """Scan all image folders and return sets of postcard numbers found."""
        image_numbers = {}

        for folder in ['Vignette', 'Grande', 'Dos', 'Zoom']:
            folder_path = postcards_dir / folder
            numbers = set()

            if folder_path.exists():
                for file in folder_path.iterdir():
                    if file.is_file() and file.suffix.lower() in ['.jpg', '.jpeg', '.png']:
                        # Extract number from filename (e.g., 000001.jpg -> 000001)
                        number = file.stem
                        numbers.add(number)

            image_numbers[folder] = numbers

        return image_numbers

    def scan_video_folder(self, animated_dir):
        """Scan animated folder and return set of postcard numbers with videos."""
        video_numbers = {}

        if not animated_dir.exists():
            return video_numbers

        for file in animated_dir.iterdir():
            if file.is_file() and file.suffix.lower() in ['.mp4', '.webm']:
                # Extract base number from filename
                # Handles: 000001.mp4, 000001_0.mp4, 000001_1.mp4
                name = file.stem
                if '_' in name:
                    base_number = name.rsplit('_', 1)[0]
                else:
                    base_number = name

                if base_number not in video_numbers:
                    video_numbers[base_number] = []
                video_numbers[base_number].append(file.name)

        return video_numbers

    def import_from_csv(self, csv_path, dry_run):
        """Import postcards from CSV file."""
        self.stdout.write(f'\n📄 Importing from CSV: {csv_path}')

        try:
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)

                created = 0
                updated = 0
                errors = 0

                for row in reader:
                    try:
                        number = row.get('number', '').strip()
                        if not number:
                            continue

                        title = row.get('title', '').strip() or f'Carte postale {number}'
                        description = row.get('description', '').strip()
                        keywords = row.get('keywords', '').strip()
                        rarity = row.get('rarity', 'common').strip()

                        if rarity not in ['common', 'rare', 'very_rare']:
                            rarity = 'common'

                        if dry_run:
                            self.stdout.write(f'   Would import: {number} - {title[:50]}')
                        else:
                            postcard, was_created = Postcard.objects.update_or_create(
                                number=number,
                                defaults={
                                    'title': title,
                                    'description': description,
                                    'keywords': keywords,
                                    'rarity': rarity,
                                }
                            )

                            if was_created:
                                created += 1
                            else:
                                updated += 1

                    except Exception as e:
                        errors += 1
                        self.stdout.write(self.style.ERROR(f'   Error: {e}'))

                self.stdout.write(f'\n   ✅ Created: {created}')
                self.stdout.write(f'   📝 Updated: {updated}')
                if errors:
                    self.stdout.write(self.style.ERROR(f'   ❌ Errors: {errors}'))

        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f'   ❌ CSV file not found: {csv_path}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'   ❌ Error reading CSV: {e}'))

    def create_from_images(self, image_numbers, dry_run):
        """Create postcard entries for images that don't have database entries."""
        self.stdout.write('\n🔧 Creating postcards from images...')

        # Get all unique numbers from Vignette (primary) or other folders
        all_numbers = set()
        for folder, numbers in image_numbers.items():
            all_numbers.update(numbers)

        # Get existing postcards
        existing = set(Postcard.objects.values_list('number', flat=True))

        # Find numbers that need creation
        to_create = all_numbers - existing

        self.stdout.write(f'   Found {len(to_create)} images without database entries')

        created = 0
        for number in sorted(to_create):
            if dry_run:
                self.stdout.write(f'   Would create: {number}')
            else:
                Postcard.objects.create(
                    number=number,
                    title=f'Carte postale {number}',
                    description='',
                    keywords='',
                    rarity='common'
                )
                created += 1

        if not dry_run:
            self.stdout.write(f'   ✅ Created {created} postcards')

    def show_summary(self):
        """Show final summary."""
        self.stdout.write('\n' + '=' * 70)
        self.stdout.write('SUMMARY')
        self.stdout.write('=' * 70)

        total_postcards = Postcard.objects.count()

        # Count postcards with images
        postcards_with_images = 0
        postcards_with_animations = 0

        for postcard in Postcard.objects.all()[:1000]:  # Limit for performance
            if postcard.has_vignette():
                postcards_with_images += 1
            if postcard.has_animation():
                postcards_with_animations += 1

        self.stdout.write(f'\n📊 Database Statistics:')
        self.stdout.write(f'   Total postcards in DB: {total_postcards}')
        self.stdout.write(f'   Postcards with images (sampled): {postcards_with_images}')
        self.stdout.write(f'   Postcards with animations (sampled): {postcards_with_animations}')
        self.stdout.write('')
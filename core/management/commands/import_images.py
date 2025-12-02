# core/management/commands/import_images.py
from django.core.management.base import BaseCommand
from core.models import Postcard
import requests


class Command(BaseCommand):
    help = 'Set image URLs for postcards based on OVH hosting structure'

    def add_arguments(self, parser):
        parser.add_argument(
            '--test',
            action='store_true',
            help='Test with 10 postcards only'
        )
        parser.add_argument(
            '--verify',
            action='store_true',
            help='Verify URLs are accessible (slower)'
        )
        parser.add_argument(
            '--base-url',
            type=str,
            default='https://collections.samathey.fr',
            help='Base URL for images'
        )
        parser.add_argument(
            '--path',
            type=str,
            default='collection_cp/cartes',
            help='Path to images on server'
        )
        parser.add_argument(
            '--digits',
            type=int,
            default=6,
            help='Number of digits for image filename (e.g., 6 = 000001.jpg)'
        )

    def handle(self, *args, **options):
        test_mode = options['test']
        verify = options['verify']
        base_url = options['base_url'].rstrip('/')
        path = options['path'].strip('/')
        digits = options['digits']

        self.stdout.write(f'📌 Configuration:')
        self.stdout.write(f'   Base URL: {base_url}')
        self.stdout.write(f'   Path: {path}')
        self.stdout.write(f'   Digits: {digits}')

        # Image type to folder mapping
        image_folders = {
            'vignette': 'Vignette',
            'grande': 'Grande',
            'dos': 'Dos',
            'zoom': 'Zoom',
        }

        # Get postcards
        postcards = Postcard.objects.all().order_by('number')
        total = postcards.count()

        if test_mode:
            postcards = postcards[:10]
            self.stdout.write(f'🧪 Test mode: processing 10 of {total} postcards')
        else:
            self.stdout.write(f'📦 Processing {total} postcards')

        updated = 0
        verified = 0
        errors = 0

        for postcard in postcards:
            try:
                # Format the number with leading zeros
                # Try to extract just the numeric part
                num_str = ''.join(filter(str.isdigit, str(postcard.number)))
                if not num_str:
                    self.stdout.write(f'⚠️  Skipping {postcard.number}: no numeric part')
                    continue

                num_padded = num_str.zfill(digits)

                # Build URLs for each image type
                postcard.vignette_url = f"{base_url}/{path}/{image_folders['vignette']}/{num_padded}.jpg"
                postcard.grande_url = f"{base_url}/{path}/{image_folders['grande']}/{num_padded}.jpg"
                postcard.dos_url = f"{base_url}/{path}/{image_folders['dos']}/{num_padded}.jpg"
                postcard.zoom_url = f"{base_url}/{path}/{image_folders['zoom']}/{num_padded}.jpg"

                # Optionally verify URLs
                if verify:
                    try:
                        response = requests.head(postcard.vignette_url, timeout=5, allow_redirects=True)
                        if response.status_code == 200:
                            verified += 1
                        else:
                            self.stdout.write(f'⚠️  {num_padded}: Vignette not found (HTTP {response.status_code})')
                    except requests.RequestException as e:
                        self.stdout.write(f'⚠️  {num_padded}: Could not verify ({e})')

                postcard.save()
                updated += 1

                if updated % 100 == 0:
                    self.stdout.write(f'   ✅ {updated} updated...')

            except Exception as e:
                errors += 1
                self.stdout.write(self.style.ERROR(f'❌ {postcard.number}: {e}'))

        # Summary
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 50))
        self.stdout.write(self.style.SUCCESS('📊 IMPORT SUMMARY'))
        self.stdout.write(self.style.SUCCESS('=' * 50))
        self.stdout.write(f'Total processed: {updated}')
        self.stdout.write(f'Errors: {errors}')

        if verify:
            self.stdout.write(f'Verified accessible: {verified}')

        # Show sample URLs
        sample = Postcard.objects.exclude(vignette_url='').first()
        if sample:
            self.stdout.write('')
            self.stdout.write(f'📌 Sample URLs for postcard #{sample.number}:')
            self.stdout.write(f'   Vignette: {sample.vignette_url}')
            self.stdout.write(f'   Grande:   {sample.grande_url}')
            self.stdout.write(f'   Dos:      {sample.dos_url}')
            self.stdout.write(f'   Zoom:     {sample.zoom_url}')

        # Database stats
        self.stdout.write('')
        self.stdout.write('📊 Database Statistics:')
        total_db = Postcard.objects.count()
        with_vignette = Postcard.objects.exclude(vignette_url='').exclude(vignette_url__isnull=True).count()
        self.stdout.write(f'   Total postcards: {total_db}')
        self.stdout.write(f'   With URLs set: {with_vignette}')
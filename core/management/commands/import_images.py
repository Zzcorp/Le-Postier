# core/management/commands/import_images.py
from django.core.management.base import BaseCommand
from core.models import Postcard


class Command(BaseCommand):
    help = 'Set image URLs for postcards'

    def add_arguments(self, parser):
        parser.add_argument('--test', action='store_true', help='Test with 10 postcards')
        parser.add_argument(
            '--mode',
            choices=['direct', 'proxy'],
            default='direct',
            help='direct=OVH URLs, proxy=local proxy URLs'
        )
        parser.add_argument(
            '--base-url',
            type=str,
            default='https://collections.samathey.fr',
            help='Base URL for direct mode'
        )
        parser.add_argument(
            '--site-url',
            type=str,
            default='',
            help='Your site URL for proxy mode (e.g., https://le-postier.onrender.com)'
        )
        parser.add_argument('--digits', type=int, default=6, help='Filename digits')
        parser.add_argument('--path', type=str, default='collection_cp/cartes', help='Image path')

    def handle(self, *args, **options):
        mode = options['mode']
        test_mode = options['test']
        digits = options['digits']

        postcards = Postcard.objects.all().order_by('number')

        if test_mode:
            postcards = postcards[:10]

        self.stdout.write(f'📌 Mode: {mode}')
        self.stdout.write(f'📦 Processing {postcards.count()} postcards')

        updated = 0

        for postcard in postcards:
            try:
                num_str = ''.join(filter(str.isdigit, str(postcard.number)))
                if not num_str:
                    continue

                num_padded = num_str.zfill(digits)

                if mode == 'direct':
                    # Direct OVH URLs
                    base = options['base_url'].rstrip('/')
                    path = options['path'].strip('/')

                    postcard.vignette_url = f"{base}/{path}/Vignette/{num_padded}.jpg"
                    postcard.grande_url = f"{base}/{path}/Grande/{num_padded}.jpg"
                    postcard.dos_url = f"{base}/{path}/Dos/{num_padded}.jpg"
                    postcard.zoom_url = f"{base}/{path}/Zoom/{num_padded}.jpg"

                else:
                    # Proxy URLs (through your Django app)
                    site = options['site_url'].rstrip('/')
                    if not site:
                        site = ''  # Will use relative URLs

                    postcard.vignette_url = f"{site}/images/vignette/{num_padded}.jpg"
                    postcard.grande_url = f"{site}/images/grande/{num_padded}.jpg"
                    postcard.dos_url = f"{site}/images/dos/{num_padded}.jpg"
                    postcard.zoom_url = f"{site}/images/zoom/{num_padded}.jpg"

                postcard.save()
                updated += 1

                if updated % 100 == 0:
                    self.stdout.write(f'  ✅ {updated} processed...')

            except Exception as e:
                self.stdout.write(self.style.ERROR(f'❌ {postcard.number}: {e}'))

        self.stdout.write(self.style.SUCCESS(f'\n✅ Updated {updated} postcards'))

        # Show sample
        sample = Postcard.objects.exclude(vignette_url='').first()
        if sample:
            self.stdout.write(f'\n📌 Sample URLs:')
            self.stdout.write(f'   Vignette: {sample.vignette_url}')
            self.stdout.write(f'   Grande: {sample.grande_url}')
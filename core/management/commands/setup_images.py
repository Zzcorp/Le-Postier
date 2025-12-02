# core/management/commands/setup_images.py
from django.core.management.base import BaseCommand
from core.models import Postcard
import urllib.request
import urllib.error


class Command(BaseCommand):
    help = 'Setup and verify postcard image URLs'

    def add_arguments(self, parser):
        parser.add_argument('--test', action='store_true', help='Test with 10 postcards')
        parser.add_argument('--verify', action='store_true', help='Verify URLs exist')
        parser.add_argument('--base-url', type=str, default='https://collections.samathey.fr')
        parser.add_argument('--path', type=str, default='collection_cp/cartes')
        parser.add_argument('--digits', type=int, default=6)
        parser.add_argument('--create-samples', action='store_true', help='Create sample postcards')

    def handle(self, *args, **options):
        # Create sample postcards if none exist
        if options['create_samples'] or Postcard.objects.count() == 0:
            self.create_sample_postcards()

        base_url = options['base_url'].rstrip('/')
        path = options['path'].strip('/')
        digits = options['digits']

        postcards = Postcard.objects.all().order_by('number')

        if options['test']:
            postcards = postcards[:10]

        self.stdout.write(f'\n📌 Configuration:')
        self.stdout.write(f'   Base URL: {base_url}')
        self.stdout.write(f'   Path: {path}')
        self.stdout.write(f'   Digits: {digits}')
        self.stdout.write(f'   Postcards: {postcards.count()}')

        updated = 0
        verified = 0

        for postcard in postcards:
            try:
                # Extract numeric part
                num_str = ''.join(filter(str.isdigit, str(postcard.number)))
                if not num_str:
                    num_str = str(postcard.id)

                num_padded = num_str.zfill(digits)

                # Build URLs
                postcard.vignette_url = f"{base_url}/{path}/Vignette/{num_padded}.jpg"
                postcard.grande_url = f"{base_url}/{path}/Grande/{num_padded}.jpg"
                postcard.dos_url = f"{base_url}/{path}/Dos/{num_padded}.jpg"
                postcard.zoom_url = f"{base_url}/{path}/Zoom/{num_padded}.jpg"

                # Verify if requested
                if options['verify']:
                    if self.verify_url(postcard.vignette_url):
                        verified += 1
                        self.stdout.write(f'  ✅ {num_padded}: OK')
                    else:
                        self.stdout.write(f'  ❌ {num_padded}: Not found')

                postcard.save()
                updated += 1

            except Exception as e:
                self.stdout.write(self.style.ERROR(f'❌ Error: {e}'))

        self.stdout.write(self.style.SUCCESS(f'\n✅ Updated {updated} postcards'))
        if options['verify']:
            self.stdout.write(f'   Verified: {verified}')

        # Show sample
        self.show_sample()

    def verify_url(self, url):
        """Check if URL is accessible"""
        try:
            req = urllib.request.Request(url, method='HEAD')
            req.add_header('User-Agent', 'Mozilla/5.0')
            response = urllib.request.urlopen(req, timeout=5)
            return response.status == 200
        except:
            return False

    def create_sample_postcards(self):
        """Create sample postcards for testing"""
        self.stdout.write('\n📦 Creating sample postcards...')

        samples = [
            {'number': '000001', 'title': 'Bateau sur la Seine - Paris'},
            {'number': '000002', 'title': 'Écluse de Bougival'},
            {'number': '000003', 'title': 'Pont de Neuilly'},
            {'number': '000004', 'title': 'Péniche au fil de l\'eau'},
            {'number': '000005', 'title': 'Les bords de Marne'},
            {'number': '000010', 'title': 'Navigation fluviale'},
            {'number': '000020', 'title': 'Le port de Paris'},
            {'number': '000050', 'title': 'Mariniers au travail'},
            {'number': '000100', 'title': 'Croisière sur la Seine'},
            {'number': '000150', 'title': 'Remorqueur à vapeur'},
        ]

        for data in samples:
            postcard, created = Postcard.objects.get_or_create(
                number=data['number'],
                defaults={
                    'title': data['title'],
                    'keywords': 'seine, bateau, navigation',
                    'rarity': 'common',
                }
            )
            if created:
                self.stdout.write(f'  ✅ Created: {data["number"]}')

    def show_sample(self):
        """Show sample URLs"""
        sample = Postcard.objects.exclude(vignette_url='').first()
        if sample:
            self.stdout.write(f'\n📌 Sample postcard #{sample.number}:')
            self.stdout.write(f'   Title: {sample.title[:50]}')
            self.stdout.write(f'   Vignette: {sample.vignette_url}')
            self.stdout.write(f'\n🌐 Test this URL in your browser!')
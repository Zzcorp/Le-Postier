# core/management/commands/fix_image_urls.py
from django.core.management.base import BaseCommand
from core.models import Postcard


class Command(BaseCommand):
    help = 'Fix all postcard image URLs with correct path'

    def add_arguments(self, parser):
        parser.add_argument('--test', action='store_true', help='Test with 10 postcards')

    def handle(self, *args, **options):
        base_url = 'https://collections.samathey.fr/cartes'
        animated_base = 'https://collections.samathey.fr/cartes/animated_cp'

        postcards = Postcard.objects.all().order_by('number')
        total = postcards.count()

        if options['test']:
            postcards = postcards[:10]
            self.stdout.write(f'🧪 Test mode: 10 of {total} postcards')
        else:
            self.stdout.write(f'📦 Updating {total} postcards')

        updated = 0

        for postcard in postcards:
            try:
                num_str = ''.join(filter(str.isdigit, str(postcard.number)))
                if not num_str:
                    num_str = str(postcard.id)

                num_padded = num_str.zfill(6)

                # Set all URLs
                postcard.vignette_url = f"{base_url}/Vignette/{num_padded}.jpg"
                postcard.grande_url = f"{base_url}/Grande/{num_padded}.jpg"
                postcard.dos_url = f"{base_url}/Dos/{num_padded}.jpg"
                postcard.zoom_url = f"{base_url}/Zoom/{num_padded}.jpg"
                postcard.animated_url = f"{animated_base}/{num_padded}.mp4"

                postcard.save()
                updated += 1

                if updated % 100 == 0:
                    self.stdout.write(f'  ✅ {updated} updated...')

            except Exception as e:
                self.stdout.write(self.style.ERROR(f'❌ {postcard.number}: {e}'))

        self.stdout.write(self.style.SUCCESS(f'\n✅ Updated {updated} postcards'))

        # Show sample
        sample = Postcard.objects.first()
        if sample:
            self.stdout.write(f'\n📌 Sample URLs for #{sample.number}:')
            self.stdout.write(f'   Vignette: {sample.vignette_url}')
            self.stdout.write(f'   Animated: {sample.animated_url}')
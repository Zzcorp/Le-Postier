# core/management/commands/fix_image_urls.py
from django.core.management.base import BaseCommand
from core.models import Postcard
import urllib.request
import urllib.error


class Command(BaseCommand):
    help = 'Fix all postcard image URLs with correct path including multiple animated videos'

    def add_arguments(self, parser):
        parser.add_argument('--test', action='store_true', help='Test with 10 postcards')
        parser.add_argument('--verify-animated', action='store_true', help='Verify animated URLs exist')

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

                # Set image URLs
                postcard.vignette_url = f"{base_url}/Vignette/{num_padded}.jpg"
                postcard.grande_url = f"{base_url}/Grande/{num_padded}.jpg"
                postcard.dos_url = f"{base_url}/Dos/{num_padded}.jpg"
                postcard.zoom_url = f"{base_url}/Zoom/{num_padded}.jpg"

                # Check for multiple animated videos
                animated_urls = []

                # First check for single video (without suffix)
                single_url = f"{animated_base}/{num_padded}.mp4"
                if options['verify_animated']:
                    if self.verify_url(single_url):
                        animated_urls.append(single_url)
                else:
                    animated_urls.append(single_url)

                # Then check for numbered videos (_0, _1, _2, etc.)
                for i in range(10):  # Check up to 10 variations
                    numbered_url = f"{animated_base}/{num_padded}_{i}.mp4"
                    if options['verify_animated']:
                        if self.verify_url(numbered_url):
                            animated_urls.append(numbered_url)
                        else:
                            break  # Stop checking if one doesn't exist
                    else:
                        # Without verification, we'll store the pattern
                        pass

                # Store as comma-separated URLs or JSON-like format
                if animated_urls:
                    postcard.animated_url = ','.join(animated_urls)
                else:
                    # Default pattern that frontend can expand
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

    def verify_url(self, url):
        """Check if URL is accessible"""
        try:
            req = urllib.request.Request(url, method='HEAD')
            req.add_header('User-Agent', 'Mozilla/5.0')
            response = urllib.request.urlopen(req, timeout=5)
            return response.status == 200
        except:
            return False
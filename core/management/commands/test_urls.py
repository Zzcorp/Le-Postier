# core/management/commands/test_urls.py
from django.core.management.base import BaseCommand
import urllib.request
import urllib.error


class Command(BaseCommand):
    help = 'Test different URL patterns to find working image URLs'

    def handle(self, *args, **options):
        # Common URL patterns to test
        test_patterns = [
            # Pattern: domain/path/folder/filename
            ('https://samathey.fr', 'collection_cp/cartes/Vignette', '000001.jpg'),
            ('https://samathey.fr', 'collection_cp/cartes/Vignette', '1.jpg'),
            ('https://samathey.fr', 'collection_cp/cartes/Vignette', '0001.jpg'),
            ('https://samathey.fr', 'images/Vignette', '000001.jpg'),
            ('https://samathey.fr', 'cartes/Vignette', '000001.jpg'),
            ('https://samathey.fr', 'cp/Vignette', '000001.jpg'),

            ('https://www.samathey.fr', 'collection_cp/cartes/Vignette', '000001.jpg'),
            ('https://www.samathey.fr', 'images/Vignette', '000001.jpg'),

            ('https://collections.samathey.fr', 'collection_cp/cartes/Vignette', '000001.jpg'),
            ('https://collections.samathey.fr', 'cartes/Vignette', '000001.jpg'),
            ('https://collections.samathey.fr', 'Vignette', '000001.jpg'),

            # Without subfolder
            ('https://samathey.fr', 'Vignette', '000001.jpg'),
            ('https://samathey.fr', 'Grande', '000001.jpg'),
        ]

        self.stdout.write('\n🔍 Testing URL patterns...\n')
        self.stdout.write('=' * 70)

        working_urls = []

        for domain, path, filename in test_patterns:
            url = f'{domain}/{path}/{filename}'
            status = self.check_url(url)

            if status == 200:
                self.stdout.write(self.style.SUCCESS(f'✅ WORKS: {url}'))
                working_urls.append((domain, path))
            elif status == 403:
                self.stdout.write(self.style.WARNING(f'🔒 FORBIDDEN: {url}'))
            elif status == 404:
                self.stdout.write(f'❌ NOT FOUND: {url}')
            else:
                self.stdout.write(f'⚠️  STATUS {status}: {url}')

        if working_urls:
            self.stdout.write(f'\n{"=" * 70}')
            self.stdout.write(self.style.SUCCESS('\n✅ WORKING URL PATTERN FOUND!\n'))
            self.stdout.write('=' * 70)

            domain, path = working_urls[0]
            self.stdout.write(f'\nUse this command to set up your images:\n')
            self.stdout.write(self.style.SUCCESS(
                f'\npython manage.py setup_images --base-url={domain} --path={path}\n'
            ))
        else:
            self.stdout.write(self.style.WARNING(
                '\n⚠️  No working URLs found. Run explore_ftp to find the correct path.'
            ))

    def check_url(self, url):
        """Check if URL is accessible"""
        try:
            req = urllib.request.Request(url)
            req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
            response = urllib.request.urlopen(req, timeout=10)
            return response.status
        except urllib.error.HTTPError as e:
            return e.code
        except urllib.error.URLError as e:
            return 0
        except Exception as e:
            return -1
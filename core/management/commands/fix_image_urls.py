# core/management/commands/fix_image_urls.py
from django.core.management.base import BaseCommand
from core.models import Postcard
import ftplib
from django.conf import settings


class Command(BaseCommand):
    help = 'Fix all postcard image URLs by scanning FTP folder for actual files'

    def add_arguments(self, parser):
        parser.add_argument('--test', action='store_true', help='Test with 10 postcards')
        parser.add_argument('--scan-ftp', action='store_true', help='Scan FTP for actual animated files')
        parser.add_argument('--list-animated', action='store_true', help='List all animated files found on FTP')

    def handle(self, *args, **options):
        base_url = 'https://collections.samathey.fr/cartes'
        animated_base = 'https://collections.samathey.fr/cartes/animated_cp'

        # FTP settings
        ftp_host = getattr(settings, 'FTP_HOST', 'ftp.cluster010.hosting.ovh.net')
        ftp_user = getattr(settings, 'FTP_USER', 'samathey')
        ftp_pass = getattr(settings, 'FTP_PASSWORD', 'qaszSZDE123')
        ftp_animated_path = 'www/collection_cp/cartes/animated_cp'  # Adjust this path!

        animated_files = {}

        # Scan FTP for animated files
        if options['scan_ftp'] or options['list_animated']:
            self.stdout.write('🔌 Connecting to FTP to scan animated files...')
            animated_files = self.scan_ftp_animated_files(
                ftp_host, ftp_user, ftp_pass, ftp_animated_path
            )

            if options['list_animated']:
                self.stdout.write(f'\n📁 Found {len(animated_files)} postcards with animations:\n')
                for number, files in sorted(animated_files.items())[:50]:
                    self.stdout.write(f'  {number}: {len(files)} video(s) - {files}')

                # Stats
                total_videos = sum(len(f) for f in animated_files.values())
                multi_video = sum(1 for f in animated_files.values() if len(f) > 1)
                self.stdout.write(f'\n📊 Stats:')
                self.stdout.write(f'   Total postcards with animation: {len(animated_files)}')
                self.stdout.write(f'   Total video files: {total_videos}')
                self.stdout.write(f'   Postcards with multiple videos: {multi_video}')
                return

        postcards = Postcard.objects.all().order_by('number')
        total = postcards.count()

        if options['test']:
            postcards = postcards[:10]
            self.stdout.write(f'🧪 Test mode: 10 of {total} postcards')
        else:
            self.stdout.write(f'📦 Updating {total} postcards')

        updated = 0
        animated_count = 0

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

                # Set animated URLs from FTP scan results
                if num_padded in animated_files:
                    # Build URLs from actual files found
                    video_urls = [
                        f"{animated_base}/{filename}"
                        for filename in sorted(animated_files[num_padded])
                    ]
                    postcard.animated_url = ','.join(video_urls)
                    animated_count += 1

                    if len(video_urls) > 1:
                        self.stdout.write(
                            f'  🎬 {num_padded}: {len(video_urls)} videos'
                        )
                elif not options['scan_ftp']:
                    # Default pattern when not scanning FTP
                    postcard.animated_url = f"{animated_base}/{num_padded}.mp4"

                postcard.save()
                updated += 1

                if updated % 100 == 0:
                    self.stdout.write(f'  ✅ {updated} updated...')

            except Exception as e:
                self.stdout.write(self.style.ERROR(f'❌ {postcard.number}: {e}'))

        self.stdout.write(self.style.SUCCESS(f'\n✅ Updated {updated} postcards'))
        if options['scan_ftp']:
            self.stdout.write(f'🎬 {animated_count} postcards have animations')

        # Show sample
        sample = Postcard.objects.exclude(animated_url='').first()
        if sample:
            self.stdout.write(f'\n📌 Sample URLs for #{sample.number}:')
            self.stdout.write(f'   Vignette: {sample.vignette_url}')
            self.stdout.write(f'   Animated: {sample.animated_url}')

    def scan_ftp_animated_files(self, host, user, password, path):
        """
        Scan FTP folder for all animated video files.
        Returns dict: { '000001': ['000001_0.mp4', '000001_1.mp4'], ... }
        """
        animated_files = {}

        try:
            self.stdout.write(f'   Host: {host}')
            self.stdout.write(f'   Path: {path}')

            ftp = ftplib.FTP(host, timeout=60)
            ftp.login(user, password)

            # Try to navigate to animated folder
            try:
                ftp.cwd(path)
            except ftplib.error_perm:
                # Try alternative paths
                alt_paths = [
                    'www/cartes/animated_cp',
                    'cartes/animated_cp',
                    'www/collection_cp/animated_cp',
                    'animated_cp',
                ]
                found = False
                for alt_path in alt_paths:
                    try:
                        ftp.cwd('/')
                        ftp.cwd(alt_path)
                        self.stdout.write(f'   ✅ Found at: {alt_path}')
                        found = True
                        break
                    except:
                        continue

                if not found:
                    self.stdout.write(self.style.WARNING(
                        f'   ⚠️ Could not find animated folder. Listing root...'
                    ))
                    self.explore_ftp(ftp)
                    ftp.quit()
                    return animated_files

            # List all files in the animated directory
            files = []
            ftp.retrlines('NLST', files.append)

            self.stdout.write(f'   📂 Found {len(files)} files in animated folder')

            # Filter and organize video files
            for filename in files:
                if not filename.lower().endswith('.mp4'):
                    continue

                # Extract postcard number from filename
                # Formats: 000001.mp4, 000001_0.mp4, 000001_1.mp4, etc.
                base_name = filename.rsplit('.', 1)[0]  # Remove .mp4

                # Check if it has a suffix (_0, _1, etc.)
                if '_' in base_name:
                    parts = base_name.rsplit('_', 1)
                    number = parts[0]
                    # Verify the suffix is a number
                    if parts[1].isdigit():
                        pass  # Valid format like 000001_0
                    else:
                        number = base_name  # Not a valid suffix, use full name
                else:
                    number = base_name

                # Ensure number is 6 digits
                number = number.zfill(6)

                # Add to dict
                if number not in animated_files:
                    animated_files[number] = []
                animated_files[number].append(filename)

            ftp.quit()
            self.stdout.write(self.style.SUCCESS(
                f'   ✅ Found animations for {len(animated_files)} postcards'
            ))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'   ❌ FTP Error: {e}'))
            import traceback
            traceback.print_exc()

        return animated_files

    def explore_ftp(self, ftp, max_depth=3):
        """Explore FTP structure to find animated folder"""
        self.stdout.write('\n   🔍 Exploring FTP structure...')

        def explore(path, depth=0):
            if depth > max_depth:
                return

            try:
                ftp.cwd(path)
                items = []
                ftp.retrlines('LIST', items.append)

                for item in items[:20]:
                    parts = item.split(None, 8)
                    if len(parts) >= 9:
                        perms = parts[0]
                        name = parts[8]

                        if name in ['.', '..']:
                            continue

                        is_dir = perms.startswith('d')
                        indent = '      ' * depth
                        icon = '📁' if is_dir else '📄'

                        # Check for interesting directories
                        if is_dir:
                            interesting = ['animated', 'video', 'mp4', 'cartes', 'collection']
                            if any(i in name.lower() for i in interesting):
                                self.stdout.write(f'{indent}{icon} {name}/ ⭐')
                                explore(f'{path}/{name}', depth + 1)
                            elif depth < 2:
                                self.stdout.write(f'{indent}{icon} {name}/')
                        elif name.endswith('.mp4'):
                            self.stdout.write(f'{indent}{icon} {name}')

            except Exception as e:
                pass

        explore('/')
# core/management/commands/scan_animated_videos.py
from django.core.management.base import BaseCommand
from core.models import Postcard
import ftplib


class Command(BaseCommand):
    help = 'Scan FTP for animated videos and update postcard URLs'

    def add_arguments(self, parser):
        parser.add_argument('--host', type=str, default='ftp.cluster010.hosting.ovh.net')
        parser.add_argument('--user', type=str, default='samathey')
        parser.add_argument('--password', type=str, default='qaszSZDE123')
        parser.add_argument('--path', type=str, default='collection_cp/cartes/animated_cp',
                            help='FTP path to animated videos folder')
        parser.add_argument('--base-url', type=str,
                            default='https://collections.samathey.fr/collection_cp/cartes/animated_cp',
                            help='Base URL for animated videos')
        parser.add_argument('--dry-run', action='store_true',
                            help='Show what would be done without making changes')
        parser.add_argument('--explore', action='store_true',
                            help='Explore FTP to find the correct path')
        parser.add_argument('--test-url', action='store_true',
                            help='Test if URLs are accessible')

    def handle(self, *args, **options):
        ftp_host = options['host']
        ftp_user = options['user']
        ftp_pass = options['password']
        ftp_path = options['path']
        base_url = options['base_url'].rstrip('/')
        dry_run = options['dry_run']

        self.stdout.write('=' * 60)
        self.stdout.write('🎬 ANIMATED VIDEOS SCANNER')
        self.stdout.write('=' * 60)
        self.stdout.write(f'\n📌 Configuration:')
        self.stdout.write(f'   FTP Path: {ftp_path}')
        self.stdout.write(f'   Base URL: {base_url}')

        # Connect to FTP
        self.stdout.write(f'\n🔌 Connecting to {ftp_host}...')

        try:
            ftp = ftplib.FTP(ftp_host, timeout=60)
            ftp.login(ftp_user, ftp_pass)
            self.stdout.write(self.style.SUCCESS('   ✅ Connected!'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'   ❌ Connection failed: {e}'))
            return

        # Explore mode
        if options['explore']:
            self.explore_ftp_structure(ftp)
            ftp.quit()
            return

        # Navigate to animated folder
        self.stdout.write(f'\n📂 Navigating to {ftp_path}...')

        try:
            ftp.cwd(ftp_path)
            self.stdout.write(self.style.SUCCESS('   ✅ Found folder!'))
        except ftplib.error_perm:
            self.stdout.write(self.style.ERROR(f'   ❌ Path not found: {ftp_path}'))
            self.stdout.write('   💡 Run with --explore to find the correct path')
            ftp.quit()
            return

        # Get all files
        self.stdout.write('\n📋 Listing video files...')
        files = []
        ftp.retrlines('NLST', files.append)

        video_files = [f for f in files if f.lower().endswith('.mp4')]
        self.stdout.write(f'   Found {len(video_files)} .mp4 files')

        # Organize by postcard number
        animated_map = {}

        for filename in video_files:
            base_name = filename.rsplit('.', 1)[0]

            # Handle formats: 000001.mp4, 000001_0.mp4, 000001_1.mp4
            if '_' in base_name:
                parts = base_name.rsplit('_', 1)
                if parts[1].isdigit():
                    number = parts[0].zfill(6)
                else:
                    number = base_name.zfill(6)
            else:
                number = base_name.zfill(6)

            if number not in animated_map:
                animated_map[number] = []
            animated_map[number].append(filename)

        # Sort files within each postcard
        for number in animated_map:
            animated_map[number].sort()

        # Stats
        self.stdout.write(f'\n📊 SCAN RESULTS:')
        self.stdout.write(f'   Postcards with animations: {len(animated_map)}')
        self.stdout.write(f'   Total video files: {len(video_files)}')

        multi_count = sum(1 for files in animated_map.values() if len(files) > 1)
        self.stdout.write(f'   Postcards with multiple videos: {multi_count}')

        # Show sample
        self.stdout.write(f'\n📌 Sample files:')
        for number, filenames in list(animated_map.items())[:10]:
            self.stdout.write(f'   {number}: {filenames}')

        # Test URL accessibility
        if options['test_url'] and animated_map:
            self.stdout.write(f'\n🔗 Testing URL accessibility...')
            first_number = list(animated_map.keys())[0]
            first_file = animated_map[first_number][0]
            test_url = f'{base_url}/{first_file}'

            import urllib.request
            try:
                req = urllib.request.Request(test_url, method='HEAD')
                req.add_header('User-Agent', 'Mozilla/5.0')
                response = urllib.request.urlopen(req, timeout=10)
                if response.status == 200:
                    self.stdout.write(self.style.SUCCESS(f'   ✅ URL works: {test_url}'))
                else:
                    self.stdout.write(self.style.WARNING(f'   ⚠️ Status {response.status}: {test_url}'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'   ❌ URL failed: {test_url}'))
                self.stdout.write(self.style.ERROR(f'      Error: {e}'))
                self.stdout.write('\n   💡 Try different base URLs:')
                alt_urls = [
                    'https://collections.samathey.fr/cartes/animated_cp',
                    'https://samathey.fr/collection_cp/cartes/animated_cp',
                    'https://www.samathey.fr/collection_cp/cartes/animated_cp',
                ]
                for alt in alt_urls:
                    self.stdout.write(f'      {alt}/{first_file}')

        if dry_run:
            self.stdout.write(self.style.WARNING('\n🔍 DRY RUN - No changes made'))
            ftp.quit()
            return

        # Update postcards
        self.stdout.write(f'\n🔄 Updating postcards...')

        updated = 0
        created_urls = 0
        not_found = 0

        for number, filenames in animated_map.items():
            postcard = None

            # Try to find postcard with different number formats
            try:
                postcard = Postcard.objects.get(number=number)
            except Postcard.DoesNotExist:
                try:
                    postcard = Postcard.objects.get(number=str(int(number)))
                except (Postcard.DoesNotExist, ValueError):
                    try:
                        postcard = Postcard.objects.get(number=number.lstrip('0') or '0')
                    except Postcard.DoesNotExist:
                        not_found += 1
                        continue

            if postcard:
                # Build comma-separated URLs
                urls = [f'{base_url}/{fn}' for fn in filenames]
                postcard.animated_url = ','.join(urls)
                postcard.save(update_fields=['animated_url'])

                updated += 1
                created_urls += len(urls)

                if len(filenames) > 1:
                    self.stdout.write(f'   ✅ {number}: {len(filenames)} videos')

        ftp.quit()

        self.stdout.write(self.style.SUCCESS(f'\n✅ COMPLETE!'))
        self.stdout.write(f'   Updated {updated} postcards')
        self.stdout.write(f'   Total URLs set: {created_urls}')
        if not_found > 0:
            self.stdout.write(f'   Not found in DB: {not_found}')

        # Verification
        self.stdout.write(f'\n🔍 Verification:')
        sample = Postcard.objects.exclude(animated_url='').exclude(animated_url__isnull=True).first()
        if sample:
            self.stdout.write(f'   Sample postcard #{sample.number}:')
            for url in sample.animated_url.split(','):
                self.stdout.write(f'      {url}')

    def explore_ftp_structure(self, ftp):
        """Explore FTP to find animated videos folder"""
        self.stdout.write('\n🔍 EXPLORING FTP STRUCTURE...')
        self.stdout.write('=' * 60)

        def explore_dir(path, depth=0, max_depth=4):
            if depth > max_depth:
                return []

            found_paths = []
            indent = '   ' * depth

            try:
                ftp.cwd(path)
                items = []
                ftp.retrlines('LIST', items.append)

                mp4_count = 0
                dirs = []

                for item in items:
                    parts = item.split(None, 8)
                    if len(parts) < 9:
                        continue

                    perms = parts[0]
                    name = parts[8]

                    if name in ['.', '..']:
                        continue

                    if perms.startswith('d'):
                        dirs.append(name)
                    elif name.lower().endswith('.mp4'):
                        mp4_count += 1

                if mp4_count > 0:
                    self.stdout.write(
                        f'{indent}📁 {path} '
                        f'[{self.style.SUCCESS(f"{mp4_count} videos")}]'
                    )
                    found_paths.append((path, mp4_count))
                elif depth < 2:
                    self.stdout.write(f'{indent}📁 {path}')

                interesting = ['animated', 'video', 'mp4', 'cartes', 'collection', 'cp', 'www', 'static']

                for dir_name in dirs:
                    if any(i in dir_name.lower() for i in interesting) or depth < 2:
                        sub_path = f'{path}/{dir_name}' if path != '/' else f'/{dir_name}'
                        found_paths.extend(explore_dir(sub_path, depth + 1, max_depth))

            except Exception as e:
                pass

            return found_paths

        found = explore_dir('/')

        if found:
            self.stdout.write('\n' + '=' * 60)
            self.stdout.write('📋 FOLDERS WITH .MP4 FILES:')
            self.stdout.write('=' * 60)

            for path, count in sorted(found, key=lambda x: -x[1]):
                self.stdout.write(f'   {path}: {count} videos')

            best = max(found, key=lambda x: x[1])
            self.stdout.write(f'\n💡 RECOMMENDED:')
            self.stdout.write(f'   FTP Path: {best[0].lstrip("/")}')

            # Suggest possible URLs
            self.stdout.write(f'\n   Possible Base URLs to try:')
            path_part = best[0].lstrip('/').replace('www/', '')
            self.stdout.write(f'      https://collections.samathey.fr/{path_part}')
            self.stdout.write(f'      https://samathey.fr/{path_part}')
        else:
            self.stdout.write(self.style.WARNING('\n⚠️ No .mp4 files found!'))
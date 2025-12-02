from django.core.management.base import BaseCommand
from core.models import Postcard
import ftplib
import re
import time


class Command(BaseCommand):
    help = 'Import postcard image URLs from FTP server'

    def __init__(self):
        super().__init__()
        self.ftp = None
        self.ftp_host = None
        self.ftp_user = None
        self.ftp_pass = None
        self.images_path = 'collection_cp/cartes'

    def add_arguments(self, parser):
        parser.add_argument('--test', action='store_true', help='Test with 10 postcards only')
        parser.add_argument('--list', action='store_true', help='List FTP directories only')
        parser.add_argument('--ftp-host', type=str, default='ftp.cluster010.hosting.ovh.net')
        parser.add_argument('--ftp-user', type=str, help='FTP username')
        parser.add_argument('--ftp-pass', type=str, help='FTP password')
        parser.add_argument('--ftp-dir', type=str, default='collection_cp/cartes', help='FTP directory path')
        parser.add_argument('--base-url', type=str, default='', help='Base URL for images')
        parser.add_argument('--type', type=str, choices=['vignette', 'grande', 'dos', 'zoom', 'all'],
                            default='all', help='Image type to import')

    def connect_ftp(self):
        """Connect to FTP"""
        try:
            if self.ftp:
                try:
                    self.ftp.quit()
                except:
                    pass

            self.stdout.write(f'🔌 Connecting to FTP: {self.ftp_host}...')
            self.ftp = ftplib.FTP(self.ftp_host, timeout=60)
            self.ftp.login(self.ftp_user, self.ftp_pass)
            self.ftp.set_pasv(True)
            self.stdout.write(self.style.SUCCESS('✅ Connected!'))
            return True
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Connection failed: {e}'))
            return False

    def navigate_to_images(self):
        """Navigate to images directory step by step"""
        parts = [p for p in self.images_path.replace('\\', '/').split('/') if p]

        for part in parts:
            try:
                self.ftp.cwd(part)
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  ❌ Cannot enter {part}: {e}'))
                return False

        return True

    def reconnect_and_navigate(self):
        """Reconnect and navigate back to images directory"""
        self.stdout.write('🔄 Reconnecting...')
        if self.connect_ftp():
            return self.navigate_to_images()
        return False

    def ensure_connection(self):
        """Ensure FTP connection is alive and in correct directory"""
        try:
            self.ftp.voidcmd("NOOP")
            return True
        except:
            return self.reconnect_and_navigate()

    def handle(self, *args, **options):
        test_mode = options.get('test', False)
        list_only = options.get('list', False)
        image_type_filter = options.get('type', 'all')

        self.ftp_host = options.get('ftp_host') or 'ftp.cluster010.hosting.ovh.net'
        self.ftp_user = options.get('ftp_user') or input('FTP Username: ').strip()
        self.ftp_pass = options.get('ftp_pass') or input('FTP Password: ').strip()
        self.images_path = options.get('ftp_dir') or 'collection_cp/cartes'

        base_url = options.get('base_url', '').strip()
        if not base_url:
            self.stdout.write('\n📌 Enter your website base URL for images')
            base_url = input('Base URL: ').strip()

        base_url = base_url.rstrip('/')

        if not self.connect_ftp():
            return

        try:
            if list_only:
                self.list_ftp_directories(self.ftp)
                self.ftp.quit()
                return

            # Navigate to images directory
            self.stdout.write(f'\n📂 Navigating to: {self.images_path}')
            if not self.navigate_to_images():
                self.stdout.write(self.style.ERROR('❌ Failed to navigate to images directory'))
                self.ftp.quit()
                return

            self.stdout.write(self.style.SUCCESS(f'✅ Now in: {self.images_path}'))

            # Get subdirectories
            subdirs = self.get_subdirectories()
            self.stdout.write(f'📂 Found subdirectories: {subdirs}')

            # Type mapping
            type_mapping = {
                'vignette': ['Vignette', 'vignette'],
                'grande': ['Grande', 'grande', 'large'],
                'dos': ['Dos', 'dos'],
                'zoom': ['Zoom', 'zoom'],
            }

            if image_type_filter == 'all':
                types_to_import = ['vignette', 'grande', 'dos', 'zoom']
            else:
                types_to_import = [image_type_filter]

            total_updated = 0

            for img_type in types_to_import:
                subdir_name = None
                for possible_name in type_mapping[img_type]:
                    if possible_name in subdirs:
                        subdir_name = possible_name
                        break

                if not subdir_name:
                    self.stdout.write(f'⚠️  No directory found for {img_type}')
                    continue

                self.stdout.write(f'\n📂 Processing {img_type} from {subdir_name}/...')

                updated = self.import_urls_from_subdirectory(
                    subdir_name, img_type, base_url, test_mode
                )
                total_updated += updated

            try:
                self.ftp.quit()
            except:
                pass

            self.stdout.write(self.style.SUCCESS(f'\n✅ Total updated: {total_updated}'))
            self.print_summary()

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error: {e}'))
            import traceback
            traceback.print_exc()

    def get_subdirectories(self):
        """Get list of subdirectories"""
        subdirs = []

        def parse_line(line):
            parts = line.split()
            if len(parts) >= 9 and parts[0].startswith('d'):
                name = ' '.join(parts[8:])
                if name not in ['.', '..']:
                    subdirs.append(name)

        self.ftp.retrlines('LIST', parse_line)
        return subdirs

    def get_files_in_directory(self, subdir_name):
        """Get files in a subdirectory"""
        files = []

        for attempt in range(3):
            try:
                # Make sure we're in the images directory first
                if attempt > 0:
                    if not self.reconnect_and_navigate():
                        continue

                self.ftp.cwd(subdir_name)

                def parse_line(line):
                    parts = line.split()
                    if len(parts) >= 9 and not parts[0].startswith('d'):
                        name = ' '.join(parts[8:])
                        if name.lower().endswith(('.jpg', '.jpeg', '.png', '.gif')):
                            files.append(name)

                self.ftp.retrlines('LIST', parse_line)
                self.ftp.cwd('..')
                return files

            except ftplib.error_temp as e:
                # Timeout error - reconnect
                self.stdout.write(f'  ⚠️  Timeout on attempt {attempt + 1}: {e}')
                time.sleep(2)
            except Exception as e:
                self.stdout.write(f'  ⚠️  Attempt {attempt + 1} failed: {e}')
                time.sleep(2)

        return files

    def import_urls_from_subdirectory(self, subdir_name, image_type, base_url, test_mode):
        """Set image URLs for postcards"""
        updated = 0

        files = self.get_files_in_directory(subdir_name)
        self.stdout.write(f'  Found {len(files)} image files')

        if len(files) == 0:
            return 0

        self.stdout.write(f'  Sample: {files[0]}')

        if test_mode:
            files = files[:10]
            self.stdout.write(f'  🧪 Test mode: processing {len(files)} files')

        # Process in batches
        batch_size = 200
        for i in range(0, len(files), batch_size):
            batch = files[i:i + batch_size]

            for filename in batch:
                try:
                    number = self.extract_number(filename)

                    if not number:
                        continue

                    # Find postcard - try multiple number formats
                    postcard = None
                    num_int = int(number)
                    for num_variant in [number, str(num_int), str(num_int).zfill(4), str(num_int).zfill(6)]:
                        try:
                            postcard = Postcard.objects.get(number=num_variant)
                            break
                        except Postcard.DoesNotExist:
                            continue

                    if not postcard:
                        continue

                    # Build URL: base_url/images_path/subdir/filename
                    image_url = f'{base_url}/{self.images_path}/{subdir_name}/{filename}'

                    # Update the appropriate field
                    if image_type == 'vignette':
                        postcard.vignette_url = image_url
                    elif image_type == 'grande':
                        postcard.grande_url = image_url
                    elif image_type == 'dos':
                        postcard.dos_url = image_url
                    elif image_type == 'zoom':
                        postcard.zoom_url = image_url

                    postcard.save()
                    updated += 1

                    if updated % 100 == 0:
                        self.stdout.write(f'  ✅ {updated} processed...')

                except Exception as e:
                    pass  # Skip errors silently for speed

            # Progress update between batches
            if i + batch_size < len(files):
                self.stdout.write(f'  📦 Batch complete: {min(i + batch_size, len(files))}/{len(files)}')

        self.stdout.write(f'  ✅ Total updated: {updated}')
        return updated

    def extract_number(self, filename):
        """Extract postcard number from filename"""
        base = filename.rsplit('.', 1)[0]

        # Pattern: 000001.jpg or 1.jpg
        match = re.match(r'^(\d+)$', base)
        if match:
            return match.group(1)

        # Pattern: 0001_something.jpg
        match = re.match(r'^(\d+)[_\-]', base)
        if match:
            return match.group(1)

        # Any number in filename
        match = re.search(r'(\d+)', base)
        if match:
            return match.group(1)

        return None

    def list_ftp_directories(self, ftp, depth=0):
        """List FTP directory structure"""
        if depth == 0:
            self.stdout.write('\n📂 FTP Directory Structure:')
            self.stdout.write('=' * 50)

        if depth > 3:
            return

        try:
            items = []
            ftp.retrlines('LIST', lambda x: items.append(x))

            for item in items:
                parts = item.split()
                if len(parts) < 9:
                    continue

                permissions = parts[0]
                name = ' '.join(parts[8:])

                if name in ['.', '..']:
                    continue

                indent = '  ' * depth

                if permissions.startswith('d'):
                    self.stdout.write(f'{indent}📁 {name}/')

                    try:
                        ftp.cwd(name)
                        sub_items = []
                        ftp.retrlines('LIST', lambda x: sub_items.append(x))

                        file_count = sum(
                            1 for si in sub_items if len(si.split()) >= 9 and not si.split()[0].startswith('d'))
                        dir_count = sum(1 for si in sub_items if
                                        len(si.split()) >= 9 and si.split()[0].startswith('d') and si.split()[
                                            -1] not in ['.', '..'])

                        self.stdout.write(f'{indent}   ({file_count} files, {dir_count} subdirs)')

                        if depth < 2 and name.lower() in ['collection_cp', 'www', 'cartes', 'images']:
                            self.list_ftp_directories(ftp, depth + 1)

                        ftp.cwd('..')
                    except:
                        pass
                elif depth == 0:
                    self.stdout.write(f'{indent}📄 {name}')

        except Exception as e:
            self.stdout.write(f'Error: {e}')

    def print_summary(self):
        """Print import summary"""
        total = Postcard.objects.count()
        with_vignette = Postcard.objects.exclude(vignette_url='').exclude(vignette_url__isnull=True).count()
        with_grande = Postcard.objects.exclude(grande_url='').exclude(grande_url__isnull=True).count()
        with_dos = Postcard.objects.exclude(dos_url='').exclude(dos_url__isnull=True).count()
        with_zoom = Postcard.objects.exclude(zoom_url='').exclude(zoom_url__isnull=True).count()

        pct = lambda x: f'{x * 100 // total}%' if total else '0%'

        self.stdout.write(self.style.SUCCESS('\n' + '=' * 50))
        self.stdout.write(self.style.SUCCESS('📊 IMAGE URL SUMMARY'))
        self.stdout.write(self.style.SUCCESS('=' * 50))
        self.stdout.write(f'Total postcards:    {total}')
        self.stdout.write(f'With vignette:      {with_vignette} ({pct(with_vignette)})')
        self.stdout.write(f'With grande:        {with_grande} ({pct(with_grande)})')
        self.stdout.write(f'With dos:           {with_dos} ({pct(with_dos)})')
        self.stdout.write(f'With zoom:          {with_zoom} ({pct(with_zoom)})')
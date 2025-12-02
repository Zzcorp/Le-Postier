from django.core.management.base import BaseCommand
from core.models import Postcard
import ftplib
import re


class Command(BaseCommand):
    help = 'Import postcard image URLs from FTP server'

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

    def handle(self, *args, **options):
        test_mode = options.get('test', False)
        list_only = options.get('list', False)
        image_type_filter = options.get('type', 'all')

        ftp_host = options.get('ftp_host') or 'ftp.cluster010.hosting.ovh.net'
        ftp_user = options.get('ftp_user') or input('FTP Username: ').strip()
        ftp_pass = options.get('ftp_pass') or input('FTP Password: ').strip()
        ftp_dir = options.get('ftp_dir', 'collection_cp/cartes')

        # Get or ask for base URL
        base_url = options.get('base_url', '').strip()
        if not base_url:
            self.stdout.write('\n📌 Enter your website base URL for images')
            self.stdout.write('   Example: https://samatheynb.cluster010.hosting.ovh.net')
            self.stdout.write('   Or: https://www.your-domain.com')
            base_url = input('Base URL: ').strip()

        # Clean base URL
        base_url = base_url.rstrip('/')

        self.stdout.write(f'🔌 Connecting to FTP: {ftp_host}...')

        try:
            ftp = ftplib.FTP(ftp_host)
            ftp.login(ftp_user, ftp_pass)
            ftp.set_pasv(True)

            self.stdout.write(self.style.SUCCESS('✅ Connected!'))

            if list_only:
                self.list_ftp_directories(ftp)
                ftp.quit()
                return

            # Navigate to directory
            if ftp_dir:
                try:
                    ftp.cwd(ftp_dir)
                    self.stdout.write(f'📂 Changed to: {ftp_dir}')
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'❌ Cannot access: {ftp_dir} - {e}'))
                    ftp.quit()
                    return

            # Get subdirectories
            subdirs = self.get_subdirectories(ftp)
            self.stdout.write('\n📂 Subdirectories found:')
            for subdir in subdirs:
                self.stdout.write(f'  - {subdir}')

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
                # Find matching subdirectory
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
                    ftp, subdir_name, img_type, base_url, ftp_dir, test_mode
                )
                total_updated += updated

            ftp.quit()

            self.stdout.write(self.style.SUCCESS(f'\n✅ Total updated: {total_updated}'))
            self.print_summary()

        except ftplib.error_perm as e:
            self.stdout.write(self.style.ERROR(f'❌ FTP Permission Error: {e}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error: {e}'))
            import traceback
            traceback.print_exc()

    def get_subdirectories(self, ftp):
        subdirs = []

        def parse_line(line):
            parts = line.split()
            if len(parts) >= 9 and parts[0].startswith('d'):
                name = ' '.join(parts[8:])
                if name not in ['.', '..']:
                    subdirs.append(name)

        ftp.retrlines('LIST', parse_line)
        return subdirs

    def get_files_in_directory(self, ftp, directory):
        files = []
        current_dir = ftp.pwd()

        try:
            ftp.cwd(directory)

            def parse_line(line):
                parts = line.split()
                if len(parts) >= 9 and not parts[0].startswith('d'):
                    name = ' '.join(parts[8:])
                    if name.lower().endswith(('.jpg', '.jpeg', '.png', '.gif')):
                        files.append(name)

            ftp.retrlines('LIST', parse_line)
            ftp.cwd(current_dir)

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error listing {directory}: {e}'))
            try:
                ftp.cwd(current_dir)
            except:
                pass

        return files

    def import_urls_from_subdirectory(self, ftp, subdir_name, image_type, base_url, ftp_dir, test_mode):
        """Set image URLs for postcards"""
        updated = 0

        files = self.get_files_in_directory(ftp, subdir_name)
        self.stdout.write(f'  Found {len(files)} image files')

        if len(files) == 0:
            return 0

        self.stdout.write(f'  Sample: {files[0]}')

        if test_mode:
            files = files[:10]
            self.stdout.write(f'  🧪 Test mode: processing {len(files)} files')

        for filename in files:
            try:
                number = self.extract_number(filename)

                if not number:
                    continue

                # Find postcard
                postcard = None
                for num_variant in [number, number.lstrip('0').zfill(4), str(int(number))]:
                    try:
                        postcard = Postcard.objects.get(number=num_variant)
                        break
                    except Postcard.DoesNotExist:
                        continue

                if not postcard:
                    continue

                # Build URL
                # URL format: base_url/ftp_dir/subdir/filename
                image_url = f'{base_url}/{ftp_dir}/{subdir_name}/{filename}'

                # Update the appropriate URL field
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
                self.stdout.write(f'  ✅ {postcard.number}')

            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  ❌ Error {filename}: {e}'))

        return updated

    def extract_number(self, filename):
        base = filename.rsplit('.', 1)[0]

        match = re.match(r'^(\d+)$', base)
        if match:
            return match.group(1).zfill(4)

        match = re.match(r'^(\d+)[_\-]', base)
        if match:
            return match.group(1).zfill(4)

        match = re.search(r'[_\-](\d+)$', base)
        if match:
            return match.group(1).zfill(4)

        match = re.search(r'(\d+)', base)
        if match:
            return match.group(1).zfill(4)

        return None

    def list_ftp_directories(self, ftp, depth=0):
        if depth == 0:
            self.stdout.write('\n📂 FTP Directory Structure:')
            self.stdout.write('=' * 50)

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
                            1 for i in sub_items if len(i.split()) >= 9 and not i.split()[0].startswith('d'))
                        self.stdout.write(f'{indent}   ({file_count} files)')
                        ftp.cwd('..')
                    except:
                        pass

        except Exception as e:
            self.stdout.write(f'Error: {e}')

    def print_summary(self):
        total = Postcard.objects.count()
        with_vignette = Postcard.objects.exclude(vignette_url='').count()
        with_grande = Postcard.objects.exclude(grande_url='').count()
        with_dos = Postcard.objects.exclude(dos_url='').count()
        with_zoom = Postcard.objects.exclude(zoom_url='').count()

        pct = lambda x: f'{x * 100 // total}%' if total else '0%'

        self.stdout.write(self.style.SUCCESS('\n' + '=' * 50))
        self.stdout.write(self.style.SUCCESS('📊 IMAGE URL SUMMARY'))
        self.stdout.write(self.style.SUCCESS('=' * 50))
        self.stdout.write(f'Total postcards:    {total}')
        self.stdout.write(f'With vignette:      {with_vignette} ({pct(with_vignette)})')
        self.stdout.write(f'With grande:        {with_grande} ({pct(with_grande)})')
        self.stdout.write(f'With dos:           {with_dos} ({pct(with_dos)})')
        self.stdout.write(f'With zoom:          {with_zoom} ({pct(with_zoom)})')
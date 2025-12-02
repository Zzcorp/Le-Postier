# core/management/commands/explore_ftp.py
from django.core.management.base import BaseCommand
import ftplib


class Command(BaseCommand):
    help = 'Explore FTP server structure to find images'

    def handle(self, *args, **options):
        ftp_host = 'ftp.cluster010.hosting.ovh.net'
        ftp_user = 'samathey'
        ftp_pass = 'qaszSZDE123'

        self.stdout.write(f'🔌 Connecting to {ftp_host}...')

        try:
            ftp = ftplib.FTP(ftp_host, timeout=30)
            ftp.login(ftp_user, ftp_pass)
            self.stdout.write(self.style.SUCCESS('✅ Connected!'))

            # Show root directory
            self.stdout.write('\n📂 ROOT DIRECTORY:')
            self.stdout.write('=' * 50)
            self.list_directory(ftp, depth=0)

            # Try to find common web directories
            common_dirs = ['www', 'public_html', 'htdocs', 'web']

            for dir_name in common_dirs:
                try:
                    ftp.cwd('/')
                    ftp.cwd(dir_name)
                    self.stdout.write(f'\n📂 FOUND: /{dir_name}/')
                    self.stdout.write('=' * 50)
                    self.list_directory(ftp, depth=0, max_depth=2)
                except:
                    pass

            # Look for image directories
            self.stdout.write('\n🔍 Searching for image directories...')
            self.find_image_dirs(ftp)

            ftp.quit()

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error: {e}'))

    def list_directory(self, ftp, depth=0, max_depth=2):
        """List directory contents"""
        if depth > max_depth:
            return

        indent = '  ' * depth

        try:
            items = []
            ftp.retrlines('LIST', lambda x: items.append(x))

            for item in items[:20]:  # Limit output
                parts = item.split()
                if len(parts) < 9:
                    continue

                permissions = parts[0]
                name = ' '.join(parts[8:])

                if name in ['.', '..']:
                    continue

                is_dir = permissions.startswith('d')
                icon = '📁' if is_dir else '📄'

                self.stdout.write(f'{indent}{icon} {name}')

                # Recurse into interesting directories
                if is_dir and depth < max_depth:
                    interesting = ['cartes', 'images', 'postcards', 'collection', 'cp', 'Vignette', 'Grande']
                    if any(i.lower() in name.lower() for i in interesting):
                        try:
                            ftp.cwd(name)
                            self.list_directory(ftp, depth + 1, max_depth)
                            ftp.cwd('..')
                        except:
                            pass

        except Exception as e:
            self.stdout.write(f'{indent}❌ Error: {e}')

    def find_image_dirs(self, ftp):
        """Search for directories containing images"""
        ftp.cwd('/')

        def search_recursive(path, depth=0):
            if depth > 4:
                return []

            results = []

            try:
                ftp.cwd(path)
                items = []
                ftp.retrlines('LIST', lambda x: items.append(x))

                jpg_count = 0
                subdirs = []

                for item in items:
                    parts = item.split()
                    if len(parts) < 9:
                        continue

                    permissions = parts[0]
                    name = ' '.join(parts[8:])

                    if name in ['.', '..']:
                        continue

                    if permissions.startswith('d'):
                        subdirs.append(name)
                    elif name.lower().endswith(('.jpg', '.jpeg', '.png')):
                        jpg_count += 1

                if jpg_count > 0:
                    results.append((path, jpg_count))
                    self.stdout.write(f'  📷 {path}: {jpg_count} images')

                # Check subdirectories
                for subdir in subdirs[:10]:  # Limit
                    sub_path = f"{path}/{subdir}" if path != '/' else f"/{subdir}"
                    results.extend(search_recursive(sub_path, depth + 1))

            except Exception as e:
                pass

            return results

        search_recursive('/')
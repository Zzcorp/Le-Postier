# core/management/commands/explore_ftp.py
from django.core.management.base import BaseCommand
import ftplib


class Command(BaseCommand):
    help = 'Explore FTP server to find correct image paths'

    def handle(self, *args, **options):
        # Your FTP credentials
        FTP_HOST = 'ftp.cluster010.hosting.ovh.net'
        FTP_USER = 'samathey'
        FTP_PASS = 'qaszSZDE123'

        self.stdout.write(f'\n🔌 Connecting to {FTP_HOST}...')

        try:
            ftp = ftplib.FTP(FTP_HOST, timeout=30)
            ftp.login(FTP_USER, FTP_PASS)
            self.stdout.write(self.style.SUCCESS('✅ Connected successfully!\n'))

            # Get current directory
            current = ftp.pwd()
            self.stdout.write(f'📍 Current directory: {current}\n')

            # List root directory
            self.stdout.write('=' * 60)
            self.stdout.write('\n📂 ROOT DIRECTORY CONTENTS:\n')
            self.stdout.write('=' * 60)
            self.list_dir(ftp, '/')

            # Common web directories to check
            web_dirs = ['www', 'public_html', 'htdocs', 'web', 'html']

            for web_dir in web_dirs:
                try:
                    ftp.cwd('/')
                    ftp.cwd(web_dir)
                    self.stdout.write(f'\n{"=" * 60}')
                    self.stdout.write(f'\n📂 FOUND WEB DIRECTORY: /{web_dir}/\n')
                    self.stdout.write('=' * 60)
                    self.explore_recursive(ftp, f'/{web_dir}', depth=0, max_depth=3)
                except ftplib.error_perm:
                    pass

            # Look specifically for image folders
            self.stdout.write(f'\n{"=" * 60}')
            self.stdout.write('\n🔍 SEARCHING FOR IMAGE FOLDERS...\n')
            self.stdout.write('=' * 60)
            self.find_image_folders(ftp)

            ftp.quit()
            self.stdout.write(self.style.SUCCESS('\n✅ Exploration complete!'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error: {e}'))
            import traceback
            traceback.print_exc()

    def list_dir(self, ftp, path):
        """List directory contents"""
        try:
            ftp.cwd(path)
            items = []
            ftp.retrlines('LIST', lambda x: items.append(x))

            for item in items[:30]:  # Limit output
                parts = item.split(None, 8)
                if len(parts) >= 9:
                    perms = parts[0]
                    name = parts[8]
                    if name in ['.', '..']:
                        continue

                    is_dir = perms.startswith('d')
                    icon = '📁' if is_dir else '📄'
                    self.stdout.write(f'  {icon} {name}')

        except Exception as e:
            self.stdout.write(f'  ❌ Error: {e}')

    def explore_recursive(self, ftp, path, depth=0, max_depth=3):
        """Recursively explore directories"""
        if depth > max_depth:
            return

        indent = '  ' * depth

        try:
            ftp.cwd(path)
            items = []
            ftp.retrlines('LIST', lambda x: items.append(x))

            dirs = []
            files = []
            image_count = 0

            for item in items:
                parts = item.split(None, 8)
                if len(parts) >= 9:
                    perms = parts[0]
                    name = parts[8]
                    if name in ['.', '..']:
                        continue

                    if perms.startswith('d'):
                        dirs.append(name)
                    else:
                        files.append(name)
                        if name.lower().endswith(('.jpg', '.jpeg', '.png', '.gif')):
                            image_count += 1

            # Show directories
            for d in dirs[:15]:
                self.stdout.write(f'{indent}📁 {d}/')

                # Explore interesting directories
                interesting = ['carte', 'image', 'photo', 'cp', 'collection',
                               'postcard', 'vignette', 'grande', 'dos', 'zoom',
                               'media', 'upload', 'asset', 'static', 'img']

                if any(i in d.lower() for i in interesting):
                    self.explore_recursive(ftp, f'{path}/{d}', depth + 1, max_depth)

            # Show image count
            if image_count > 0:
                self.stdout.write(f'{indent}  📷 {image_count} images found!')
                # Show sample filenames
                sample_images = [f for f in files if f.lower().endswith(('.jpg', '.jpeg', '.png'))][:3]
                for img in sample_images:
                    self.stdout.write(f'{indent}    → {img}')

        except Exception as e:
            pass

    def find_image_folders(self, ftp):
        """Search for folders containing images"""
        found_paths = []

        def search(path, depth=0):
            if depth > 5:
                return

            try:
                ftp.cwd(path)
                items = []
                ftp.retrlines('LIST', lambda x: items.append(x))

                dirs = []
                image_count = 0
                sample_file = None

                for item in items:
                    parts = item.split(None, 8)
                    if len(parts) >= 9:
                        perms = parts[0]
                        name = parts[8]
                        if name in ['.', '..']:
                            continue

                        if perms.startswith('d'):
                            dirs.append(name)
                        elif name.lower().endswith(('.jpg', '.jpeg', '.png')):
                            image_count += 1
                            if not sample_file:
                                sample_file = name

                if image_count > 0:
                    found_paths.append({
                        'path': path,
                        'count': image_count,
                        'sample': sample_file
                    })
                    self.stdout.write(f'\n✅ Found {image_count} images in: {path}')
                    self.stdout.write(f'   Sample file: {sample_file}')

                # Continue searching in subdirectories
                for d in dirs:
                    if not d.startswith('.'):
                        search(f'{path}/{d}', depth + 1)

            except:
                pass

        search('/')

        if found_paths:
            self.stdout.write(f'\n{"=" * 60}')
            self.stdout.write('\n📋 SUMMARY - IMAGE FOLDERS FOUND:\n')
            self.stdout.write('=' * 60)

            for fp in found_paths:
                self.stdout.write(f'\n  📁 {fp["path"]}')
                self.stdout.write(f'     Images: {fp["count"]}')
                self.stdout.write(f'     Sample: {fp["sample"]}')

            # Suggest URLs
            self.stdout.write(f'\n{"=" * 60}')
            self.stdout.write('\n🌐 TRY THESE URLs IN YOUR BROWSER:\n')
            self.stdout.write('=' * 60)

            # Common domain patterns
            domains = [
                'https://samathey.fr',
                'https://www.samathey.fr',
                'https://collections.samathey.fr',
            ]

            for fp in found_paths[:3]:
                # Remove /www or /public_html from path for URL
                url_path = fp['path']
                for prefix in ['/www', '/public_html', '/htdocs', '/web']:
                    if url_path.startswith(prefix):
                        url_path = url_path[len(prefix):]
                        break

                for domain in domains:
                    test_url = f"{domain}{url_path}/{fp['sample']}"
                    self.stdout.write(f'\n  🔗 {test_url}')
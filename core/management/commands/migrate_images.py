import os
import ftplib
from django.core.management.base import BaseCommand
from django.conf import settings

class Command(BaseCommand):
    help = 'Migrate images from OVH FTP to local MEDIA_ROOT'

    def handle(self, *args, **options):
        # Connect to FTP
        ftp = ftplib.FTP(settings.FTP_HOST)
        ftp.login(settings.FTP_USER, settings.FTP_PASSWORD)
        ftp.cwd(settings.FTP_IMAGE_PATH)  # Navigate to your images dir

        # Ensure MEDIA_ROOT exists
        if not os.path.exists(settings.MEDIA_ROOT):
            os.makedirs(settings.MEDIA_ROOT)

        # Download all files recursively (adjust if subdirs)
        def download_dir(ftp, path):
            files = []
            ftp.retrlines('LIST', files.append)
            for file in files:
                parts = file.split()
                filename = parts[-1]
                if filename in ('.', '..'):
                    continue
                if parts[0].startswith('d'):  # Directory
                    subpath = os.path.join(path, filename)
                    os.makedirs(subpath, exist_ok=True)
                    ftp.cwd(filename)
                    download_dir(ftp, subpath)
                    ftp.cwd('..')
                else:  # File
                    local_path = os.path.join(path, filename)
                    with open(local_path, 'wb') as f:
                        ftp.retrbinary(f'RETR {filename}', f.write)
                    self.stdout.write(self.style.SUCCESS(f'Downloaded {local_path}'))

        download_dir(ftp, settings.MEDIA_ROOT)
        ftp.quit()
        self.stdout.write(self.style.SUCCESS('Migration complete!'))
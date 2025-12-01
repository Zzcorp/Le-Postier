from django.core.management.base import BaseCommand
from django.core.files import File
from django.core.files.temp import NamedTemporaryFile
from core.models import Postcard
import ftplib
import os
from django.conf import settings


class Command(BaseCommand):
    help = 'Import postcard images from OVH FTP server'

    def handle(self, *args, **options):
        ftp = ftplib.FTP(settings.FTP_HOST)
        ftp.login(settings.FTP_USER, settings.FTP_PASSWORD)

        # Navigate to postcards directory
        ftp.cwd(settings.FTP_POSTCARDS_PATH)

        # Get list of files
        files = ftp.nlst()

        for filename in files:
            if filename.endswith(('.jpg', '.jpeg', '.png')):
                # Download file to temp
                temp_file = NamedTemporaryFile(delete=True)
                ftp.retrbinary(f'RETR {filename}', temp_file.write)
                temp_file.seek(0)

                # Extract postcard number (assuming format: NUMBER_Type.jpg)
                parts = filename.rsplit('_', 1)
                if len(parts) == 2:
                    postcard_number = parts[0]
                    image_type = parts[1].rsplit('.', 1)[0].lower()

                    try:
                        postcard = Postcard.objects.get(number=postcard_number)

                        if 'vignette' in image_type:
                            postcard.vignette_image.save(filename, File(temp_file))
                            self.stdout.write(f'Updated vignette image for {postcard_number}')
                        elif 'grande' in image_type:
                            postcard.grande_image.save(filename, File(temp_file))
                            self.stdout.write(f'Updated grande image for {postcard_number}')
                        elif 'dos' in image_type:
                            postcard.dos_image.save(filename, File(temp_file))
                            self.stdout.write(f'Updated dos image for {postcard_number}')
                        elif 'zoom' in image_type:
                            postcard.zoom_image.save(filename, File(temp_file))
                            self.stdout.write(f'Updated zoom image for {postcard_number}')
                        else:
                            self.stdout.write(f'Unknown image type: {image_type}')

                    except Postcard.DoesNotExist:
                        self.stdout.write(f'Postcard {postcard_number} not found')

        ftp.quit()
        self.stdout.write(self.style.SUCCESS('Successfully imported images from FTP'))
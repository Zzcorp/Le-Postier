import os
from urllib.parse import urlparse
from django.core.management.base import BaseCommand
from django.conf import settings
from core.models import Postcard, PostcardVideo

class Command(BaseCommand):
    help = 'Migrate old URLFields to new ImageField/FileField based on local files'

    def handle(self, *args, **options):
        # For each Postcard
        for postcard in Postcard.objects.all():
            updated = False

            # Helper to set new field from old URL or assumed filename
            def migrate_image(field_name, upload_to, old_url):
                if old_url:
                    # Extract filename from old URL (e.g., '001.jpg' from https://.../Vignette/001.jpg)
                    filename = os.path.basename(urlparse(old_url).path)
                else:
                    # Assume filename based on number, tweak if your naming differs (e.g., add .jpg or prefix)
                    filename = f"{postcard.number}.jpg"  # Or .png, whatever your format

                relative_path = os.path.join(upload_to, filename)
                full_path = os.path.join(settings.MEDIA_ROOT, relative_path)

                if os.path.exists(full_path):
                    setattr(postcard, field_name, relative_path)
                    updated = True
                    self.stdout.write(self.style.SUCCESS(f"Set {field_name} for {postcard.number} to {relative_path}"))
                else:
                    self.stdout.write(self.style.WARNING(f"File not found for {postcard.number} at {full_path}"))

            # Migrate images
            migrate_image('vignette_image', 'Vignette', postcard.vignette_url)
            migrate_image('grande_image', 'Grande', postcard.grande_url)
            migrate_image('dos_image', 'Dos', postcard.dos_url)
            migrate_image('zoom_image', 'Zoom', postcard.zoom_url)

            if updated:
                postcard.save()

        # For videos
        for video in PostcardVideo.objects.all():
            if video.video_url:
                filename = os.path.basename(urlparse(video.video_url).path)
            else:
                # Assume naming, e.g., '{postcard.number}_anim.mp4' - tweak this!
                filename = f"{video.postcard.number}_{video.order}.mp4"

            relative_path = os.path.join('animated_cp', filename)
            full_path = os.path.join(settings.MEDIA_ROOT, relative_path)

            if os.path.exists(full_path):
                video.video_file = relative_path
                video.save()
                self.stdout.write(self.style.SUCCESS(f"Set video_file for {video} to {relative_path}"))
            else:
                self.stdout.write(self.style.WARNING(f"Video not found at {full_path}"))

        # Handle legacy animated_url if needed
        for postcard in Postcard.objects.filter(animated_url__isnull=False):
            urls = postcard.get_animated_urls()
            for idx, url in enumerate(urls):
                if not postcard.videos.filter(order=idx).exists():
                    filename = os.path.basename(urlparse(url).path)
                    relative_path = os.path.join('animated_cp', filename)
                    if os.path.exists(os.path.join(settings.MEDIA_ROOT, relative_path)):
                        PostcardVideo.objects.create(
                            postcard=postcard,
                            video_file=relative_path,
                            order=idx
                        )
                        self.stdout.write(self.style.SUCCESS(f"Created PostcardVideo from legacy for {postcard.number}"))

        self.stdout.write(self.style.SUCCESS('Media migration complete!'))
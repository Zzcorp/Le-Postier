# core/management/commands/import_animated_videos.py
from django.core.management.base import BaseCommand
from core.models import Postcard, PostcardVideo
import ftplib


class Command(BaseCommand):
    help = 'Scan FTP for animated videos and create PostcardVideo entries'

    def add_arguments(self, parser):
        parser.add_argument('--host', type=str, default='ftp.cluster010.hosting.ovh.net')
        parser.add_argument('--user', type=str, default='samathey')
        parser.add_argument('--password', type=str, default='qaszSZDE123')
        parser.add_argument('--path', type=str, default='collection_cp/cartes/animated_cp')
        parser.add_argument('--base-url', type=str,
                            default='https://collections.samathey.fr/cartes/animated_cp')
        parser.add_argument('--dry-run', action='store_true')
        parser.add_argument('--explore', action='store_true')
        parser.add_argument('--clear', action='store_true',
                            help='Clear existing video entries before import')

    def handle(self, *args, **options):
        if options['explore']:
            self.explore_ftp(options)
            return

        self.stdout.write('=' * 60)
        self.stdout.write('🎬 IMPORTING ANIMATED VIDEOS')
        self.stdout.write('=' * 60)

        # Connect to FTP
        try:
            ftp = ftplib.FTP(options['host'], timeout=60)
            ftp.login(options['user'], options['password'])
            self.stdout.write(self.style.SUCCESS('✅ Connected to FTP'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ FTP Error: {e}'))
            return

        # Navigate to folder
        try:
            ftp.cwd(options['path'])
        except ftplib.error_perm:
            self.stdout.write(self.style.ERROR(f'❌ Path not found: {options["path"]}'))
            self.stdout.write('Run with --explore to find correct path')
            ftp.quit()
            return

        # Get all video files
        files = []
        ftp.retrlines('NLST', files.append)
        video_files = sorted([f for f in files if f.lower().endswith('.mp4')])

        self.stdout.write(f'📂 Found {len(video_files)} video files')
        ftp.quit()

        # Organize by postcard number
        videos_map = {}
        for filename in video_files:
            base = filename.rsplit('.', 1)[0]

            if '_' in base:
                parts = base.rsplit('_', 1)
                if parts[1].isdigit():
                    number = parts[0].zfill(6)
                    order = int(parts[1])
                else:
                    number = base.zfill(6)
                    order = 0
            else:
                number = base.zfill(6)
                order = 0

            if number not in videos_map:
                videos_map[number] = []
            videos_map[number].append({
                'filename': filename,
                'order': order,
                'url': f"{options['base_url'].rstrip('/')}/{filename}"
            })

        # Sort by order within each postcard
        for number in videos_map:
            videos_map[number].sort(key=lambda x: x['order'])

        # Stats
        total_videos = sum(len(v) for v in videos_map.values())
        multi_video = sum(1 for v in videos_map.values() if len(v) > 1)

        self.stdout.write(f'\n📊 SCAN RESULTS:')
        self.stdout.write(f'   Postcards with videos: {len(videos_map)}')
        self.stdout.write(f'   Total videos: {total_videos}')
        self.stdout.write(f'   Multi-video postcards: {multi_video}')

        # Show samples
        self.stdout.write(f'\n📌 Samples:')
        for number, vids in list(videos_map.items())[:5]:
            self.stdout.write(f'   {number}: {[v["filename"] for v in vids]}')

        if options['dry_run']:
            self.stdout.write(self.style.WARNING('\n🔍 DRY RUN - No changes made'))
            return

        # Clear existing if requested
        if options['clear']:
            deleted = PostcardVideo.objects.all().delete()[0]
            self.stdout.write(f'🗑️ Cleared {deleted} existing video entries')

        # Create PostcardVideo entries
        self.stdout.write(f'\n💾 Creating database entries...')

        created = 0
        skipped = 0
        not_found = 0

        for number, videos in videos_map.items():
            # Find postcard
            postcard = None
            try:
                postcard = Postcard.objects.get(number=number)
            except Postcard.DoesNotExist:
                try:
                    postcard = Postcard.objects.get(number=str(int(number)))
                except (Postcard.DoesNotExist, ValueError):
                    not_found += 1
                    continue

            for video_data in videos:
                obj, was_created = PostcardVideo.objects.get_or_create(
                    postcard=postcard,
                    video_url=video_data['url'],
                    defaults={'order': video_data['order']}
                )
                if was_created:
                    created += 1
                else:
                    skipped += 1

        self.stdout.write(self.style.SUCCESS(f'\n✅ COMPLETE!'))
        self.stdout.write(f'   Created: {created}')
        self.stdout.write(f'   Skipped (existing): {skipped}')
        self.stdout.write(f'   Postcards not found: {not_found}')

        # Verification
        self.stdout.write(f'\n🔍 Verification:')
        sample = Postcard.objects.filter(videos__isnull=False).distinct().first()
        if sample:
            self.stdout.write(f'   Postcard #{sample.number}:')
            for vid in sample.videos.all():
                self.stdout.write(f'      [{vid.order}] {vid.video_url}')

    def explore_ftp(self, options):
        """Explore FTP structure"""
        self.stdout.write('🔍 Exploring FTP...')

        try:
            ftp = ftplib.FTP(options['host'], timeout=60)
            ftp.login(options['user'], options['password'])
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error: {e}'))
            return

        def explore(path, depth=0):
            if depth > 4:
                return []

            found = []
            indent = '  ' * depth

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
                    perms, name = parts[0], parts[8]
                    if name in ['.', '..']:
                        continue
                    if perms.startswith('d'):
                        dirs.append(name)
                    elif name.lower().endswith('.mp4'):
                        mp4_count += 1

                if mp4_count > 0:
                    self.stdout.write(f'{indent}📁 {path} [{mp4_count} videos] ⭐')
                    found.append((path, mp4_count))

                keywords = ['animated', 'video', 'mp4', 'cartes', 'collection', 'www']
                for d in dirs:
                    if any(k in d.lower() for k in keywords) or depth < 2:
                        subpath = f'{path}/{d}' if path != '/' else f'/{d}'
                        found.extend(explore(subpath, depth + 1))

            except:
                pass

            return found

        results = explore('/')
        ftp.quit()

        if results:
            self.stdout.write('\n📋 FOLDERS WITH VIDEOS:')
            for path, count in sorted(results, key=lambda x: -x[1]):
                self.stdout.write(f'   {path}: {count} videos')

            best = max(results, key=lambda x: x[1])
            self.stdout.write(f'\n💡 Use: --path="{best[0].lstrip("/")}"')
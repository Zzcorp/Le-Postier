# core/management/commands/update_animated_urls.py
from django.core.management.base import BaseCommand
from core.models import Postcard
import ftplib


class Command(BaseCommand):
    help = 'Clear all animated URLs and rescan FTP to set correct ones'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true',
                            help='Show what would be done without making changes')
        parser.add_argument('--explore', action='store_true',
                            help='Explore FTP structure to find animated folder')

    def handle(self, *args, **options):
        # Configuration
        FTP_HOST = 'ftp.cluster010.hosting.ovh.net'
        FTP_USER = 'samathey'
        FTP_PASS = 'qaszSZDE123'
        FTP_PATH = 'collection_cp/cartes/animated_cp'  # Path on FTP server
        BASE_URL = 'https://collections.samathey.fr/cartes/animated_cp'

        dry_run = options['dry_run']

        self.stdout.write('=' * 70)
        self.stdout.write('🎬 UPDATE ANIMATED URLS')
        self.stdout.write('=' * 70)

        # Step 1: Clear all existing animated URLs
        if not dry_run:
            self.stdout.write('\n🗑️  Step 1: Clearing all existing animated URLs...')
            cleared = Postcard.objects.exclude(animated_url='').update(animated_url='')
            self.stdout.write(self.style.SUCCESS(f'   ✅ Cleared {cleared} postcards'))
        else:
            count = Postcard.objects.exclude(animated_url='').count()
            self.stdout.write(f'\n🗑️  Step 1: Would clear {count} postcards (dry-run)')

        # Step 2: Connect to FTP
        self.stdout.write(f'\n🔌 Step 2: Connecting to FTP...')
        self.stdout.write(f'   Host: {FTP_HOST}')

        try:
            ftp = ftplib.FTP(FTP_HOST, timeout=60)
            ftp.login(FTP_USER, FTP_PASS)
            self.stdout.write(self.style.SUCCESS('   ✅ Connected!'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'   ❌ Connection failed: {e}'))
            return

        # Explore mode
        if options['explore']:
            self.explore_ftp(ftp)
            ftp.quit()
            return

        # Step 3: Navigate to animated folder
        self.stdout.write(f'\n📂 Step 3: Navigating to animated folder...')
        self.stdout.write(f'   Path: {FTP_PATH}')

        try:
            ftp.cwd(FTP_PATH)
            self.stdout.write(self.style.SUCCESS('   ✅ Found!'))
        except ftplib.error_perm:
            self.stdout.write(self.style.ERROR(f'   ❌ Path not found!'))
            self.stdout.write('   💡 Run with --explore to find correct path')
            ftp.quit()
            return

        # Step 4: List all video files
        self.stdout.write(f'\n📋 Step 4: Scanning video files...')

        files = []
        ftp.retrlines('NLST', files.append)

        # Filter only .mp4 files
        video_files = sorted([f for f in files if f.lower().endswith('.mp4')])
        self.stdout.write(f'   Found {len(video_files)} .mp4 files')

        # Step 5: Group files by postcard number
        self.stdout.write(f'\n🔢 Step 5: Grouping by postcard number...')

        animated_map = {}  # { '000001': ['000001_0.mp4', '000001_1.mp4'], ... }

        for filename in video_files:
            # Remove .mp4 extension
            base_name = filename[:-4]  # e.g., '000001_0' or '000001'

            # Extract postcard number
            if '_' in base_name:
                # Format: 000001_0, 000001_1, etc.
                number = base_name.rsplit('_', 1)[0]
            else:
                # Format: 000001
                number = base_name

            # Ensure 6 digits
            number = number.zfill(6)

            if number not in animated_map:
                animated_map[number] = []
            animated_map[number].append(filename)

        # Sort files within each postcard (000001_0.mp4 before 000001_1.mp4)
        for number in animated_map:
            animated_map[number].sort()

        # Stats
        total_postcards = len(animated_map)
        total_videos = len(video_files)
        single_video = sum(1 for f in animated_map.values() if len(f) == 1)
        multi_video = sum(1 for f in animated_map.values() if len(f) > 1)
        max_videos = max(len(f) for f in animated_map.values()) if animated_map else 0

        self.stdout.write(f'\n📊 STATISTICS:')
        self.stdout.write(f'   Postcards with animations: {total_postcards}')
        self.stdout.write(f'   Total video files: {total_videos}')
        self.stdout.write(f'   With 1 video: {single_video}')
        self.stdout.write(f'   With 2+ videos: {multi_video}')
        self.stdout.write(f'   Max videos per postcard: {max_videos}')

        # Show breakdown by video count
        self.stdout.write(f'\n📈 BREAKDOWN:')
        for count in range(1, max_videos + 1):
            num = sum(1 for f in animated_map.values() if len(f) == count)
            if num > 0:
                self.stdout.write(f'   {count} video(s): {num} postcards')

        # Show sample
        self.stdout.write(f'\n📌 SAMPLE FILES:')
        shown = 0
        for number, filenames in sorted(animated_map.items()):
            if shown >= 15:
                self.stdout.write(f'   ... and {total_postcards - 15} more')
                break
            self.stdout.write(f'   {number}: {filenames}')
            shown += 1

        # Step 6: Update database
        self.stdout.write(f'\n💾 Step 6: Updating database...')

        if dry_run:
            self.stdout.write(self.style.WARNING('   🔍 DRY RUN - No changes made'))
            ftp.quit()
            return

        updated = 0
        not_found = 0
        errors = []

        for number, filenames in animated_map.items():
            try:
                # Try to find postcard by number (with leading zeros)
                postcard = None

                # Try exact match first
                try:
                    postcard = Postcard.objects.get(number=number)
                except Postcard.DoesNotExist:
                    pass

                # Try without leading zeros
                if not postcard:
                    try:
                        postcard = Postcard.objects.get(number=str(int(number)))
                    except (Postcard.DoesNotExist, ValueError):
                        pass

                # Try with different padding
                if not postcard:
                    for padding in [4, 5, 3]:
                        try:
                            postcard = Postcard.objects.get(number=number.lstrip('0').zfill(padding))
                        except Postcard.DoesNotExist:
                            continue
                        break

                if not postcard:
                    not_found += 1
                    if not_found <= 10:
                        errors.append(f'Postcard {number} not found in database')
                    continue

                # Build comma-separated URLs
                urls = [f'{BASE_URL}/{fn}' for fn in filenames]
                postcard.animated_url = ','.join(urls)
                postcard.save(update_fields=['animated_url'])

                updated += 1

                # Show progress for multi-video postcards
                if len(filenames) > 1:
                    self.stdout.write(f'   ✅ {number}: {len(filenames)} videos → {postcard.number}')

            except Exception as e:
                errors.append(f'{number}: {str(e)}')

        ftp.quit()

        # Final report
        self.stdout.write('\n' + '=' * 70)
        self.stdout.write('✅ COMPLETE!')
        self.stdout.write('=' * 70)
        self.stdout.write(f'   Postcards updated: {updated}')
        self.stdout.write(f'   Not found in DB: {not_found}')

        if errors:
            self.stdout.write(f'\n⚠️  ERRORS ({len(errors)}):')
            for err in errors[:10]:
                self.stdout.write(f'   - {err}')
            if len(errors) > 10:
                self.stdout.write(f'   ... and {len(errors) - 10} more')

        # Verification
        self.stdout.write(f'\n🔍 VERIFICATION:')

        # Show some updated postcards
        samples = Postcard.objects.exclude(animated_url='').exclude(animated_url__isnull=True)[:5]
        for sample in samples:
            urls = sample.animated_url.split(',')
            self.stdout.write(f'\n   Postcard #{sample.number}:')
            for url in urls:
                self.stdout.write(f'      {url}')

        # Final count
        animated_count = Postcard.objects.exclude(animated_url='').exclude(animated_url__isnull=True).count()
        self.stdout.write(f'\n📊 Total postcards with animations in DB: {animated_count}')

    def explore_ftp(self, ftp):
        """Explore FTP structure to find animated folder"""
        self.stdout.write('\n🔍 EXPLORING FTP STRUCTURE...')
        self.stdout.write('Looking for folders with .mp4 files...\n')

        found_paths = []

        def explore(path, depth=0):
            if depth > 5:
                return

            try:
                ftp.cwd(path)
                items = []
                ftp.retrlines('LIST', items.append)

                mp4_count = 0
                subdirs = []

                for item in items:
                    parts = item.split(None, 8)
                    if len(parts) < 9:
                        continue

                    perms, name = parts[0], parts[8]

                    if name in ['.', '..']:
                        continue

                    if perms.startswith('d'):
                        subdirs.append(name)
                    elif name.lower().endswith('.mp4'):
                        mp4_count += 1

                if mp4_count > 0:
                    found_paths.append((path, mp4_count))
                    indent = '  ' * depth
                    self.stdout.write(f'{indent}📁 {path} → {self.style.SUCCESS(f"{mp4_count} videos")}')

                # Explore subdirectories
                keywords = ['animated', 'video', 'mp4', 'cartes', 'collection', 'cp', 'www', 'media', 'static']
                for subdir in subdirs:
                    if any(k in subdir.lower() for k in keywords) or depth < 2:
                        new_path = f'{path}/{subdir}' if path != '/' else f'/{subdir}'
                        explore(new_path, depth + 1)

            except Exception:
                pass

        explore('/')

        if found_paths:
            self.stdout.write('\n' + '=' * 70)
            self.stdout.write('📋 FOLDERS WITH .MP4 FILES:')
            self.stdout.write('=' * 70)

            for path, count in sorted(found_paths, key=lambda x: -x[1]):
                self.stdout.write(f'   {path}: {count} videos')

            best = max(found_paths, key=lambda x: x[1])
            self.stdout.write(f'\n💡 RECOMMENDED: Update FTP_PATH in command to:')
            self.stdout.write(self.style.SUCCESS(f'   "{best[0].lstrip("/")}"'))
        else:
            self.stdout.write(self.style.WARNING('\n⚠️ No .mp4 files found on FTP!'))
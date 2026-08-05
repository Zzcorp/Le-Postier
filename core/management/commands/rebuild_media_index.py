# core/management/commands/rebuild_media_index.py
"""
Rebuild the Postcard media cache (vignette/grande/dos/zoom/animation paths,
has_images, has_animation, search_blob, media_synced_at) from the files on
disk — ONE directory listing per folder, then a bulk_update.

This supersedes the old scanning commands (update_flags, update_postcard_flags,
scan_media): run it after any media rsync/upload batch, and nightly if desired.

Usage:
    manage.py rebuild_media_index            # rebuild and save
    manage.py rebuild_media_index --check    # report only, no writes
    manage.py rebuild_media_index --verbose  # per-card change output
"""

from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import Postcard

IMAGE_SUFFIXES = {'.jpg', '.jpeg', '.png', '.gif'}
VIDEO_SUFFIXES = {'.mp4', '.webm'}

MEDIA_FIELDS = [
    'vignette_file', 'grande_file', 'dos_file', 'zoom_file',
    'animation_files', 'has_animation', 'has_images',
    'search_blob', 'media_synced_at',
]


class Command(BaseCommand):
    help = ('Rebuild the per-card media cache (paths + flags + search_blob) '
            'from disk with one directory listing per folder')

    def add_arguments(self, parser):
        parser.add_argument(
            '--check',
            action='store_true',
            help='Report changes and orphan files without writing anything',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show per-card changes',
        )

    # ---- index building -------------------------------------------------

    @staticmethod
    def build_image_index(directory):
        """
        Map padded and unpadded numeric stems -> relative path (exact filename).
        One directory listing, no per-card probing.
        """
        index = {}
        if not directory.exists():
            return index

        for f in sorted(directory.iterdir()):
            if not f.is_file() or f.suffix.lower() not in IMAGE_SUFFIXES:
                continue
            stem = f.stem.strip().lower()
            index.setdefault(stem, f.name)
            try:
                num = int(stem)
            except ValueError:
                continue
            index.setdefault(str(num), f.name)
            index.setdefault(str(num).zfill(6), f.name)

        return index

    @staticmethod
    def build_animation_index(directory):
        """
        Map padded and unpadded numeric stems -> ordered list of filenames.
        Handles both 000123.mp4 and 000123_0.mp4 / 000123_1.mp4 naming.
        """
        by_base = {}
        if not directory.exists():
            return by_base

        for f in sorted(directory.iterdir()):
            if not f.is_file() or f.suffix.lower() not in VIDEO_SUFFIXES:
                continue
            base = f.stem.strip().lower().split('_')[0]
            keys = {base}
            try:
                num = int(base)
                keys.add(str(num))
                keys.add(str(num).zfill(6))
            except ValueError:
                pass
            for key in keys:
                by_base.setdefault(key, [])
                if f.name not in by_base[key]:
                    by_base[key].append(f.name)

        return by_base

    @staticmethod
    def lookup(index, postcard):
        """Try padded then raw number against an index."""
        padded = postcard.get_padded_number().lower()
        raw = str(postcard.number).strip().lower()
        for key in (padded, raw):
            if key in index:
                return index[key]
        return None

    # ---- command --------------------------------------------------------

    def handle(self, *args, **options):
        check_only = options['check']
        verbose = options['verbose']

        media_root = Path(settings.MEDIA_ROOT)
        self.stdout.write(f'Media root: {media_root} (exists: {media_root.exists()})')

        folders = {
            'Vignette': media_root / 'postcards' / 'Vignette',
            'Grande': media_root / 'postcards' / 'Grande',
            'Dos': media_root / 'postcards' / 'Dos',
            'Zoom': media_root / 'postcards' / 'Zoom',
        }
        animated_dir = media_root / 'animated_cp'

        # One listing per folder
        indexes = {name: self.build_image_index(path) for name, path in folders.items()}
        animation_index = self.build_animation_index(animated_dir)

        for name, index in indexes.items():
            self.stdout.write(f'  {name}: {len(index)} index entries')
        self.stdout.write(f'  animated_cp: {len(animation_index)} index entries')
        self.stdout.write('')

        now = timezone.now()
        updates = []
        changed = 0
        with_images = 0
        with_animation = 0
        matched_stems = {name: set() for name in folders}
        matched_animation_files = set()

        for postcard in Postcard.objects.all().iterator(chunk_size=500):
            new_values = {}

            for name, rel_dir in (
                ('Vignette', 'postcards/Vignette'),
                ('Grande', 'postcards/Grande'),
                ('Dos', 'postcards/Dos'),
                ('Zoom', 'postcards/Zoom'),
            ):
                filename = self.lookup(indexes[name], postcard)
                field = {
                    'Vignette': 'vignette_file',
                    'Grande': 'grande_file',
                    'Dos': 'dos_file',
                    'Zoom': 'zoom_file',
                }[name]
                new_values[field] = f'{rel_dir}/{filename}' if filename else ''
                if filename:
                    matched_stems[name].add(Path(filename).stem.strip().lower())

            animation_names = self.lookup(animation_index, postcard) or []
            new_values['animation_files'] = [f'animated_cp/{n}' for n in animation_names]
            matched_animation_files.update(animation_names)

            new_values['has_images'] = bool(
                new_values['vignette_file'] or new_values['grande_file']
            )
            new_values['has_animation'] = bool(new_values['animation_files'])
            new_values['search_blob'] = postcard.build_search_blob()

            if new_values['has_images']:
                with_images += 1
            if new_values['has_animation']:
                with_animation += 1

            dirty = any(
                getattr(postcard, field) != value for field, value in new_values.items()
            )

            if dirty:
                changed += 1
                if verbose:
                    self.stdout.write(
                        f'  ~ {postcard.number}: '
                        f'images={new_values["has_images"]} '
                        f'animation={len(new_values["animation_files"])}'
                    )

            # media_synced_at is always refreshed on a real run
            for field, value in new_values.items():
                setattr(postcard, field, value)
            postcard.media_synced_at = now
            updates.append(postcard)

        total = len(updates)

        if not check_only and updates:
            Postcard.objects.bulk_update(updates, MEDIA_FIELDS, batch_size=500)

        # Orphan report: files on disk that matched no card
        orphans = []
        for name, path in folders.items():
            if not path.exists():
                continue
            for f in sorted(path.iterdir()):
                if not f.is_file() or f.suffix.lower() not in IMAGE_SUFFIXES:
                    continue
                if f.stem.strip().lower() not in matched_stems[name]:
                    orphans.append(f'{name}/{f.name}')
        if animated_dir.exists():
            for f in sorted(animated_dir.iterdir()):
                if not f.is_file() or f.suffix.lower() not in VIDEO_SUFFIXES:
                    continue
                if f.name not in matched_animation_files:
                    orphans.append(f'animated_cp/{f.name}')

        self.stdout.write('')
        self.stdout.write('=' * 60)
        self.stdout.write('REBUILD MEDIA INDEX SUMMARY')
        self.stdout.write('=' * 60)
        self.stdout.write(f'Total postcards:      {total}')
        self.stdout.write(f'Rows with changes:    {changed}')
        self.stdout.write(self.style.SUCCESS(f'With images:          {with_images}'))
        self.stdout.write(self.style.SUCCESS(f'With animation:       {with_animation}'))
        self.stdout.write(f'Orphan media files:   {len(orphans)}')
        if orphans:
            for orphan in orphans[:30]:
                self.stdout.write(f'  - {orphan}')
            if len(orphans) > 30:
                self.stdout.write(f'  ... and {len(orphans) - 30} more')

        if check_only:
            self.stdout.write('')
            self.stdout.write(self.style.WARNING('--check mode: nothing was saved'))
        else:
            self.stdout.write('')
            self.stdout.write(self.style.SUCCESS('Media index saved.'))

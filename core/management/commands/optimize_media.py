# core/management/commands/optimize_media.py
"""
Recompress oversized JPEG scans in MEDIA_ROOT/postcards/{Grande,Zoom,Vignette}.

Per-folder caps on the longest side:
    Grande   1600px
    Zoom     2000px
    Vignette  800px

Each JPEG is re-encoded at quality 82 (progressive, optimize) after an
optional downscale. Before overwriting, the original is copied to a backup
tree that mirrors the postcards/ structure (default:
MEDIA_ROOT.parent / 'media_originaux', override with --backup-dir).

A file is only rewritten when the re-encode succeeded AND the result is at
least 10% smaller than the original. Non-JPEG files (png/gif…) are never
touched — they are logged and skipped. Corrupt files are logged and skipped
too; the command never aborts mid-batch.

Filenames never change, so no rebuild_media_index run is needed afterwards.

Usage:
    manage.py optimize_media                       # optimize all three folders
    manage.py optimize_media --dry-run             # report only, no writes
    manage.py optimize_media --folder Grande       # limit to one folder
    manage.py optimize_media --quality 78          # override JPEG quality
    manage.py optimize_media --backup-dir /mnt/bk  # custom backup tree
"""

import io
import shutil
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

# Longest-side cap per folder
FOLDER_CAPS = {
    'Grande': 1600,
    'Zoom': 2000,
    'Vignette': 800,
}

DEFAULT_QUALITY = 82
MIN_SAVING_RATIO = 0.10  # only rewrite when at least 10% smaller
JPEG_SUFFIXES = {'.jpg', '.jpeg'}


class Command(BaseCommand):
    help = ('Recompress oversized JPEG scans in postcards/{Grande,Zoom,Vignette} '
            '(Grande 1600px, Zoom 2000px, Vignette 800px, quality 82) with a '
            'mirrored backup of every original before overwrite')

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Report per-folder counts and MB saved without writing anything',
        )
        parser.add_argument(
            '--folder',
            choices=sorted(FOLDER_CAPS),
            help='Limit the pass to one folder (Grande, Zoom or Vignette)',
        )
        parser.add_argument(
            '--quality',
            type=int,
            default=DEFAULT_QUALITY,
            help=f'JPEG quality for the re-encode (default {DEFAULT_QUALITY})',
        )
        parser.add_argument(
            '--backup-dir',
            help="Backup tree for originals (default: MEDIA_ROOT.parent / 'media_originaux')",
        )

    def handle(self, *args, **options):
        try:
            from PIL import Image
        except ImportError:
            self.stderr.write(self.style.ERROR(
                'Pillow is not installed — run: pip install Pillow'
            ))
            return

        dry_run = options['dry_run']
        quality = options['quality']
        if not 1 <= quality <= 95:
            raise CommandError('--quality must be between 1 and 95')

        media_root = Path(settings.MEDIA_ROOT)
        if options['backup_dir']:
            backup_root = Path(options['backup_dir'])
        else:
            backup_root = media_root.parent / 'media_originaux'

        folders = [options['folder']] if options['folder'] else sorted(FOLDER_CAPS)

        self.stdout.write(f'Media root:  {media_root} (exists: {media_root.exists()})')
        self.stdout.write(f'Backup tree: {backup_root}')
        self.stdout.write(f'Quality:     {quality} (progressive, optimize)')
        self.stdout.write(f'Folders:     {", ".join(folders)}')
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN — nothing will be written'))
        self.stdout.write('')

        total = {
            'examined': 0, 'optimized': 0, 'skipped': 0, 'errors': 0,
            'non_jpeg': 0, 'bytes_before': 0, 'bytes_after': 0,
        }

        for folder in folders:
            cap = FOLDER_CAPS[folder]
            directory = media_root / 'postcards' / folder
            self.stdout.write(f'--- {folder} (cap {cap}px) ---')
            if not directory.exists():
                self.stdout.write(self.style.WARNING(f'  folder not found: {directory}'))
                continue

            examined = 0
            optimized = 0
            skipped = 0
            errors = 0
            saved_bytes = 0

            for path in sorted(directory.iterdir()):
                if not path.is_file():
                    continue
                suffix = path.suffix.lower()
                if suffix not in JPEG_SUFFIXES:
                    total['non_jpeg'] += 1
                    self.stdout.write(f'  - non-JPEG skipped: {path.name}')
                    continue

                examined += 1
                original_size = path.stat().st_size
                total['bytes_before'] += original_size

                # Re-encode into memory: nothing touches the disk unless the
                # result is worth keeping (and never in --dry-run).
                try:
                    with Image.open(path) as img:
                        if img.format != 'JPEG':
                            # Extension lies (a PNG named .jpg): never touch it
                            total['non_jpeg'] += 1
                            examined -= 1
                            total['bytes_before'] -= original_size
                            self.stdout.write(
                                f'  - non-JPEG content skipped: {path.name} ({img.format})'
                            )
                            continue
                        if img.mode not in ('RGB', 'L'):
                            img = img.convert('RGB')
                        if max(img.size) > cap:
                            img.thumbnail((cap, cap), Image.LANCZOS)
                        buffer = io.BytesIO()
                        img.save(buffer, 'JPEG', quality=quality,
                                 optimize=True, progressive=True)
                except Exception as exc:  # corrupt file, decode error…
                    errors += 1
                    total['bytes_after'] += original_size
                    self.stderr.write(self.style.ERROR(
                        f'  ! cannot process {path.name} — {exc}'
                    ))
                    continue

                new_size = buffer.getbuffer().nbytes
                if new_size > original_size * (1 - MIN_SAVING_RATIO):
                    skipped += 1
                    total['bytes_after'] += original_size
                    continue

                if not dry_run:
                    backup_path = backup_root / 'postcards' / folder / path.name
                    try:
                        backup_path.parent.mkdir(parents=True, exist_ok=True)
                        if not backup_path.exists():
                            shutil.copy2(path, backup_path)
                        path.write_bytes(buffer.getvalue())
                    except Exception as exc:  # backup or write failure
                        errors += 1
                        total['bytes_after'] += original_size
                        self.stderr.write(self.style.ERROR(
                            f'  ! backup/write failed for {path.name} — {exc} '
                            f'(original left untouched)'
                        ))
                        continue

                optimized += 1
                saved_bytes += original_size - new_size
                total['bytes_after'] += new_size

            mb_saved = saved_bytes / (1024 * 1024)
            verb = 'would be optimized' if dry_run else 'optimized'
            self.stdout.write(
                f'  examined {examined}, {verb} {optimized}, '
                f'skipped {skipped} (saving < 10%), errors {errors}, '
                f'saved {mb_saved:.1f} MB'
            )
            self.stdout.write('')

            total['examined'] += examined
            total['optimized'] += optimized
            total['skipped'] += skipped
            total['errors'] += errors

        mb_before = total['bytes_before'] / (1024 * 1024)
        mb_after = total['bytes_after'] / (1024 * 1024)

        self.stdout.write('=' * 60)
        self.stdout.write('OPTIMIZE MEDIA SUMMARY')
        self.stdout.write('=' * 60)
        self.stdout.write(f'Files examined:       {total["examined"]}')
        self.stdout.write(self.style.SUCCESS(f'Files optimized:      {total["optimized"]}'))
        self.stdout.write(f'Skipped (< 10% gain): {total["skipped"]}')
        self.stdout.write(f'Non-JPEG skipped:     {total["non_jpeg"]}')
        if total['errors']:
            self.stdout.write(self.style.ERROR(f'Errors:               {total["errors"]}'))
        else:
            self.stdout.write(f'Errors:               {total["errors"]}')
        self.stdout.write(f'Size before -> after: {mb_before:.1f} MB -> {mb_after:.1f} MB')
        if dry_run:
            self.stdout.write('')
            self.stdout.write(self.style.WARNING('--dry-run: nothing was written'))
        else:
            self.stdout.write(f'Originals backed up under: {backup_root}')
        self.stdout.write('')
        self.stdout.write('Filenames are unchanged — no rebuild_media_index run is needed.')

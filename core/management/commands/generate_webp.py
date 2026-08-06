# core/management/commands/generate_webp.py
"""
Generate WebP derivatives of the postcard vignettes.

For every Postcard whose vignette_file is set and whose vignette_webp is
empty or stale (missing on disk, stem mismatch after a vignette swap, or
source image newer than the derivative), open the vignette with Pillow,
downscale to a 640px max dimension (aspect preserved) and save a WebP to
MEDIA_ROOT/postcards/VignetteWebP/<stem>.webp, then cache the relative
path on the row (bulk_update).

Corrupt or missing source files are logged and skipped — the command
never aborts mid-batch.

Usage:
    manage.py generate_webp                 # generate missing/stale only
    manage.py generate_webp --force         # regenerate everything
    manage.py generate_webp --quality 75    # override WebP quality (default 82)
"""

from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from core.models import Postcard

WEBP_REL_DIR = 'postcards/VignetteWebP'
MAX_DIMENSION = 640
DEFAULT_QUALITY = 82


class Command(BaseCommand):
    help = ('Generate 640px WebP derivatives of postcard vignettes into '
            'MEDIA_ROOT/postcards/VignetteWebP/ and cache the paths')

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Regenerate every WebP even if it already exists and is fresh',
        )
        parser.add_argument(
            '--quality',
            type=int,
            default=DEFAULT_QUALITY,
            help=f'WebP quality (default {DEFAULT_QUALITY})',
        )

    def handle(self, *args, **options):
        try:
            from PIL import Image
        except ImportError:
            self.stderr.write(self.style.ERROR(
                'Pillow is not installed — run: pip install Pillow'
            ))
            return

        force = options['force']
        quality = options['quality']

        media_root = Path(settings.MEDIA_ROOT)
        webp_dir = media_root / 'postcards' / 'VignetteWebP'
        webp_dir.mkdir(parents=True, exist_ok=True)

        self.stdout.write(f'Media root: {media_root} (exists: {media_root.exists()})')
        self.stdout.write(f'WebP dir:   {webp_dir}')
        self.stdout.write(f'Quality:    {quality}   Max dimension: {MAX_DIMENSION}px')
        self.stdout.write('')

        updates = []
        generated = 0
        skipped_fresh = 0
        errors = 0
        missing_sources = 0

        queryset = Postcard.objects.exclude(vignette_file='').only(
            'id', 'number', 'vignette_file', 'vignette_webp'
        )

        for postcard in queryset.iterator(chunk_size=500):
            source = media_root / postcard.vignette_file
            stem = Path(postcard.vignette_file).stem
            rel_path = f'{WEBP_REL_DIR}/{stem}.webp'
            dest = media_root / 'postcards' / 'VignetteWebP' / f'{stem}.webp'

            if not source.exists():
                missing_sources += 1
                self.stderr.write(self.style.WARNING(
                    f'  ! {postcard.number}: vignette missing on disk '
                    f'({postcard.vignette_file}) — skipped'
                ))
                continue

            # Staleness check (unless --force): regenerate when the cached
            # path is empty or points elsewhere, when the derivative file is
            # gone, or when the source is newer than the derivative.
            if not force:
                fresh = (
                    postcard.vignette_webp == rel_path
                    and dest.exists()
                    and dest.stat().st_mtime >= source.stat().st_mtime
                )
                if fresh:
                    skipped_fresh += 1
                    continue

            try:
                with Image.open(source) as img:
                    if img.mode in ('P', 'LA'):
                        img = img.convert('RGBA')
                    elif img.mode not in ('RGB', 'RGBA'):
                        img = img.convert('RGB')
                    img.thumbnail((MAX_DIMENSION, MAX_DIMENSION), Image.LANCZOS)
                    img.save(dest, 'WEBP', quality=quality, method=6)
            except Exception as exc:  # corrupt file, decode error, disk error…
                errors += 1
                self.stderr.write(self.style.ERROR(
                    f'  ! {postcard.number}: cannot convert '
                    f'{postcard.vignette_file} — {exc}'
                ))
                continue

            generated += 1
            if postcard.vignette_webp != rel_path:
                postcard.vignette_webp = rel_path
                updates.append(postcard)

        if updates:
            Postcard.objects.bulk_update(updates, ['vignette_webp'], batch_size=500)

        self.stdout.write('')
        self.stdout.write('=' * 60)
        self.stdout.write('GENERATE WEBP SUMMARY')
        self.stdout.write('=' * 60)
        self.stdout.write(self.style.SUCCESS(f'WebP generated:       {generated}'))
        self.stdout.write(f'Already fresh:        {skipped_fresh}')
        self.stdout.write(f'Rows updated:         {len(updates)}')
        self.stdout.write(f'Missing sources:      {missing_sources}')
        if errors:
            self.stdout.write(self.style.ERROR(f'Conversion errors:    {errors}'))
        else:
            self.stdout.write(f'Conversion errors:    {errors}')

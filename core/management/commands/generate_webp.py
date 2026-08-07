# core/management/commands/generate_webp.py
"""
Generate WebP derivatives of the postcard vignettes AND grandes.

For every Postcard whose vignette_file is set and whose vignette_webp is
empty or stale (missing on disk, stem mismatch after a vignette swap, or
source image newer than the derivative), open the vignette with Pillow,
downscale to a 640px max dimension (aspect preserved) and save a WebP to
MEDIA_ROOT/postcards/VignetteWebP/<stem>.webp, then cache the relative
path on the row (bulk_update).

The same logic runs for grande_file -> grande_webp: a 1600px max
dimension WebP (quality 80) saved to MEDIA_ROOT/postcards/GrandeWebP/
<stem>.webp, with identical staleness and --force behavior.

Corrupt or missing source files are logged and skipped — the command
never aborts mid-batch.

Usage:
    manage.py generate_webp                 # generate missing/stale only
    manage.py generate_webp --force         # regenerate everything
    manage.py generate_webp --quality 75    # override vignette WebP quality (default 82)
"""

from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.models import Q

from core.models import Postcard

WEBP_REL_DIR = 'postcards/VignetteWebP'
MAX_DIMENSION = 640
DEFAULT_QUALITY = 82

GRANDE_WEBP_REL_DIR = 'postcards/GrandeWebP'
GRANDE_MAX_DIMENSION = 1600
GRANDE_QUALITY = 80


class Command(BaseCommand):
    help = ('Generate WebP derivatives of postcard vignettes (640px) and '
            'grandes (1600px) into MEDIA_ROOT/postcards/{VignetteWebP,GrandeWebP}/ '
            'and cache the paths')

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
            help=f'Vignette WebP quality (default {DEFAULT_QUALITY}; '
                 f'grande WebP is fixed at {GRANDE_QUALITY})',
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
        grande_webp_dir = media_root / 'postcards' / 'GrandeWebP'
        grande_webp_dir.mkdir(parents=True, exist_ok=True)

        self.stdout.write(f'Media root: {media_root} (exists: {media_root.exists()})')
        self.stdout.write(f'WebP dir:   {webp_dir}')
        self.stdout.write(f'Quality:    {quality}   Max dimension: {MAX_DIMENSION}px')
        self.stdout.write(f'Grande WebP dir: {grande_webp_dir}')
        self.stdout.write(f'Grande quality:  {GRANDE_QUALITY}   Max dimension: {GRANDE_MAX_DIMENSION}px')
        self.stdout.write('')

        # (source_field, cache_field, rel_dir, dest_dir, max_dim, quality)
        kinds = [
            ('vignette_file', 'vignette_webp', WEBP_REL_DIR, webp_dir,
             MAX_DIMENSION, quality),
            ('grande_file', 'grande_webp', GRANDE_WEBP_REL_DIR, grande_webp_dir,
             GRANDE_MAX_DIMENSION, GRANDE_QUALITY),
        ]

        updates = []
        stats = {
            cache_field: {'generated': 0, 'skipped_fresh': 0, 'errors': 0, 'missing': 0}
            for _, cache_field, _, _, _, _ in kinds
        }

        queryset = Postcard.objects.filter(
            ~Q(vignette_file='') | ~Q(grande_file='')
        ).only(
            'id', 'number', 'vignette_file', 'vignette_webp',
            'grande_file', 'grande_webp',
        )

        for postcard in queryset.iterator(chunk_size=500):
            dirty = False

            for source_field, cache_field, rel_dir, dest_dir, max_dim, kind_quality in kinds:
                source_rel = getattr(postcard, source_field)
                if not source_rel:
                    continue

                counters = stats[cache_field]
                source = media_root / source_rel
                stem = Path(source_rel).stem
                rel_path = f'{rel_dir}/{stem}.webp'
                dest = dest_dir / f'{stem}.webp'

                if not source.exists():
                    counters['missing'] += 1
                    self.stderr.write(self.style.WARNING(
                        f'  ! {postcard.number}: {source_field} missing on disk '
                        f'({source_rel}) — skipped'
                    ))
                    continue

                # Staleness check (unless --force): regenerate when the cached
                # path is empty or points elsewhere, when the derivative file is
                # gone, or when the source is newer than the derivative.
                if not force:
                    fresh = (
                        getattr(postcard, cache_field) == rel_path
                        and dest.exists()
                        and dest.stat().st_mtime >= source.stat().st_mtime
                    )
                    if fresh:
                        counters['skipped_fresh'] += 1
                        continue

                try:
                    with Image.open(source) as img:
                        if img.mode in ('P', 'LA'):
                            img = img.convert('RGBA')
                        elif img.mode not in ('RGB', 'RGBA'):
                            img = img.convert('RGB')
                        img.thumbnail((max_dim, max_dim), Image.LANCZOS)
                        img.save(dest, 'WEBP', quality=kind_quality, method=6)
                except Exception as exc:  # corrupt file, decode error, disk error…
                    counters['errors'] += 1
                    self.stderr.write(self.style.ERROR(
                        f'  ! {postcard.number}: cannot convert '
                        f'{source_rel} — {exc}'
                    ))
                    continue

                counters['generated'] += 1
                if getattr(postcard, cache_field) != rel_path:
                    setattr(postcard, cache_field, rel_path)
                    dirty = True

            if dirty:
                updates.append(postcard)

        if updates:
            Postcard.objects.bulk_update(
                updates, ['vignette_webp', 'grande_webp'], batch_size=500
            )

        vignette = stats['vignette_webp']
        grande = stats['grande_webp']

        self.stdout.write('')
        self.stdout.write('=' * 60)
        self.stdout.write('GENERATE WEBP SUMMARY')
        self.stdout.write('=' * 60)
        self.stdout.write(self.style.SUCCESS(f'WebP generated:       {vignette["generated"]}'))
        self.stdout.write(f'Already fresh:        {vignette["skipped_fresh"]}')
        self.stdout.write(f'Rows updated:         {len(updates)}')
        self.stdout.write(f'Missing sources:      {vignette["missing"]}')
        if vignette['errors']:
            self.stdout.write(self.style.ERROR(f'Conversion errors:    {vignette["errors"]}'))
        else:
            self.stdout.write(f'Conversion errors:    {vignette["errors"]}')
        self.stdout.write(self.style.SUCCESS(f'Grande WebP generated: {grande["generated"]}'))
        self.stdout.write(f'Grande already fresh:  {grande["skipped_fresh"]}')
        self.stdout.write(f'Grande missing sources: {grande["missing"]}')
        if grande['errors']:
            self.stdout.write(self.style.ERROR(f'Grande conversion errors: {grande["errors"]}'))
        else:
            self.stdout.write(f'Grande conversion errors: {grande["errors"]}')

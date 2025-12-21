# core/management/commands/import_csv_update.py
from django.core.management.base import BaseCommand
from django.db import transaction
from core.models import Postcard
import csv
import os
from pathlib import Path


class Command(BaseCommand):
    help = 'Import/Update postcards from CSV file - handles updates and new entries'

    def add_arguments(self, parser):
        parser.add_argument(
            'csv_file',
            type=str,
            help='Path to the CSV file'
        )
        parser.add_argument(
            '--update',
            action='store_true',
            help='Update existing postcards if they exist'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview changes without saving'
        )
        parser.add_argument(
            '--clear-first',
            action='store_true',
            help='Delete all existing postcards before import (use with caution!)'
        )

    def handle(self, *args, **options):
        csv_file = options['csv_file']
        update_existing = options['update']
        dry_run = options['dry_run']
        clear_first = options['clear_first']

        if not os.path.exists(csv_file):
            self.stderr.write(self.style.ERROR(f'File not found: {csv_file}'))
            return

        self.stdout.write(f'Reading CSV file: {csv_file}')

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN - No changes will be saved'))

        # Count before
        count_before = Postcard.objects.count()
        self.stdout.write(f'Current postcards in database: {count_before}')

        # Clear existing if requested
        if clear_first and not dry_run:
            self.stdout.write(self.style.WARNING('Deleting all existing postcards...'))
            Postcard.objects.all().delete()
            self.stdout.write(self.style.WARNING('All existing postcards deleted'))

        created_count = 0
        updated_count = 0
        skipped_count = 0
        error_count = 0
        errors = []

        try:
            # Try different encodings
            rows = None
            detected_encoding = None
            detected_delimiter = None
            fieldnames = None

            for encoding in ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252', 'iso-8859-1']:
                try:
                    with open(csv_file, 'r', encoding=encoding) as f:
                        # Try to detect delimiter
                        sample = f.read(2048)
                        f.seek(0)

                        # Count delimiters in sample
                        semicolons = sample.count(';')
                        commas = sample.count(',')
                        tabs = sample.count('\t')

                        if semicolons > commas and semicolons > tabs:
                            delimiter = ';'
                        elif tabs > commas:
                            delimiter = '\t'
                        else:
                            delimiter = ','

                        reader = csv.DictReader(f, delimiter=delimiter)

                        # Normalize field names
                        if reader.fieldnames:
                            original_fields = reader.fieldnames.copy()
                            reader.fieldnames = [
                                name.strip().lower().replace(' ', '_').replace('-', '_')
                                for name in reader.fieldnames
                            ]
                            fieldnames = reader.fieldnames

                        rows = list(reader)
                        detected_encoding = encoding
                        detected_delimiter = delimiter

                        self.stdout.write(f'Detected encoding: {encoding}')
                        self.stdout.write(f'Detected delimiter: "{delimiter}"')
                        self.stdout.write(f'Original fields: {original_fields}')
                        self.stdout.write(f'Normalized fields: {fieldnames}')
                        self.stdout.write(f'Total rows: {len(rows)}')

                        break

                except UnicodeDecodeError:
                    continue
                except Exception as e:
                    self.stderr.write(f'Error with {encoding}: {e}')
                    continue

            if rows is None:
                self.stderr.write(self.style.ERROR('Could not read CSV file with any encoding'))
                return

            # Show sample row
            if rows:
                self.stdout.write(f'Sample row: {rows[0]}')

            with transaction.atomic():
                for i, row in enumerate(rows, 1):
                    try:
                        # Get postcard number - try multiple field names
                        number = None
                        for field in ['number', 'numero', 'n°', 'no', 'num', 'id', 'numéro', 'n_', 'n']:
                            if field in row and row[field]:
                                number = str(row[field]).strip()
                                break

                        if not number:
                            # Try first field if nothing matched
                            first_value = list(row.values())[0] if row else None
                            if first_value and str(first_value).strip().isdigit():
                                number = str(first_value).strip()

                        if not number:
                            errors.append(f'Row {i}: No number found in {row}')
                            error_count += 1
                            continue

                        # Get title - try multiple field names
                        title = ''
                        for field in ['title', 'titre', 'name', 'nom', 'description', 'desc', 'libelle', 'libellé']:
                            if field in row and row[field]:
                                title = str(row[field]).strip()
                                break

                        if not title:
                            # Try second field as title
                            values = list(row.values())
                            if len(values) > 1 and values[1]:
                                title = str(values[1]).strip()

                        if not title:
                            title = f'Carte postale {number}'

                        # Get other fields
                        description = ''
                        for field in ['description', 'desc', 'details', 'détails', 'detail']:
                            if field in row and row[field]:
                                description = str(row[field]).strip()
                                break

                        keywords = ''
                        for field in ['keywords', 'mots_cles', 'mots_clés', 'tags', 'mot_cle', 'motcles', 'keyword']:
                            if field in row and row[field]:
                                keywords = str(row[field]).strip()
                                break

                        rarity = 'common'
                        for field in ['rarity', 'rarete', 'rareté', 'rare']:
                            if field in row and row[field]:
                                rarity_value = str(row[field]).strip().lower()
                                if rarity_value in ['rare', 'r', '1']:
                                    rarity = 'rare'
                                elif rarity_value in ['very_rare', 'very rare', 'très rare', 'tres rare', 'vr', 'very',
                                                      '2']:
                                    rarity = 'very_rare'
                                break

                        # Check if exists
                        existing = Postcard.objects.filter(number=number).first()

                        if existing:
                            if update_existing:
                                if not dry_run:
                                    existing.title = title
                                    if description:
                                        existing.description = description
                                    if keywords:
                                        existing.keywords = keywords
                                    existing.rarity = rarity
                                    existing.save()
                                updated_count += 1
                            else:
                                skipped_count += 1
                        else:
                            if not dry_run:
                                Postcard.objects.create(
                                    number=number,
                                    title=title,
                                    description=description,
                                    keywords=keywords,
                                    rarity=rarity,
                                    has_images=False  # Will be updated by update_flags
                                )
                            created_count += 1

                        if i % 500 == 0:
                            self.stdout.write(f'Processed {i}/{len(rows)} rows...')

                    except Exception as e:
                        errors.append(f'Row {i}: {str(e)}')
                        error_count += 1

                if dry_run:
                    # Rollback in dry run
                    transaction.set_rollback(True)

        except Exception as e:
            self.stderr.write(self.style.ERROR(f'Error processing CSV: {e}'))
            import traceback
            traceback.print_exc()
            return

        # Report
        self.stdout.write('')
        self.stdout.write('=' * 50)
        self.stdout.write('IMPORT SUMMARY')
        self.stdout.write('=' * 50)
        self.stdout.write(f'Total rows processed: {len(rows)}')
        self.stdout.write(self.style.SUCCESS(f'Created: {created_count}'))
        self.stdout.write(self.style.WARNING(f'Updated: {updated_count}'))
        self.stdout.write(f'Skipped (already exists): {skipped_count}')
        self.stdout.write(self.style.ERROR(f'Errors: {error_count}'))

        if not dry_run:
            count_after = Postcard.objects.count()
            self.stdout.write(f'Total postcards now: {count_after}')

        if errors:
            self.stdout.write('')
            self.stdout.write('First 10 errors:')
            for error in errors[:10]:
                self.stdout.write(f'  - {error}')
            if len(errors) > 10:
                self.stdout.write(f'  ... and {len(errors) - 10} more errors')

        if dry_run:
            self.stdout.write('')
            self.stdout.write(self.style.WARNING('This was a DRY RUN. Run without --dry-run to apply changes.'))
        else:
            self.stdout.write('')
            self.stdout.write(self.style.SUCCESS('Import complete! Now run: python manage.py update_flags'))
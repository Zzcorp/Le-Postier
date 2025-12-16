# core/management/commands/generate_csv_export.py
"""
Generate a clean CSV export of postcards
Run this on your LOCAL machine with the OVH database
"""

import csv
from django.core.management.base import BaseCommand
from core.models import Postcard


class Command(BaseCommand):
    help = 'Generate CSV export of all postcards'

    def add_arguments(self, parser):
        parser.add_argument('--output', type=str, default='postcards_export.csv')

    def handle(self, *args, **options):
        output_file = options['output']

        postcards = Postcard.objects.all().order_by('number')

        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)

            # Header
            writer.writerow([
                'number', 'title', 'description', 'keywords', 'rarity',
                'views_count', 'likes_count', 'zoom_count'
            ])

            # Data
            for p in postcards:
                writer.writerow([
                    p.number,
                    p.title,
                    p.description or '',
                    p.keywords or '',
                    p.rarity,
                    p.views_count,
                    p.likes_count,
                    p.zoom_count,
                ])

        self.stdout.write(self.style.SUCCESS(f"Exported {postcards.count()} postcards to {output_file}"))
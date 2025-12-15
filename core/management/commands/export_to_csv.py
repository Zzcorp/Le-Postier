# core/management/commands/export_to_csv.py
"""
Export postcards to CSV for migration
Run this on your OVH server first
"""

import csv
from django.core.management.base import BaseCommand
from core.models import Postcard


class Command(BaseCommand):
    help = 'Export postcards to CSV'

    def add_arguments(self, parser):
        parser.add_argument('--output', type=str, default='postcards_export.csv')

    def handle(self, *args, **options):
        output_file = options['output']

        postcards = Postcard.objects.all()

        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = [
                'number', 'title', 'description', 'keywords',
                'rarity', 'views_count', 'likes_count'
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            writer.writeheader()
            for postcard in postcards:
                writer.writerow({
                    'number': postcard.number,
                    'title': postcard.title,
                    'description': postcard.description,
                    'keywords': postcard.keywords,
                    'rarity': postcard.rarity,
                    'views_count': postcard.views_count,
                    'likes_count': postcard.likes_count,
                })

        self.stdout.write(self.style.SUCCESS(f'Exported {postcards.count()} postcards to {output_file}'))
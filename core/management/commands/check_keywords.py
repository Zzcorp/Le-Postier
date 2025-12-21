# core/management/commands/check_keywords.py
from django.core.management.base import BaseCommand
from core.models import Postcard


class Command(BaseCommand):
    help = 'Check keywords status in the database'

    def handle(self, *args, **options):
        total = Postcard.objects.count()
        with_keywords = Postcard.objects.exclude(keywords='').exclude(keywords__isnull=True).count()
        without_keywords = total - with_keywords

        self.stdout.write('=' * 50)
        self.stdout.write('KEYWORDS STATUS')
        self.stdout.write('=' * 50)
        self.stdout.write(f'Total postcards: {total}')
        self.stdout.write(f'With keywords: {with_keywords}')
        self.stdout.write(f'Without keywords: {without_keywords}')
        self.stdout.write('')

        if with_keywords > 0:
            self.stdout.write('Sample postcards WITH keywords:')
            self.stdout.write('-' * 40)
            samples = Postcard.objects.exclude(keywords='').exclude(keywords__isnull=True)[:5]
            for p in samples:
                self.stdout.write(f'  {p.number}: {p.title[:40]}...')
                self.stdout.write(f'    Keywords: {p.keywords[:80]}...')
                self.stdout.write('')

        if without_keywords > 0:
            self.stdout.write('Sample postcards WITHOUT keywords:')
            self.stdout.write('-' * 40)
            samples = Postcard.objects.filter(keywords='')[:5]
            for p in samples:
                self.stdout.write(f'  {p.number}: {p.title[:40]}...')
                self.stdout.write(f'    Keywords: "{p.keywords}" (empty)')
                self.stdout.write('')
# core/management/commands/update_image_urls.py
from django.core.management.base import BaseCommand
from core.models import Postcard


class Command(BaseCommand):
    help = 'Update all postcard image URLs to new domain'

    def add_arguments(self, parser):
        parser.add_argument('--old-domain', type=str, default='collections.samathey.fr',
                            help='Old domain to replace')
        parser.add_argument('--new-domain', type=str, required=True,
                            help='New domain to use')
        parser.add_argument('--dry-run', action='store_true',
                            help='Show what would be changed without making changes')

    def handle(self, *args, **options):
        old_domain = options['old_domain']
        new_domain = options['new_domain']
        dry_run = options['dry_run']

        self.stdout.write(f'Replacing {old_domain} with {new_domain}')

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN - No changes will be made'))

        postcards = Postcard.objects.all()
        updated = 0

        for postcard in postcards:
            changed = False

            # Update each URL field
            for field in ['vignette_url', 'grande_url', 'dos_url', 'zoom_url', 'animated_url']:
                value = getattr(postcard, field, '')
                if value and old_domain in value:
                    new_value = value.replace(old_domain, new_domain)
                    if not dry_run:
                        setattr(postcard, field, new_value)
                    changed = True
                    if dry_run:
                        self.stdout.write(f'  {field}: {value} -> {new_value}')

            if changed:
                if not dry_run:
                    postcard.save()
                updated += 1

        self.stdout.write(self.style.SUCCESS(f'Updated {updated} postcards'))
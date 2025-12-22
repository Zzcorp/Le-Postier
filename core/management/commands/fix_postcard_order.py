# core/management/commands/fix_postcard_order.py
from django.core.management.base import BaseCommand
from core.models import Postcard


class Command(BaseCommand):
    help = 'Reorder postcards by number in the database (for consistent ordering)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--update-numbers',
            action='store_true',
            help='Update postcard numbers to be properly padded (e.g., 000001)',
        )

    def handle(self, *args, **options):
        self.stdout.write('Analyzing postcard numbers...')

        postcards = Postcard.objects.all()

        # Create list with extracted numeric values
        postcard_data = []
        for p in postcards:
            # Extract numeric part from number
            num_str = ''.join(filter(str.isdigit, str(p.number)))
            try:
                num_value = int(num_str) if num_str else 0
            except ValueError:
                num_value = 0

            postcard_data.append({
                'id': p.id,
                'number': p.number,
                'numeric_value': num_value,
                'postcard': p
            })

        # Sort by numeric value
        postcard_data.sort(key=lambda x: x['numeric_value'])

        self.stdout.write(f'Found {len(postcard_data)} postcards')

        # Show first 10 and last 10
        self.stdout.write('\nFirst 10 postcards by number:')
        for i, pd in enumerate(postcard_data[:10]):
            self.stdout.write(f"  {i + 1}. Number: '{pd['number']}' (numeric: {pd['numeric_value']})")

        self.stdout.write('\nLast 10 postcards by number:')
        for i, pd in enumerate(postcard_data[-10:]):
            self.stdout.write(
                f"  {len(postcard_data) - 9 + i}. Number: '{pd['number']}' (numeric: {pd['numeric_value']})")

        # Check for issues
        issues = []
        for pd in postcard_data:
            if pd['numeric_value'] == 0:
                issues.append(f"Postcard ID {pd['id']}: number '{pd['number']}' has no numeric value")
            elif len(str(pd['number'])) != 6:
                issues.append(f"Postcard ID {pd['id']}: number '{pd['number']}' is not 6 digits")

        if issues:
            self.stdout.write(self.style.WARNING(f'\nFound {len(issues)} potential issues:'))
            for issue in issues[:20]:
                self.stdout.write(f'  - {issue}')
            if len(issues) > 20:
                self.stdout.write(f'  ... and {len(issues) - 20} more')

        # Optionally update numbers to be properly padded
        if options['update_numbers']:
            self.stdout.write('\nUpdating postcard numbers to be 6-digit padded...')
            updated = 0
            for pd in postcard_data:
                if pd['numeric_value'] > 0:
                    new_number = str(pd['numeric_value']).zfill(6)
                    if pd['postcard'].number != new_number:
                        pd['postcard'].number = new_number
                        pd['postcard'].save(update_fields=['number'])
                        updated += 1

            self.stdout.write(self.style.SUCCESS(f'Updated {updated} postcard numbers'))

        self.stdout.write(self.style.SUCCESS('\nDone!'))
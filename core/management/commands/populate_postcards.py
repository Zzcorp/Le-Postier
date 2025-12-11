# core/management/commands/populate_postcards.py
from django.core.management.base import BaseCommand
from core.models import Postcard
import random


class Command(BaseCommand):
    help = 'Populate postcards with image URLs from external source'

    def add_arguments(self, parser):
        parser.add_argument('--count', type=int, default=1871, help='Number of postcards to create')
        parser.add_argument('--clear', action='store_true', help='Clear existing postcards first')
        parser.add_argument('--update-urls', action='store_true', help='Only update URLs for existing postcards')

    def handle(self, *args, **options):
        base_url = 'https://collections.samathey.fr/cartes'
        animated_base = 'https://collections.samathey.fr/cartes/animated_cp'

        count = options['count']

        if options['clear']:
            self.stdout.write('🗑️  Clearing existing postcards...')
            deleted, _ = Postcard.objects.all().delete()
            self.stdout.write(f'   Deleted {deleted} postcards')

        if options['update_urls']:
            self.stdout.write('🔄 Updating URLs for existing postcards...')
            postcards = Postcard.objects.all()
            updated = 0

            for postcard in postcards:
                num_str = ''.join(filter(str.isdigit, str(postcard.number)))
                if not num_str:
                    continue

                num_padded = num_str.zfill(6)

                postcard.vignette_url = f"{base_url}/Vignette/{num_padded}.jpg"
                postcard.grande_url = f"{base_url}/Grande/{num_padded}.jpg"
                postcard.dos_url = f"{base_url}/Dos/{num_padded}.jpg"
                postcard.zoom_url = f"{base_url}/Zoom/{num_padded}.jpg"

                # Randomly assign animated URLs to some postcards (about 10%)
                if random.random() < 0.1:
                    postcard.animated_url = f"{animated_base}/{num_padded}.mp4"

                postcard.save()
                updated += 1

                if updated % 100 == 0:
                    self.stdout.write(f'   Updated {updated} postcards...')

            self.stdout.write(self.style.SUCCESS(f'✅ Updated {updated} postcards'))
            return

        # Create new postcards
        self.stdout.write(f'📦 Creating {count} postcards...')

        # Sample titles and keywords for realistic data
        title_templates = [
            "Vue de la Seine à {}",
            "Le pont {} sur la Marne",
            "Bateau-mouche près de {}",
            "Les berges de {} en été",
            "Navigation fluviale à {}",
            "Péniche sur le canal de {}",
            "Écluse de {} - Vue générale",
            "Port fluvial de {}",
            "Croisière sur la {} - Souvenir",
            "Les quais de {} au crépuscule",
            "Promenade au bord de la {}",
            "Moulin sur la rivière {}",
            "Barrage de {} - Construction",
            "Remorqueur sur la Seine à {}",
            "Lavoir de {} - Scène de vie",
        ]

        locations = [
            "Paris", "Conflans", "Mantes", "Vernon", "Rouen", "Le Havre",
            "Melun", "Meaux", "Lagny", "Nogent", "Joinville", "Charenton",
            "Alfortville", "Choisy", "Vitry", "Ivry", "Argenteuil", "Bezons",
            "Chatou", "Bougival", "Marly", "Saint-Cloud", "Sèvres", "Issy",
            "Boulogne", "Suresnes", "Courbevoie", "Asnières", "Clichy", "Saint-Denis"
        ]

        keywords_pool = [
            "seine", "marne", "fleuve", "rivière", "bateau", "péniche",
            "navigation", "pont", "écluse", "port", "quai", "berge",
            "croisière", "vapeur", "remorqueur", "lavoir", "moulin",
            "barrage", "canal", "marinier", "batelier", "halage",
            "promenade", "été", "hiver", "belle époque", "1900"
        ]

        rarities = ['common', 'common', 'common', 'common', 'rare', 'very_rare']

        created = 0
        errors = 0

        for i in range(1, count + 1):
            num_padded = str(i).zfill(6)

            # Generate title
            template = random.choice(title_templates)
            location = random.choice(locations)
            title = template.format(location)

            # Generate keywords
            num_keywords = random.randint(3, 8)
            keywords = random.sample(keywords_pool, min(num_keywords, len(keywords_pool)))
            keywords.append(location.lower())

            # Generate rarity
            rarity = random.choice(rarities)

            try:
                postcard, was_created = Postcard.objects.update_or_create(
                    number=num_padded,
                    defaults={
                        'title': title,
                        'description': f"Carte postale ancienne - {title}. Collection de la Belle Époque (1873-1914).",
                        'keywords': ', '.join(keywords),
                        'rarity': rarity,
                        'vignette_url': f"{base_url}/Vignette/{num_padded}.jpg",
                        'grande_url': f"{base_url}/Grande/{num_padded}.jpg",
                        'dos_url': f"{base_url}/Dos/{num_padded}.jpg",
                        'zoom_url': f"{base_url}/Zoom/{num_padded}.jpg",
                        'animated_url': f"{animated_base}/{num_padded}.mp4" if random.random() < 0.1 else '',
                        'views_count': random.randint(0, 500),
                        'likes_count': random.randint(0, 50),
                    }
                )
                created += 1

                if created % 100 == 0:
                    self.stdout.write(f'   Created {created} postcards...')

            except Exception as e:
                errors += 1
                if errors <= 5:
                    self.stdout.write(self.style.ERROR(f'   Error creating #{num_padded}: {e}'))

        self.stdout.write('')
        self.stdout.write('=' * 60)
        self.stdout.write(self.style.SUCCESS(f'✅ Created {created} postcards'))
        if errors:
            self.stdout.write(self.style.WARNING(f'⚠️  {errors} errors occurred'))

        # Summary
        total = Postcard.objects.count()
        with_images = Postcard.objects.exclude(vignette_url='').exclude(vignette_url__isnull=True).count()
        animated = Postcard.objects.exclude(animated_url='').exclude(animated_url__isnull=True).count()

        self.stdout.write('')
        self.stdout.write('📊 DATABASE SUMMARY:')
        self.stdout.write(f'   Total postcards: {total}')
        self.stdout.write(f'   With images: {with_images}')
        self.stdout.write(f'   With animations: {animated}')

        # Show sample
        sample = Postcard.objects.first()
        if sample:
            self.stdout.write('')
            self.stdout.write('📌 SAMPLE POSTCARD:')
            self.stdout.write(f'   Number: {sample.number}')
            self.stdout.write(f'   Title: {sample.title}')
            self.stdout.write(f'   Vignette: {sample.vignette_url}')
# core/management/commands/process_signatures.py
"""Retraite toutes les signatures existantes avec le pipeline transparent.

Même traitement que la vue upload_signature (core/imaging.py) :
PNG RGBA 600px max, fond blanc rendu transparent (encre seule).
Les originaux sont sauvegardés dans MEDIA_ROOT.parent/'signatures_originales'
en conservant l'arborescence des noms (signatures/xxx.jpg).
"""
from io import BytesIO
from pathlib import Path

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand

from core.imaging import process_signature_image
from core.models import CustomUser


class Command(BaseCommand):
    help = "Retraite toutes les signatures utilisateur : PNG transparent (encre seule), 600px max."

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help="Compte et liste les signatures à retraiter sans rien modifier.",
        )

    def handle(self, *args, **options):
        users = (
            CustomUser.objects
            .exclude(signature_image__isnull=True)
            .exclude(signature_image='')
            .order_by('id')
        )

        if options['dry_run']:
            self.stdout.write(f"{users.count()} signature(s) à retraiter :")
            for user in users:
                self.stdout.write(f"  - {user.username}: {user.signature_image.name}")
            return

        backup_root = Path(settings.MEDIA_ROOT).parent / 'signatures_originales'
        processed = 0
        errors = 0

        for user in users:
            field = user.signature_image
            old_name = field.name
            try:
                storage = field.storage
                with storage.open(old_name, 'rb') as src:
                    original_bytes = src.read()

                # Sauvegarde de l'original (arborescence miroir, jamais écrasée)
                backup_path = backup_root / old_name
                backup_path.parent.mkdir(parents=True, exist_ok=True)
                if not backup_path.exists():
                    backup_path.write_bytes(original_bytes)

                png_bytes = process_signature_image(BytesIO(original_bytes))

                # Remplace le fichier stocké ; field.save met à jour le nom
                # (extension .png) via upload_to='signatures/'.
                storage.delete(old_name)
                stem = Path(old_name).stem or 'signature'
                field.save(f'{stem}.png', ContentFile(png_bytes), save=False)
                user.save(update_fields=['signature_image'])

                processed += 1
                self.stdout.write(f"OK  {user.username}: {old_name} -> {user.signature_image.name}")
            except Exception as exc:
                errors += 1
                self.stderr.write(f"ERREUR {user.username} ({old_name}): {exc}")

        self.stdout.write(self.style.SUCCESS(
            f"Terminé : {processed} signature(s) retraitée(s), {errors} erreur(s). "
            f"Originaux : {backup_root}"
        ))

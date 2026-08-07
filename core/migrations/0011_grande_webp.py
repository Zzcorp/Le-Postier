# Hand-written migration: Postcard.grande_webp (chemin relatif, sous MEDIA_ROOT,
# du dérivé WebP 1600px de l'image Grande — peuplé par generate_webp et
# entretenu par rebuild_media_index, exactement comme vignette_webp).
# Matches the definition in core/models.py.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0010_generation_rating'),
    ]

    operations = [
        migrations.AddField(
            model_name='postcard',
            name='grande_webp',
            field=models.CharField(blank=True, default='', max_length=255),
        ),
    ]

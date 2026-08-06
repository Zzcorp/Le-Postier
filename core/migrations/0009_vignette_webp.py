# Hand-written migration: Postcard.vignette_webp (cached WebP derivative path).
# Matches the field definition in core/models.py (Postcard).

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0008_media_cache'),
    ]

    operations = [
        migrations.AddField(
            model_name='postcard',
            name='vignette_webp',
            field=models.CharField(blank=True, default='', max_length=255),
        ),
    ]

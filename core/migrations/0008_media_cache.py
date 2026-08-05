# Hand-written migration: Postcard media cache fields + search_blob.
# Matches the field definitions in core/models.py (Postcard).

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0007_visitorsession_actions_count_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='postcard',
            name='vignette_file',
            field=models.CharField(blank=True, default='', max_length=255),
        ),
        migrations.AddField(
            model_name='postcard',
            name='grande_file',
            field=models.CharField(blank=True, default='', max_length=255),
        ),
        migrations.AddField(
            model_name='postcard',
            name='dos_file',
            field=models.CharField(blank=True, default='', max_length=255),
        ),
        migrations.AddField(
            model_name='postcard',
            name='zoom_file',
            field=models.CharField(blank=True, default='', max_length=255),
        ),
        migrations.AddField(
            model_name='postcard',
            name='animation_files',
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name='postcard',
            name='has_animation',
            field=models.BooleanField(db_index=True, default=False, verbose_name='Animation présente'),
        ),
        migrations.AddField(
            model_name='postcard',
            name='media_synced_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='postcard',
            name='search_blob',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AlterField(
            model_name='postcard',
            name='has_images',
            field=models.BooleanField(db_index=True, default=False, verbose_name='Images présentes'),
        ),
    ]

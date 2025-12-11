# core/migrations/0012_local_image_fields.py
# Generated manually

from django.db import migrations, models
import core.models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0011_remove_postcard_local_dos_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='postcard',
            name='vignette_image',
            field=models.ImageField(blank=True, null=True, upload_to=core.models.postcard_vignette_path, verbose_name='Image Vignette'),
        ),
        migrations.AddField(
            model_name='postcard',
            name='grande_image',
            field=models.ImageField(blank=True, null=True, upload_to=core.models.postcard_grande_path, verbose_name='Image Grande'),
        ),
        migrations.AddField(
            model_name='postcard',
            name='dos_image',
            field=models.ImageField(blank=True, null=True, upload_to=core.models.postcard_dos_path, verbose_name='Image Dos'),
        ),
        migrations.AddField(
            model_name='postcard',
            name='zoom_image',
            field=models.ImageField(blank=True, null=True, upload_to=core.models.postcard_zoom_path, verbose_name='Image Zoom'),
        ),
        migrations.AlterField(
            model_name='postcard',
            name='vignette_url',
            field=models.URLField(blank=True, max_length=500, verbose_name='URL Vignette (legacy)'),
        ),
        migrations.AlterField(
            model_name='postcard',
            name='grande_url',
            field=models.URLField(blank=True, max_length=500, verbose_name='URL Grande (legacy)'),
        ),
        migrations.AlterField(
            model_name='postcard',
            name='dos_url',
            field=models.URLField(blank=True, max_length=500, verbose_name='URL Dos (legacy)'),
        ),
        migrations.AlterField(
            model_name='postcard',
            name='zoom_url',
            field=models.URLField(blank=True, max_length=500, verbose_name='URL Zoom (legacy)'),
        ),
        migrations.AlterField(
            model_name='postcard',
            name='animated_url',
            field=models.TextField(blank=True, max_length=2000, verbose_name='URL Animation(s) (legacy)'),
        ),
    ]
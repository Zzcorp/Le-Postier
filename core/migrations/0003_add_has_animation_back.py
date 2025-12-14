# core/migrations/0003_add_has_animation_back.py
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_remove_postcard_has_animation'),
    ]

    operations = [
        migrations.AddField(
            model_name='postcard',
            name='has_animation',
            field=models.BooleanField(default=False, verbose_name='Animation présente'),
        ),
    ]
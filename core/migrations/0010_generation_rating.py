# Hand-written migration: Postcard.generation_rating (note de qualité 0-5 donnée
# par le propriétaire à l'animation générée) and the AnimationRating model
# (notes publiques 1-5 des membres connectés, une par carte et par membre).
# Matches the definitions in core/models.py.

import django.core.validators
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('core', '0009_vignette_webp'),
    ]

    operations = [
        migrations.AddField(
            model_name='postcard',
            name='generation_rating',
            field=models.PositiveSmallIntegerField(default=0, verbose_name='Note de génération (0-5)'),
        ),
        migrations.CreateModel(
            name='AnimationRating',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('rating', models.PositiveSmallIntegerField(validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(5)], verbose_name='Note (1-5)')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('postcard', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='animation_ratings', to='core.postcard')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': "Note d'animation",
                'verbose_name_plural': "Notes d'animation",
                'unique_together': {('postcard', 'user')},
            },
        ),
    ]

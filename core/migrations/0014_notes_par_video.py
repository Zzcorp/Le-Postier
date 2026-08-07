# Hand-written migration: notes PAR VIDÉO.
#   - AnimationRating.video_index (1-based, ordre de get_animated_urls()) et
#     unicité déplacée sur (postcard, video_index, user). Les notes existantes
#     gardent l'index 1 grâce au défaut.
#   - Postcard.generation_ratings : dictionnaire {"<index>": note 0-5} des notes
#     du créateur. Les notes plates non nulles y sont recopiées en {"1": note}.
# La colonne generation_rating est CONSERVÉE (commodité = note de l'index 1).
# Matches the definitions in core/models.py.

from django.db import migrations, models


def copier_notes_creation(apps, schema_editor):
    """generation_rating (non nul) -> generation_ratings {"1": note}."""
    Postcard = apps.get_model('core', 'Postcard')
    for pk, note in (
        Postcard.objects.exclude(generation_rating=0)
        .values_list('pk', 'generation_rating')
        .iterator()
    ):
        try:
            valeur = int(note or 0)
        except (TypeError, ValueError):
            continue
        if valeur:
            Postcard.objects.filter(pk=pk).update(generation_ratings={'1': valeur})


def restaurer_notes_creation(apps, schema_editor):
    """Retour arrière : l'entrée "1" du dictionnaire redevient la colonne plate."""
    Postcard = apps.get_model('core', 'Postcard')
    for pk, notes in (
        Postcard.objects.values_list('pk', 'generation_ratings').iterator()
    ):
        if not isinstance(notes, dict) or not notes:
            continue
        try:
            valeur = int(notes.get('1', 0) or 0)
        except (TypeError, ValueError):
            valeur = 0
        Postcard.objects.filter(pk=pk).update(
            generation_rating=valeur,
            generation_ratings={},
        )


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0013_handwriting'),
    ]

    operations = [
        migrations.AddField(
            model_name='postcard',
            name='generation_ratings',
            field=models.JSONField(
                blank=True,
                default=dict,
                verbose_name='Notes de génération par vidéo',
            ),
        ),
        migrations.AddField(
            model_name='animationrating',
            name='video_index',
            field=models.PositiveSmallIntegerField(
                default=1,
                verbose_name='Index de la vidéo',
            ),
        ),
        migrations.AlterUniqueTogether(
            name='animationrating',
            unique_together={('postcard', 'video_index', 'user')},
        ),
        migrations.RunPython(copier_notes_creation, restaurer_notes_creation),
    ]

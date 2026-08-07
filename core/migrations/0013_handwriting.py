# Hand-written migration: SentPostcard.handwriting (écriture choisie à la
# composition — anglaise, Parisienne, ronde formelle, plume courante, main
# libre). Les cartes déjà envoyées reprennent l'anglaise (défaut 'dancing').
# Matches the definition in core/models.py.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0012_civilite'),
    ]

    operations = [
        migrations.AddField(
            model_name='sentpostcard',
            name='handwriting',
            field=models.CharField(
                choices=[('dancing', 'Anglaise'), ('parisienne', 'Parisienne'), ('formal', 'Ronde formelle'), ('marck', 'Plume courante'), ('caveat', 'Main libre')],
                default='dancing',
                max_length=24,
                verbose_name='Écriture',
            ),
        ),
    ]

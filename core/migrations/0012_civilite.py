# Hand-written migration: CustomUser.civilite (civilité facultative — M., Mme,
# Dr, Pr, Me — préfixée au nom d'utilisateur via get_display_name() dans les
# affichages La Poste).
# Matches the definition in core/models.py.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0011_grande_webp'),
    ]

    operations = [
        migrations.AddField(
            model_name='customuser',
            name='civilite',
            field=models.CharField(
                blank=True,
                choices=[('', '—'), ('M.', 'M.'), ('Mme', 'Mme'), ('Dr', 'Dr'), ('Pr', 'Pr'), ('Me', 'Me')],
                default='',
                max_length=4,
                verbose_name='Civilité',
            ),
        ),
    ]

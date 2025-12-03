# core/migrations/0004_likes_suggestions_intro.py
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0003_postcard_animated_url'),
    ]

    operations = [
        # Update CustomUser
        migrations.AddField(
            model_name='customuser',
            name='last_intro_seen',
            field=models.DateField(blank=True, null=True, verbose_name='Dernière intro vue'),
        ),

        # Update Postcard
        migrations.AddField(
            model_name='postcard',
            name='likes_count',
            field=models.IntegerField(default=0, verbose_name='Nombre de likes'),
        ),

        # Change animated_url to TextField for multiple URLs
        migrations.AlterField(
            model_name='postcard',
            name='animated_url',
            field=models.TextField(blank=True, max_length=2000, verbose_name='URL Animation(s)'),
        ),

        # Create PostcardLike model
        migrations.CreateModel(
            name='PostcardLike',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('session_key', models.CharField(blank=True, max_length=100)),
                ('ip_address', models.GenericIPAddressField(blank=True, null=True)),
                ('is_animated_like', models.BooleanField(default=False, verbose_name='Like pour animation')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('postcard', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='likes',
                                               to='core.postcard')),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE,
                                           to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Like',
                'verbose_name_plural': 'Likes',
            },
        ),

        # Create AnimationSuggestion model
        migrations.CreateModel(
            name='AnimationSuggestion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('description', models.TextField(verbose_name="Description de l'animation suggérée")),
                ('status', models.CharField(
                    choices=[('pending', 'En attente'), ('reviewed', 'Examiné'), ('approved', 'Approuvé'),
                             ('rejected', 'Rejeté')], default='pending', max_length=20)),
                ('ip_address', models.GenericIPAddressField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('reviewed_at', models.DateTimeField(blank=True, null=True)),
                ('postcard',
                 models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='animation_suggestions',
                                   to='core.postcard')),
                ('reviewed_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                                                  related_name='reviewed_suggestions', to=settings.AUTH_USER_MODEL)),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                                           to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': "Suggestion d'animation",
                'verbose_name_plural': "Suggestions d'animation",
                'ordering': ['-created_at'],
            },
        ),

        # Update IntroSeen model
        migrations.AddField(
            model_name='introseen',
            name='user',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE,
                                    to=settings.AUTH_USER_MODEL),
        ),

        # Add unique constraints
        migrations.AddConstraint(
            model_name='postcardlike',
            constraint=models.UniqueConstraint(fields=['postcard', 'user', 'is_animated_like'],
                                               name='unique_user_like'),
        ),
        migrations.AddConstraint(
            model_name='postcardlike',
            constraint=models.UniqueConstraint(fields=['postcard', 'session_key', 'is_animated_like'],
                                               name='unique_session_like'),
        ),
        migrations.AlterUniqueTogether(
            name='introseen',
            unique_together={('session_key', 'date_seen')},
        ),

        # Update UserActivity choices
        migrations.AlterField(
            model_name='useractivity',
            name='action',
            field=models.CharField(
                choices=[('login', 'Connexion'), ('logout', 'Déconnexion'), ('register', 'Inscription'),
                         ('postcard_view', 'Vue carte postale'), ('postcard_zoom', 'Zoom carte postale'),
                         ('postcard_like', 'Like carte postale'), ('animation_like', 'Like animation'),
                         ('animation_suggest', 'Suggestion animation'), ('search', 'Recherche'),
                         ('contact', 'Message de contact')], max_length=20),
        ),
    ]
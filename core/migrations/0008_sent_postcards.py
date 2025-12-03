# core/migrations/0008_sent_postcards.py
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0007_alter_postcardlike_unique_together_and_more'),
    ]

    operations = [
        # Add fields to CustomUser
        migrations.AddField(
            model_name='customuser',
            name='signature_image',
            field=models.ImageField(blank=True, null=True, upload_to='signatures/', verbose_name='Signature'),
        ),
        migrations.AddField(
            model_name='customuser',
            name='bio',
            field=models.TextField(blank=True, max_length=500, verbose_name='Biographie'),
        ),

        # Create SentPostcard model
        migrations.CreateModel(
            name='SentPostcard',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('custom_image_url', models.URLField(blank=True, max_length=500)),
                ('message', models.TextField(max_length=1000, verbose_name='Message')),
                ('visibility', models.CharField(
                    choices=[('private', 'Privé - Destinataire uniquement'), ('public', 'Public - Visible par tous')],
                    default='private', max_length=20)),
                ('is_read', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('postcard', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                                               to='core.postcard')),
                ('recipient', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE,
                                                related_name='received_postcards', to=settings.AUTH_USER_MODEL)),
                ('sender', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sent_postcards',
                                             to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Carte postale envoyée',
                'verbose_name_plural': 'Cartes postales envoyées',
                'ordering': ['-created_at'],
            },
        ),

        # Create PostcardComment model
        migrations.CreateModel(
            name='PostcardComment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('message', models.TextField(max_length=500)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('sent_postcard',
                 models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='comments',
                                   to='core.sentpostcard')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Commentaire',
                'verbose_name_plural': 'Commentaires',
                'ordering': ['created_at'],
            },
        ),
    ]
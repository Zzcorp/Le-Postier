from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies = [
        ('core', '0005_remove_postcardlike_unique_user_like_and_more'),  # Change this to your latest migration
    ]

    operations = [
        migrations.CreateModel(
            name='PostcardVideo',
            fields=[
                (
                'id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('video_url', models.URLField(max_length=500, verbose_name='URL Vidéo')),
                ('order', models.PositiveIntegerField(default=0, verbose_name='Ordre')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('postcard', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='videos',
                                               to='core.postcard')),
            ],
            options={
                'verbose_name': 'Vidéo animée',
                'verbose_name_plural': 'Vidéos animées',
                'ordering': ['postcard', 'order'],
            },
        ),
    ]
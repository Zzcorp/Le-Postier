# core/admin.py
from django.contrib import admin
from django.shortcuts import render, redirect
from django.urls import path
from django.http import HttpResponse
from django.core.management import call_command
from django.contrib import messages
import tempfile
import os
from .models import (
    CustomUser, Postcard, PostcardLike, AnimationSuggestion,
    Theme, ContactMessage, SearchLog, PageView, UserActivity,
    SystemLog, IntroSeen, SentPostcard, PostcardComment
)


class PostcardAdmin(admin.ModelAdmin):
    list_display = ['number', 'title', 'rarity', 'has_images', 'has_animation', 'views_count', 'likes_count', 'generation_rating']
    list_editable = ['generation_rating']
    list_filter = ['rarity', 'has_images', 'has_animation']
    search_fields = ['number', 'title', 'keywords']
    readonly_fields = [
        'views_count', 'zoom_count', 'likes_count', 'created_at', 'updated_at',
        'vignette_file', 'grande_file', 'dos_file', 'zoom_file',
        'animation_files', 'media_synced_at', 'search_blob',
        # Notes par vidéo : lecture seule ici, tenues à jour par le helper du
        # modèle (l'API du tableau de bord les édite vidéo par vidéo).
        'generation_ratings',
    ]

    def save_model(self, request, obj, form, change):
        """
        La colonne plate generation_rating reste éditable (liste + fiche) et
        représente la note de la PREMIÈRE vidéo : on repasse par le helper pour
        que generation_ratings ne se désynchronise jamais.
        """
        try:
            note = int(obj.generation_rating or 0)
        except (TypeError, ValueError):
            note = 0
        obj.set_generation_rating(1, max(0, min(5, note)))
        super().save_model(request, obj, form, change)

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('import-csv/', self.import_csv_view, name='postcard-import-csv'),
            path('update-flags/', self.update_flags_view, name='postcard-update-flags'),
        ]
        return custom_urls + urls

    def import_csv_view(self, request):
        """Upload and import CSV"""
        if request.method == 'POST':
            csv_file = request.FILES.get('csv_file')
            update_existing = request.POST.get('update_existing') == 'on'

            if not csv_file:
                messages.error(request, 'Please select a CSV file')
                return redirect('..')

            # Save to temp file
            with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.csv') as tmp:
                for chunk in csv_file.chunks():
                    tmp.write(chunk)
                tmp_path = tmp.name

            try:
                # Run import command
                from io import StringIO
                import sys

                # Capture output
                old_stdout = sys.stdout
                sys.stdout = output = StringIO()

                call_command(
                    'import_csv',
                    tmp_path,
                    update=update_existing,
                )

                sys.stdout = old_stdout
                result = output.getvalue()

                messages.success(request, f'Import successful!\n\n{result}')

            except Exception as e:
                messages.error(request, f'Import failed: {e}')
            finally:
                os.unlink(tmp_path)

            return redirect('..')

        # Show upload form
        return render(request, 'admin/postcard_import_csv.html')

    def update_flags_view(self, request):
        """Rebuild the media index (paths, has_images, has_animation, search_blob)"""
        if request.method == 'POST':
            try:
                call_command('rebuild_media_index')
                messages.success(request, 'Media index rebuilt successfully!')
            except Exception as e:
                messages.error(request, f'Update failed: {e}')

        return redirect('..')


class CustomUserAdmin(admin.ModelAdmin):
    list_display = ['username', 'civilite', 'email', 'category', 'email_verified', 'date_joined']
    search_fields = ['username', 'email']


# Register all models
admin.site.register(Postcard, PostcardAdmin)
admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(PostcardLike)
admin.site.register(AnimationSuggestion)
admin.site.register(Theme)
admin.site.register(ContactMessage)
admin.site.register(SearchLog)
admin.site.register(PageView)
admin.site.register(UserActivity)
admin.site.register(SystemLog)
admin.site.register(IntroSeen)
admin.site.register(SentPostcard)
admin.site.register(PostcardComment)
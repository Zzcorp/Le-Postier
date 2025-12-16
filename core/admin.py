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
    list_display = ['number', 'title', 'rarity', 'has_images', 'views_count', 'likes_count']
    list_filter = ['rarity', 'has_images']
    search_fields = ['number', 'title', 'keywords']
    readonly_fields = ['views_count', 'zoom_count', 'likes_count', 'created_at', 'updated_at']

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
        """Update has_images and has_animation flags"""
        if request.method == 'POST':
            try:
                call_command('update_postcard_flags')
                messages.success(request, 'Flags updated successfully!')
            except Exception as e:
                messages.error(request, f'Update failed: {e}')

        return redirect('..')

    def has_images(self, obj):
        return obj.check_has_vignette()

    has_images.boolean = True


# Register all models
admin.site.register(Postcard, PostcardAdmin)
admin.site.register(CustomUser)
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
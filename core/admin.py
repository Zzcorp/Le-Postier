from django.contrib import admin
from django.utils.html import format_html
from .models import Postcard, Theme, ContactMessage, SearchLog, PageView


@admin.register(Postcard)
class PostcardAdmin(admin.ModelAdmin):
    list_display = ['number', 'title_short', 'rarity', 'thumbnail', 'created_at']
    list_filter = ['rarity', 'created_at']
    search_fields = ['number', 'title', 'keywords', 'description']
    readonly_fields = ['created_at', 'updated_at', 'image_preview']

    fieldsets = (
        ('Informations principales', {
            'fields': ('number', 'title', 'description', 'keywords', 'rarity')
        }),
        ('Images', {
            'fields': ('front_image', 'back_image', 'image_preview')
        }),
        ('Métadonnées', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def title_short(self, obj):
        return obj.title[:50] + '...' if len(obj.title) > 50 else obj.title

    title_short.short_description = 'Titre'

    def thumbnail(self, obj):
        if obj.front_image:
            return format_html(
                '<img src="{}" style="width: 100px; height: auto;" />',
                obj.front_image.url
            )
        return '-'

    thumbnail.short_description = 'Aperçu'

    def image_preview(self, obj):
        if obj.front_image:
            return format_html(
                '<img src="{}" style="max-width: 400px; height: auto;" />',
                obj.front_image.url
            )
        return '-'

    image_preview.short_description = 'Aperçu de l\'image'


@admin.register(Theme)
class ThemeAdmin(admin.ModelAdmin):
    list_display = ['display_name', 'order', 'postcard_count']
    list_editable = ['order']
    filter_horizontal = ['postcards']

    def postcard_count(self, obj):
        return obj.postcards.count()

    postcard_count.short_description = 'Nombre de cartes'


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ['created_at', 'message_short', 'ip_address']
    readonly_fields = ['created_at', 'ip_address']

    def message_short(self, obj):
        return obj.message[:100] + '...' if len(obj.message) > 100 else obj.message

    message_short.short_description = 'Message'


@admin.register(SearchLog)
class SearchLogAdmin(admin.ModelAdmin):
    list_display = ['keyword', 'results_count', 'user', 'created_at']
    list_filter = ['created_at']
    search_fields = ['keyword']
    readonly_fields = ['created_at']


@admin.register(PageView)
class PageViewAdmin(admin.ModelAdmin):
    list_display = ['page_name', 'user', 'timestamp']
    list_filter = ['page_name', 'timestamp']
    readonly_fields = ['timestamp']

    def changelist_view(self, request, extra_context=None):
        # Add statistics
        extra_context = extra_context or {}

        from django.db.models import Count
        from datetime import datetime, timedelta

        # Last 30 days views
        thirty_days_ago = datetime.now() - timedelta(days=30)
        recent_views = PageView.objects.filter(timestamp__gte=thirty_days_ago)

        extra_context['stats'] = {
            'total_views': PageView.objects.count(),
            'recent_views': recent_views.count(),
            'by_page': recent_views.values('page_name').annotate(
                count=Count('id')
            ).order_by('-count')
        }

        return super().changelist_view(request, extra_context=extra_context)

from django.contrib import admin
from django.utils.html import format_html
from .models import (
    CustomUser, Postcard, Theme, ContactMessage,
    SearchLog, PageView, UserActivity, SystemLog, IntroSeen
)


@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ['username', 'email', 'category', 'email_verified', 'is_staff']
    list_filter = ['category', 'email_verified', 'is_staff']
    search_fields = ['username', 'email']


@admin.register(Postcard)
class PostcardAdmin(admin.ModelAdmin):
    list_display = ['number', 'title', 'rarity', 'has_images', 'views_count']
    list_filter = ['rarity']
    search_fields = ['number', 'title', 'keywords']
    readonly_fields = ['preview_vignette']

    def has_images(self, obj):
        return bool(obj.vignette_url)

    has_images.boolean = True
    has_images.short_description = 'Images'

    def preview_vignette(self, obj):
        if obj.vignette_url:
            return format_html('<img src="{}" style="max-width: 200px; max-height: 150px;" />', obj.vignette_url)
        return "No image"

    preview_vignette.short_description = 'Preview'


@admin.register(Theme)
class ThemeAdmin(admin.ModelAdmin):
    list_display = ['display_name', 'order', 'postcard_count']
    filter_horizontal = ['postcards']

    def postcard_count(self, obj):
        return obj.postcards.count()

    postcard_count.short_description = 'Postcards'


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ['created_at', 'user', 'is_read']
    list_filter = ['is_read', 'created_at']


@admin.register(SearchLog)
class SearchLogAdmin(admin.ModelAdmin):
    list_display = ['keyword', 'results_count', 'created_at']
    list_filter = ['created_at']


@admin.register(PageView)
class PageViewAdmin(admin.ModelAdmin):
    list_display = ['page_name', 'timestamp', 'user']
    list_filter = ['page_name', 'timestamp']


admin.site.register(UserActivity)
admin.site.register(SystemLog)
admin.site.register(IntroSeen)
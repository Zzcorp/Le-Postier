# core/admin.py
from django.contrib import admin
from django.utils.html import format_html
from .models import (
    CustomUser, Postcard, PostcardLike, AnimationSuggestion,
    Theme, ContactMessage, SearchLog, PageView, UserActivity,
    SystemLog, IntroSeen, SentPostcard, PostcardComment
)


@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ['username', 'email', 'category', 'email_verified', 'is_staff', 'date_joined']
    list_filter = ['category', 'email_verified', 'is_staff']
    search_fields = ['username', 'email']


@admin.register(Postcard)
class PostcardAdmin(admin.ModelAdmin):
    list_display = ['number', 'title', 'rarity', 'has_images_display', 'has_video_display', 'views_count', 'likes_count']
    list_filter = ['rarity']
    search_fields = ['number', 'title', 'keywords']
    readonly_fields = ['preview_vignette', 'views_count', 'zoom_count', 'likes_count']

    def has_images_display(self, obj):
        return obj.has_vignette()
    has_images_display.boolean = True
    has_images_display.short_description = 'Images'

    def has_video_display(self, obj):
        count = obj.video_count()
        if count > 0:
            return format_html('<span style="color: green;">🎬 {}</span>', count)
        return '-'
    has_video_display.short_description = 'Vidéos'

    def preview_vignette(self, obj):
        url = obj.get_vignette_url()
        if url:
            return format_html('<img src="{}" style="max-width: 200px; max-height: 150px;" />', url)
        return "No image"
    preview_vignette.short_description = 'Preview'


@admin.register(PostcardLike)
class PostcardLikeAdmin(admin.ModelAdmin):
    list_display = ['postcard', 'user', 'is_animated_like', 'created_at']
    list_filter = ['is_animated_like', 'created_at']
    search_fields = ['postcard__number', 'user__username']


@admin.register(AnimationSuggestion)
class AnimationSuggestionAdmin(admin.ModelAdmin):
    list_display = ['postcard', 'user', 'status', 'created_at', 'reviewed_at']
    list_filter = ['status', 'created_at']
    search_fields = ['postcard__number', 'description']
    actions = ['mark_reviewed', 'mark_approved', 'mark_rejected']

    def mark_reviewed(self, request, queryset):
        queryset.update(status='reviewed')
    mark_reviewed.short_description = "Marquer comme examiné"

    def mark_approved(self, request, queryset):
        queryset.update(status='approved')
    mark_approved.short_description = "Approuver"

    def mark_rejected(self, request, queryset):
        queryset.update(status='rejected')
    mark_rejected.short_description = "Rejeter"


@admin.register(Theme)
class ThemeAdmin(admin.ModelAdmin):
    list_display = ['display_name', 'order', 'postcard_count']
    filter_horizontal = ['postcards']

    def postcard_count(self, obj):
        return obj.postcards.count()
    postcard_count.short_description = 'Postcards'


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ['created_at', 'user', 'short_message', 'is_read']
    list_filter = ['is_read', 'created_at']
    search_fields = ['message', 'user__username']

    def short_message(self, obj):
        return obj.message[:50] + '...' if len(obj.message) > 50 else obj.message
    short_message.short_description = 'Message'


@admin.register(SearchLog)
class SearchLogAdmin(admin.ModelAdmin):
    list_display = ['keyword', 'results_count', 'user', 'created_at']
    list_filter = ['created_at']
    search_fields = ['keyword']


@admin.register(PageView)
class PageViewAdmin(admin.ModelAdmin):
    list_display = ['page_name', 'timestamp', 'user', 'ip_address']
    list_filter = ['page_name', 'timestamp']


@admin.register(IntroSeen)
class IntroSeenAdmin(admin.ModelAdmin):
    list_display = ['session_key', 'user', 'date_seen']
    list_filter = ['date_seen']


@admin.register(UserActivity)
class UserActivityAdmin(admin.ModelAdmin):
    list_display = ['user', 'action', 'timestamp', 'ip_address']
    list_filter = ['action', 'timestamp']
    search_fields = ['user__username', 'details']


@admin.register(SystemLog)
class SystemLogAdmin(admin.ModelAdmin):
    list_display = ['level', 'short_message', 'user', 'timestamp']
    list_filter = ['level', 'timestamp']

    def short_message(self, obj):
        return obj.message[:80] + '...' if len(obj.message) > 80 else obj.message
    short_message.short_description = 'Message'


@admin.register(SentPostcard)
class SentPostcardAdmin(admin.ModelAdmin):
    list_display = ['sender', 'recipient', 'visibility', 'is_read', 'created_at']
    list_filter = ['visibility', 'is_read', 'created_at']


@admin.register(PostcardComment)
class PostcardCommentAdmin(admin.ModelAdmin):
    list_display = ['sent_postcard', 'user', 'created_at']
    list_filter = ['created_at']
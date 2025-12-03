# core/admin.py
from django.contrib import admin
from django.utils.html import format_html
from .models import (
    CustomUser, Postcard, PostcardLike, PostcardVideo, AnimationSuggestion,
    Theme, ContactMessage, SearchLog, PageView, UserActivity, SystemLog, IntroSeen
)


# Inline for PostcardVideo
class PostcardVideoInline(admin.TabularInline):
    model = PostcardVideo
    extra = 1
    fields = ['video_url', 'order']


@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ['username', 'email', 'category', 'email_verified', 'is_staff', 'last_intro_seen']
    list_filter = ['category', 'email_verified', 'is_staff']
    search_fields = ['username', 'email']


@admin.register(Postcard)
class PostcardAdmin(admin.ModelAdmin):
    list_display = ['number', 'title', 'rarity', 'has_images', 'video_count', 'views_count', 'likes_count']
    list_filter = ['rarity']
    search_fields = ['number', 'title', 'keywords']
    readonly_fields = ['preview_vignette', 'views_count', 'zoom_count', 'likes_count']
    inlines = [PostcardVideoInline]

    def has_images(self, obj):
        return bool(obj.vignette_url)

    has_images.boolean = True
    has_images.short_description = 'Images'

    def video_count(self, obj):
        count = obj.videos.count()
        return f'🎬 {count}' if count > 0 else '-'

    video_count.short_description = 'Vidéos'

    def preview_vignette(self, obj):
        if obj.vignette_url:
            return format_html('<img src="{}" style="max-width: 200px; max-height: 150px;" />', obj.vignette_url)
        return "No image"

    preview_vignette.short_description = 'Preview'


@admin.register(PostcardVideo)
class PostcardVideoAdmin(admin.ModelAdmin):
    list_display = ['postcard', 'order', 'video_url_short', 'created_at']
    list_filter = ['created_at']
    search_fields = ['postcard__number', 'video_url']
    raw_id_fields = ['postcard']

    def video_url_short(self, obj):
        if len(obj.video_url) > 60:
            return obj.video_url[:60] + '...'
        return obj.video_url

    video_url_short.short_description = 'URL'


@admin.register(PostcardLike)
class PostcardLikeAdmin(admin.ModelAdmin):
    list_display = ['postcard', 'user', 'is_animated_like', 'created_at']
    list_filter = ['is_animated_like', 'created_at']
    search_fields = ['postcard__number', 'user__username']


@admin.register(AnimationSuggestion)
class AnimationSuggestionAdmin(admin.ModelAdmin):
    list_display = ['postcard', 'user', 'status', 'short_description', 'created_at', 'reviewed_at']
    list_filter = ['status', 'created_at']
    search_fields = ['postcard__number', 'description']
    readonly_fields = ['created_at']

    actions = ['mark_reviewed', 'mark_approved', 'mark_rejected']

    def short_description(self, obj):
        if len(obj.description) > 50:
            return obj.description[:50] + '...'
        return obj.description

    short_description.short_description = 'Description'

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
        if len(obj.message) > 50:
            return obj.message[:50] + '...'
        return obj.message

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
        if len(obj.message) > 80:
            return obj.message[:80] + '...'
        return obj.message

    short_message.short_description = 'Message'
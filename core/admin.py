# core/admin.py
from django.contrib import admin
from django.utils.html import format_html
from .models import (
    CustomUser, Postcard, PostcardLike, AnimationSuggestion, Theme,
    ContactMessage, SearchLog, PageView, UserActivity, SystemLog, IntroSeen
)


@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ['username', 'email', 'category', 'email_verified', 'is_staff', 'last_intro_seen']
    list_filter = ['category', 'email_verified', 'is_staff']
    search_fields = ['username', 'email']


@admin.register(Postcard)
class PostcardAdmin(admin.ModelAdmin):
    list_display = ['number', 'title', 'rarity', 'has_images', 'has_animation', 'views_count', 'likes_count']
    list_filter = ['rarity']
    search_fields = ['number', 'title', 'keywords']
    readonly_fields = ['preview_vignette', 'views_count', 'zoom_count', 'likes_count']

    def has_images(self, obj):
        return bool(obj.vignette_url)

    has_images.boolean = True
    has_images.short_description = 'Images'

    def has_animation(self, obj):
        return bool(obj.animated_url)

    has_animation.boolean = True
    has_animation.short_description = 'Animée'

    def preview_vignette(self, obj):
        if obj.vignette_url:
            return format_html('<img src="{}" style="max-width: 200px; max-height: 150px;" />', obj.vignette_url)
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
    readonly_fields = ['created_at']

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


@admin.register(IntroSeen)
class IntroSeenAdmin(admin.ModelAdmin):
    list_display = ['session_key', 'user', 'date_seen']
    list_filter = ['date_seen']


admin.site.register(UserActivity)
admin.site.register(SystemLog)
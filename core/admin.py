from django.contrib import admin
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
    list_display = ['number', 'title', 'rarity', 'views_count']
    list_filter = ['rarity']
    search_fields = ['number', 'title', 'keywords']

@admin.register(Theme)
class ThemeAdmin(admin.ModelAdmin):
    list_display = ['display_name', 'order']
    filter_horizontal = ['postcards']

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

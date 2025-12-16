# core/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # Main pages
    path('', views.home, name='home'),
    path('intro/', views.intro, name='intro'),
    path('decouvrir/', views.decouvrir, name='decouvrir'),
    path('presentation/', views.presentation, name='presentation'),
    path('parcourir/', views.browse, name='browse'),
    path('cp-animes/', views.animated_gallery, name='animated_gallery'),
    path('contact/', views.contact, name='contact'),
    path('inscription/', views.register, name='register'),
    path('connexion/', views.login_view, name='login'),
    path('profil/', views.profile, name='profile'),
    path('logout/', views.logout_view, name='logout'),

    # La Poste - Social Hub
    path('la-poste/', views.la_poste, name='la_poste'),
    path('api/la-poste/send/', views.send_postcard, name='send_postcard'),
    path('api/la-poste/postcards/', views.get_user_postcards, name='get_user_postcards'),
    path('api/la-poste/public/', views.get_public_postcards, name='get_public_postcards'),
    path('api/la-poste/<int:postcard_id>/read/', views.mark_postcard_read, name='mark_postcard_read'),
    path('api/la-poste/<int:postcard_id>/comment/', views.add_comment, name='add_comment'),
    path('api/users/search/', views.search_users, name='search_users'),
    path('api/profile/update/', views.update_profile, name='update_profile'),
    path('api/profile/signature/', views.upload_signature, name='upload_signature'),

    # Admin Dashboard
    path('tableau-de-bord/', views.admin_dashboard, name='admin_dashboard'),
    path('api/admin/stats/', views.admin_stats_api, name='admin_stats_api'),
    path('api/admin/users/', views.admin_users_api, name='admin_users_api'),
    path('api/admin/user/<int:user_id>/', views.admin_user_detail, name='admin_user_detail'),
    path('api/admin/postcards/', views.admin_postcards_api, name='admin_postcards_api'),
    path('api/admin/postcard/<int:postcard_id>/', views.admin_postcard_detail, name='admin_postcard_detail'),
    path('api/admin/suggestions/', views.admin_suggestions_api, name='admin_suggestions_api'),
    path('api/admin/suggestion/<int:suggestion_id>/', views.admin_suggestion_detail, name='admin_suggestion_detail'),
    path('api/admin/postcards/next-number/', views.admin_next_postcard_number, name='admin_next_postcard_number'),

    # Media upload endpoints (NEW)
    path('api/admin/upload-media/', views.admin_upload_media, name='admin_upload_media'),
    path('api/admin/media-stats/', views.admin_media_stats, name='admin_media_stats'),

    # API endpoints
    path('api/postcard/<int:postcard_id>/', views.get_postcard_detail, name='postcard_detail'),
    path('api/postcard/<int:postcard_id>/zoom/', views.zoom_postcard, name='postcard_zoom'),
    path('api/postcard/<int:postcard_id>/like/', views.like_postcard, name='postcard_like'),
    path('api/postcard/<int:postcard_id>/suggest/', views.suggest_animation, name='suggest_animation'),
    path('api/debug/postcard/<int:postcard_id>/', views.debug_postcard_images, name='debug_postcard'),

    # Legacy URLs
    path('admin/update-user/<int:user_id>/', views.update_user_category, name='update_user_category'),
    path('admin/delete-user/<int:user_id>/', views.delete_user, name='delete_user'),
    path('galerie/', views.decouvrir, name='gallery'),
]
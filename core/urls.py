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

    # Authentication - Updated flow
    path('inscription/', views.register, name='register'),
    path('verification/', views.verify_email, name='verify_email'),
    path('verification/renvoyer/', views.resend_verification_code, name='resend_verification_code'),
    path('definir-mot-de-passe/', views.set_password, name='set_password'),
    path('inscription-terminee/', views.registration_complete, name='registration_complete'),
    path('connexion/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # Profile - Enhanced
    path('profil/', views.profile_view, name='profile'),
    path('profil/parametres/', views.profile_settings, name='profile_settings'),
    path('profil/connexions/', views.profile_connections, name='profile_connections'),
    path('profil/favoris/', views.profile_favorites, name='profile_favorites'),
    path('profil/activite/', views.profile_activity, name='profile_activity'),
    path('utilisateur/<str:username>/', views.view_user_profile, name='view_user_profile'),

    # Profile API
    path('api/profile/update/', views.update_profile, name='update_profile'),
    path('api/profile/signature/', views.upload_signature, name='upload_signature'),
    path('api/profile/cover/', views.upload_cover, name='upload_cover'),
    path('api/profile/change-password/', views.change_password, name='change_password'),
    path('api/connection/<int:connection_id>/favorite/', views.toggle_connection_favorite, name='toggle_connection_favorite'),
    path('api/connection/<int:connection_id>/notes/', views.update_connection_notes, name='update_connection_notes'),

    # La Poste - Social Hub
    path('la-poste/', views.la_poste, name='la_poste'),
    path('api/la-poste/send/', views.send_postcard, name='send_postcard'),
    path('api/la-poste/postcards/', views.get_user_postcards, name='get_user_postcards'),
    path('api/la-poste/public/', views.get_public_postcards, name='get_public_postcards'),
    path('api/la-poste/<int:postcard_id>/read/', views.mark_postcard_read, name='mark_postcard_read'),
    path('api/la-poste/<int:postcard_id>/comment/', views.add_comment, name='add_comment'),
    path('api/la-poste/<int:postcard_id>/message/', views.get_postcard_message, name='get_postcard_message'),
    path('api/la-poste/check-signature/', views.check_user_signature, name='check_user_signature'),
    path('api/users/search/', views.search_users, name='search_users'),

    # Postcard API endpoints
    path('api/postcard/<int:postcard_id>/', views.get_postcard_detail, name='postcard_detail'),
    path('api/postcard/<int:postcard_id>/zoom/', views.zoom_postcard, name='postcard_zoom'),
    path('api/postcard/<int:postcard_id>/like/', views.like_postcard, name='postcard_like'),
    path('api/postcard/<int:postcard_id>/suggest/', views.suggest_animation, name='suggest_animation'),
    path('api/postcards/for-cover/', views.get_postcards_for_cover, name='postcards_for_cover'),

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
    path('api/admin/realtime/', views.admin_realtime_api, name='admin_realtime_api'),
    path('api/admin/geographic/', views.admin_geographic_api, name='admin_geographic_api'),
    path('api/admin/ip/<str:ip_address>/', views.admin_ip_lookup, name='admin_ip_lookup'),
    path('api/admin/export/', views.admin_export_data, name='admin_export_data'),
    path('api/admin/upload-media/', views.admin_upload_media, name='admin_upload_media'),
    path('api/admin/media-stats/', views.admin_media_stats, name='admin_media_stats'),
    path('api/admin/likes/', views.admin_likes_api, name='admin_likes_api'),
    path('api/admin/geographic/', views.admin_geographic_api, name='admin_geographic_api'),
    path('api/admin/ip/<str:ip_address>/', views.admin_ip_lookup, name='admin_ip_lookup'),
    path('api/admin/postcard-analytics/<int:postcard_id>/', views.admin_postcard_analytics, name='admin_postcard_analytics'),
    path('api/admin/add-postcard/', views.admin_add_postcard, name='admin_add_postcard'),
    path('api/admin/detailed-stats/', views.admin_detailed_stats_api, name='admin_detailed_stats_api'),
    path('api/admin/user-analytics/<int:user_id>/', views.admin_user_analytics_api, name='admin_user_analytics_api'),
    path('api/admin/country-analytics/<str:country>/', views.admin_country_analytics_api, name='admin_country_analytics_api'),
    path('api/admin/export/', views.admin_export_analytics, name='admin_export_analytics'),

    # Debug
    path('debug/browse/', views.debug_browse, name='debug_browse'),
    path('debug/media/', views.debug_media, name='debug_media'),
    path('debug/postcard/<int:postcard_id>/', views.debug_postcard_images, name='debug_postcard_images'),
]
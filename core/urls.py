from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('decouvrir/', views.decouvrir, name='decouvrir'),
    path('presentation/', views.presentation, name='presentation'),
    path('parcourir/', views.browse, name='browse'),
    path('contact/', views.contact, name='contact'),
    path('inscription/', views.register, name='register'),
    path('connexion/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # Admin Dashboard
    path('tableau-de-bord/', views.admin_dashboard, name='admin_dashboard'),
    path('api/admin/stats/', views.admin_stats_api, name='admin_stats_api'),
    path('api/admin/users/', views.admin_users_api, name='admin_users_api'),
    path('api/admin/user/<int:user_id>/', views.admin_user_detail, name='admin_user_detail'),
    path('api/admin/postcards/', views.admin_postcards_api, name='admin_postcards_api'),
    path('api/admin/postcard/<int:postcard_id>/', views.admin_postcard_detail, name='admin_postcard_detail'),

    # API endpoints
    path('api/postcard/<int:postcard_id>/', views.get_postcard_detail, name='postcard_detail'),
    path('api/postcard/<int:postcard_id>/zoom/', views.zoom_postcard, name='postcard_zoom'),

    # Legacy
    path('admin/update-user/<int:user_id>/', views.update_user_category, name='update_user_category'),
    path('admin/delete-user/<int:user_id>/', views.delete_user, name='delete_user'),

    # Redirects for old URLs
    path('galerie/', views.decouvrir, name='gallery'),
]
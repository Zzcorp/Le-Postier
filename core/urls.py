from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('intro/', views.intro_view, name='intro'),
    path('parcourir/', views.browse, name='browse'),
    path('galerie/', views.gallery, name='gallery'),
    path('presentation/', views.presentation, name='presentation'),
    path('contact/', views.contact, name='contact'),
    path('inscription/', views.register, name='register'),
    path('connexion/', views.login_view, name='login'),
    path('health/', views.health_check, name='health_check'),

    # Admin
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin/update-user/<int:user_id>/', views.update_user_category, name='update_user_category'),
    path('admin/delete-user/<int:user_id>/', views.delete_user, name='delete_user'),

    # AJAX endpoints
    path('api/postcard/<int:postcard_id>/', views.get_postcard_detail, name='postcard_detail'),
    path('api/postcard/<int:postcard_id>/zoom/', views.zoom_postcard, name='postcard_zoom'),

    # Auth
    path('logout/', auth_views.LogoutView.as_view(next_page='home'), name='logout'),
]
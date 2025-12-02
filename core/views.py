from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Q, Count
from django.db.models.functions import TruncDate
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from datetime import timedelta
import traceback
import json

from .models import (
    CustomUser, Postcard, Theme, ContactMessage,
    SearchLog, PageView, UserActivity, SystemLog, IntroSeen
)
from .forms import ContactForm, SimpleRegistrationForm

# core/views.py - Add these imports and views

import ftplib
from io import BytesIO
from django.http import HttpResponse, Http404
from django.views.decorators.cache import cache_page
from django.conf import settings

# FTP Configuration - Add to settings.py or use directly
FTP_CONFIG = {
    'host': 'ftp.cluster010.hosting.ovh.net',
    'user': 'samathey',
    'password': 'qaszSZDE123',
    'image_path': 'www/collection_cp/cartes',  # Adjust after exploring
}

# core/views.py - Improved version with better caching

import ftplib
from io import BytesIO
from django.http import HttpResponse, Http404
from django.core.cache import cache
from django.conf import settings
import hashlib


def get_ftp_image(image_type, number):
    """
    Fetch image from FTP with caching
    """
    # Create cache key
    cache_key = f"postcard_image_{image_type}_{number}"

    # Check cache first
    cached_data = cache.get(cache_key)
    if cached_data is not None:
        return cached_data if cached_data != 'NOT_FOUND' else None

    # Fetch from FTP
    try:
        ftp = ftplib.FTP(
            getattr(settings, 'FTP_HOST', 'ftp.cluster010.hosting.ovh.net'),
            timeout=30
        )
        ftp.login(
            getattr(settings, 'FTP_USER', 'samathey'),
            getattr(settings, 'FTP_PASSWORD', 'qaszSZDE123')
        )

        # Build path
        folder_map = {
            'vignette': 'Vignette',
            'grande': 'Grande',
            'dos': 'Dos',
            'zoom': 'Zoom',
        }

        folder = folder_map.get(image_type.lower())
        if not folder:
            cache.set(cache_key, 'NOT_FOUND', 60 * 60)  # Cache miss for 1 hour
            return None

        num_padded = str(number).zfill(6)
        base_path = getattr(settings, 'FTP_IMAGE_PATH', 'www/collection_cp/cartes')
        file_path = f"{base_path}/{folder}/{num_padded}.jpg"

        # Download
        buffer = BytesIO()
        ftp.retrbinary(f'RETR {file_path}', buffer.write)
        ftp.quit()

        buffer.seek(0)
        image_data = buffer.getvalue()

        # Cache for 24 hours
        cache.set(cache_key, image_data, 60 * 60 * 24)

        return image_data

    except ftplib.error_perm:
        # File not found - cache this result
        cache.set(cache_key, 'NOT_FOUND', 60 * 60)
        return None
    except Exception as e:
        print(f"FTP Error fetching {image_type}/{number}: {e}")
        return None


def serve_postcard_image(request, image_type, number):
    """
    Serve postcard image - with caching and proper headers
    """
    valid_types = ['vignette', 'grande', 'dos', 'zoom']

    image_type = image_type.lower()
    if image_type not in valid_types:
        raise Http404("Invalid image type")

    # Clean number
    number = ''.join(filter(str.isdigit, str(number).split('.')[0]))
    if not number:
        raise Http404("Invalid number")

    # Get image
    image_data = get_ftp_image(image_type, number)

    if image_data is None:
        raise Http404("Image not found")

    # Generate ETag for browser caching
    etag = hashlib.md5(image_data).hexdigest()

    # Check If-None-Match header
    if request.META.get('HTTP_IF_NONE_MATCH') == etag:
        return HttpResponse(status=304)

    response = HttpResponse(image_data, content_type='image/jpeg')
    response['Cache-Control'] = 'public, max-age=86400'
    response['ETag'] = etag
    response['Access-Control-Allow-Origin'] = '*'

    return response


# Alternative: Batch check which images exist
def check_ftp_images(request):
    """Admin view to check which images exist on FTP"""
    if not request.user.is_staff:
        raise Http404()

    from core.models import Postcard

    fetcher = FTPImageFetcher()
    results = []

    postcards = Postcard.objects.all()[:20]  # Test with 20

    for pc in postcards:
        num = ''.join(filter(str.isdigit, str(pc.number)))
        if not num:
            continue

        exists = {
            'number': pc.number,
            'vignette': fetcher.get_image('vignette', num) is not None,
            'grande': fetcher.get_image('grande', num) is not None,
        }
        results.append(exists)

    from django.http import JsonResponse
    return JsonResponse({'results': results})


def is_admin(user):
    """Check if user is admin"""
    return user.is_authenticated and (user.is_staff or user.is_superuser)


def home(request):
    """Home page view"""
    try:
        return render(request, 'home.html')
    except Exception as e:
        return HttpResponse(f"<h1>Home Error</h1><pre>{traceback.format_exc()}</pre>")


def decouvrir(request):
    """Découvrir page - 6 category panels"""
    try:
        # Define the 6 discovery categories
        categories = [
            {
                'title': 'Les Bateaux',
                'subtitle': 'Découvrez les embarcations fluviales',
                'keyword': 'bateau',
                'image': 'https://collections.samathey.fr/collection_cp/cartes/Grande/000001.jpg',
            },
            {
                'title': 'Les Écluses',
                'subtitle': 'Passages et ouvrages d\'art',
                'keyword': 'écluse',
                'image': 'https://collections.samathey.fr/collection_cp/cartes/Grande/000050.jpg',
            },
            {
                'title': 'Les Ponts',
                'subtitle': 'Traversées historiques',
                'keyword': 'pont',
                'image': 'https://collections.samathey.fr/collection_cp/cartes/Grande/000100.jpg',
            },
            {
                'title': 'La Seine',
                'subtitle': 'Le fleuve parisien',
                'keyword': 'seine',
                'image': 'https://collections.samathey.fr/collection_cp/cartes/Grande/000150.jpg',
            },
            {
                'title': 'La Marne',
                'subtitle': 'Affluent et paysages',
                'keyword': 'marne',
                'image': 'https://collections.samathey.fr/collection_cp/cartes/Grande/000200.jpg',
            },
            {
                'title': 'Les Métiers',
                'subtitle': 'Mariniers et travailleurs',
                'keyword': 'marinier',
                'image': 'https://collections.samathey.fr/collection_cp/cartes/Grande/000250.jpg',
            },
        ]

        return render(request, 'decouvrir.html', {'categories': categories})

    except Exception as e:
        import traceback
        return HttpResponse(f"<h1>Découvrir Error</h1><pre>{traceback.format_exc()}</pre>")


@login_required
def profile(request):
    """User profile page"""
    try:
        context = {
            'user': request.user,
        }
        return render(request, 'profile.html', context)
    except Exception as e:
        import traceback
        return HttpResponse(f"<h1>Profile Error</h1><pre>{traceback.format_exc()}</pre>")


def browse(request):
    """Browse page"""
    try:
        query = request.GET.get('keywords_input', '').strip()

        postcards = Postcard.objects.all()
        themes = Theme.objects.all()

        if query:
            postcards = postcards.filter(
                Q(title__icontains=query) |
                Q(keywords__icontains=query)
            )
            # Log search
            SearchLog.objects.create(
                keyword=query,
                results_count=postcards.count(),
                user=request.user if request.user.is_authenticated else None
            )

        postcards_with_images = postcards.exclude(vignette_url='').exclude(vignette_url__isnull=True)

        context = {
            'postcards': postcards_with_images[:50],
            'themes': themes,
            'query': query,
            'total_count': postcards.count(),
            'slideshow_postcards': postcards_with_images[:20],
            'user': request.user,
        }

        return render(request, 'browse.html', context)

    except Exception as e:
        return HttpResponse(f"<h1>Browse Error</h1><pre>{traceback.format_exc()}</pre>")


def gallery(request):
    """Gallery page"""
    try:
        postcards = Postcard.objects.exclude(
            vignette_url=''
        ).exclude(
            vignette_url__isnull=True
        ).order_by('?')[:50]

        context = {
            'postcards': postcards,
            'user': request.user,
        }

        return render(request, 'gallery.html', context)

    except Exception as e:
        return HttpResponse(f"<h1>Gallery Error</h1><pre>{traceback.format_exc()}</pre>")


def presentation(request):
    """Presentation page"""
    try:
        return render(request, 'presentation.html')
    except Exception as e:
        return HttpResponse(f"<h1>Presentation Error</h1><pre>{traceback.format_exc()}</pre>")


def contact(request):
    """Contact page"""
    try:
        if request.method == 'POST':
            form = ContactForm(request.POST)
            if form.is_valid():
                message = form.save(commit=False)
                if request.user.is_authenticated:
                    message.user = request.user
                message.save()
                return render(request, 'contact.html', {'form': ContactForm(), 'success': True})
        else:
            form = ContactForm()

        return render(request, 'contact.html', {'form': form})

    except Exception as e:
        return HttpResponse(f"<h1>Contact Error</h1><pre>{traceback.format_exc()}</pre>")


def register(request):
    """Registration page"""
    try:
        if request.method == 'POST':
            form = SimpleRegistrationForm(request.POST)
            if form.is_valid():
                user = form.save()
                login(request, user)
                return redirect('home')
        else:
            form = SimpleRegistrationForm()

        return render(request, 'register.html', {'form': form})

    except Exception as e:
        return HttpResponse(f"<h1>Register Error</h1><pre>{traceback.format_exc()}</pre>")


def login_view(request):
    """Login page"""
    try:
        error = None
        if request.method == 'POST':
            username = request.POST.get('username')
            password = request.POST.get('password')
            user = authenticate(request, username=username, password=password)

            if user is not None:
                login(request, user)
                next_url = request.GET.get('next', '/')
                return redirect(next_url)
            else:
                error = "Nom d'utilisateur ou mot de passe incorrect."

        return render(request, 'login.html', {'error': error})

    except Exception as e:
        return HttpResponse(f"<h1>Login Error</h1><pre>{traceback.format_exc()}</pre>")


def logout_view(request):
    """Logout"""
    logout(request)
    return redirect('home')


def get_postcard_detail(request, postcard_id):
    """API endpoint for postcard details"""
    try:
        postcard = Postcard.objects.get(id=postcard_id)
        postcard.views_count += 1
        postcard.save(update_fields=['views_count'])

        data = {
            'id': postcard.id,
            'number': postcard.number,
            'title': postcard.title,
            'description': postcard.description,
            'keywords': postcard.keywords,
            'rarity': postcard.rarity,
            'vignette_url': postcard.vignette_url or '',
            'grande_url': postcard.grande_url or '',
            'dos_url': postcard.dos_url or '',
            'zoom_url': postcard.zoom_url or '',
        }
        return JsonResponse(data)
    except Postcard.DoesNotExist:
        return JsonResponse({'error': 'Not found'}, status=404)


def zoom_postcard(request, postcard_id):
    """API endpoint for zoom"""
    try:
        postcard = Postcard.objects.get(id=postcard_id)

        can_view = True
        if postcard.rarity == 'very_rare':
            if not request.user.is_authenticated:
                can_view = False
            elif hasattr(request.user, 'can_view_very_rare') and not request.user.can_view_very_rare():
                can_view = False

        if can_view:
            postcard.zoom_count += 1
            postcard.save(update_fields=['zoom_count'])

        return JsonResponse({
            'can_view': can_view,
            'zoom_url': postcard.zoom_url if can_view else '',
            'grande_url': postcard.grande_url if can_view else '',
        })
    except Postcard.DoesNotExist:
        return JsonResponse({'error': 'Not found'}, status=404)


# ============================================
# ADMIN DASHBOARD VIEWS
# ============================================

@user_passes_test(is_admin)
def admin_dashboard(request):
    """Custom admin dashboard"""
    try:
        # Get statistics
        today = timezone.now().date()
        week_ago = today - timedelta(days=7)

        context = {
            'total_users': CustomUser.objects.count(),
            'total_postcards': Postcard.objects.count(),
            'total_themes': Theme.objects.count(),
            'total_messages': ContactMessage.objects.count(),
            'unread_messages': ContactMessage.objects.filter(is_read=False).count(),
            'total_searches': SearchLog.objects.count(),
            'today_searches': SearchLog.objects.filter(created_at__date=today).count(),
            'postcards_with_images': Postcard.objects.exclude(vignette_url='').exclude(
                vignette_url__isnull=True).count(),
            'recent_users': CustomUser.objects.order_by('-date_joined')[:5],
            'recent_searches': SearchLog.objects.order_by('-created_at')[:10],
            'recent_messages': ContactMessage.objects.order_by('-created_at')[:5],
            'top_postcards': Postcard.objects.order_by('-views_count')[:5],
            'user_categories': CustomUser.USER_CATEGORIES,
        }

        return render(request, 'admin_dashboard.html', context)

    except Exception as e:
        return HttpResponse(f"<h1>Admin Error</h1><pre>{traceback.format_exc()}</pre>")


@user_passes_test(is_admin)
def admin_stats_api(request):
    """API for dashboard statistics"""
    try:
        today = timezone.now().date()

        # Get daily views for last 7 days
        daily_views = []
        for i in range(7):
            date = today - timedelta(days=6 - i)
            count = PageView.objects.filter(timestamp__date=date).count()
            daily_views.append({
                'date': date.strftime('%d/%m'),
                'count': count
            })

        # Get daily searches
        daily_searches = []
        for i in range(7):
            date = today - timedelta(days=6 - i)
            count = SearchLog.objects.filter(created_at__date=date).count()
            daily_searches.append({
                'date': date.strftime('%d/%m'),
                'count': count
            })

        # Top search terms
        top_searches = SearchLog.objects.values('keyword').annotate(
            count=Count('id')
        ).order_by('-count')[:10]

        return JsonResponse({
            'daily_views': daily_views,
            'daily_searches': daily_searches,
            'top_searches': list(top_searches),
            'total_users': CustomUser.objects.count(),
            'total_postcards': Postcard.objects.count(),
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@user_passes_test(is_admin)
def admin_users_api(request):
    """API for user management"""
    if request.method == 'GET':
        users = CustomUser.objects.all().order_by('-date_joined')
        data = [{
            'id': u.id,
            'username': u.username,
            'email': u.email,
            'category': u.category,
            'is_staff': u.is_staff,
            'is_active': u.is_active,
            'date_joined': u.date_joined.strftime('%d/%m/%Y %H:%M'),
            'last_login': u.last_login.strftime('%d/%m/%Y %H:%M') if u.last_login else 'Jamais',
        } for u in users]
        return JsonResponse({'users': data})

    return JsonResponse({'error': 'Method not allowed'}, status=405)


@user_passes_test(is_admin)
@require_http_methods(["GET", "PUT", "DELETE"])
def admin_user_detail(request, user_id):
    """API for individual user management"""
    try:
        user = CustomUser.objects.get(id=user_id)

        if request.method == 'GET':
            return JsonResponse({
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'category': user.category,
                'is_staff': user.is_staff,
                'is_active': user.is_active,
            })

        elif request.method == 'PUT':
            data = json.loads(request.body)

            if 'category' in data:
                user.category = data['category']
            if 'is_active' in data:
                user.is_active = data['is_active']
            if 'is_staff' in data and request.user.is_superuser:
                user.is_staff = data['is_staff']

            user.save()
            return JsonResponse({'success': True})

        elif request.method == 'DELETE':
            if user.is_superuser:
                return JsonResponse({'error': 'Cannot delete superuser'}, status=400)
            user.delete()
            return JsonResponse({'success': True})

    except CustomUser.DoesNotExist:
        return JsonResponse({'error': 'User not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@user_passes_test(is_admin)
def admin_postcards_api(request):
    """API for postcard management"""
    if request.method == 'GET':
        postcards = Postcard.objects.all().order_by('number')[:100]
        data = [{
            'id': p.id,
            'number': p.number,
            'title': p.title[:50],
            'rarity': p.rarity,
            'views_count': p.views_count,
            'has_vignette': bool(p.vignette_url),
            'has_grande': bool(p.grande_url),
            'has_dos': bool(p.dos_url),
            'has_zoom': bool(p.zoom_url),
        } for p in postcards]
        return JsonResponse({'postcards': data, 'total': Postcard.objects.count()})

    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
            postcard = Postcard.objects.create(
                number=data['number'],
                title=data['title'],
                description=data.get('description', ''),
                keywords=data.get('keywords', ''),
                rarity=data.get('rarity', 'common'),
            )
            return JsonResponse({'success': True, 'id': postcard.id})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)

    return JsonResponse({'error': 'Method not allowed'}, status=405)


@user_passes_test(is_admin)
@require_http_methods(["GET", "PUT", "DELETE"])
def admin_postcard_detail(request, postcard_id):
    """API for individual postcard management"""
    try:
        postcard = Postcard.objects.get(id=postcard_id)

        if request.method == 'GET':
            return JsonResponse({
                'id': postcard.id,
                'number': postcard.number,
                'title': postcard.title,
                'description': postcard.description,
                'keywords': postcard.keywords,
                'rarity': postcard.rarity,
                'vignette_url': postcard.vignette_url,
                'grande_url': postcard.grande_url,
                'dos_url': postcard.dos_url,
                'zoom_url': postcard.zoom_url,
                'views_count': postcard.views_count,
                'zoom_count': postcard.zoom_count,
            })

        elif request.method == 'PUT':
            data = json.loads(request.body)

            for field in ['number', 'title', 'description', 'keywords', 'rarity',
                          'vignette_url', 'grande_url', 'dos_url', 'zoom_url']:
                if field in data:
                    setattr(postcard, field, data[field])

            postcard.save()
            return JsonResponse({'success': True})

        elif request.method == 'DELETE':
            postcard.delete()
            return JsonResponse({'success': True})

    except Postcard.DoesNotExist:
        return JsonResponse({'error': 'Postcard not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def update_user_category(request, user_id):
    """Legacy update user category"""
    return admin_user_detail(request, user_id)


def delete_user(request, user_id):
    """Legacy delete user"""
    return admin_user_detail(request, user_id)


# core/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Q, Count, Sum, Avg
from django.db.models.functions import TruncDate, TruncHour
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from datetime import timedelta
import traceback
import json

from .models import (
    CustomUser, Postcard, PostcardLike, AnimationSuggestion, Theme,
    ContactMessage, SearchLog, PageView, UserActivity, SystemLog, IntroSeen
)
from .forms import ContactForm, SimpleRegistrationForm


def get_client_ip(request):
    """Get client IP address from request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def is_admin(user):
    """Check if user is admin"""
    return user.is_authenticated and (user.is_staff or user.is_superuser)


def should_show_intro(request):
    """Check if intro should be shown to user"""
    today = timezone.now().date()

    # For authenticated users
    if request.user.is_authenticated:
        if request.user.last_intro_seen == today:
            return False
        return True

    # For anonymous users, use session
    if not request.session.session_key:
        request.session.create()

    session_key = request.session.session_key

    # Check if intro was seen today
    intro_seen = IntroSeen.objects.filter(
        session_key=session_key,
        date_seen=today
    ).exists()

    return not intro_seen


def mark_intro_seen(request):
    """Mark intro as seen for today"""
    today = timezone.now().date()

    if request.user.is_authenticated:
        request.user.last_intro_seen = today
        request.user.save(update_fields=['last_intro_seen'])

    if not request.session.session_key:
        request.session.create()

    IntroSeen.objects.get_or_create(
        session_key=request.session.session_key,
        date_seen=today,
        defaults={'user': request.user if request.user.is_authenticated else None}
    )


def intro(request):
    """Intro/Loading page"""
    mark_intro_seen(request)

    # Get redirect URL (default to home)
    redirect_url = request.GET.get('next', '/')

    return render(request, 'intro.html', {
        'redirect_url': redirect_url
    })


def home(request):
    """Home page view"""
    try:
        # Check if intro should be shown
        if should_show_intro(request):
            return redirect(f'/intro/?next=/')

        # Get all animated postcards for background video
        animated_postcards = Postcard.objects.exclude(
            animated_url=''
        ).exclude(
            animated_url__isnull=True
        ).values_list('animated_url', flat=True)[:50]

        # Flatten URLs (since some might have multiple)
        all_videos = []
        for url_string in animated_postcards:
            urls = [u.strip() for u in url_string.split(',') if u.strip()]
            all_videos.extend(urls)

        return render(request, 'home.html', {
            'animated_videos': all_videos[:50]  # Limit to 50
        })
    except Exception as e:
        return HttpResponse(f"<h1>Home Error</h1><pre>{traceback.format_exc()}</pre>")


def decouvrir(request):
    """Découvrir page - 6 paintings with videos"""
    try:
        paintings = [
            {
                'title': "Ascenseur de la Terrasse",
                'image_off': 'https://collections.samathey.fr/decouvrir/static/Cadre_1_Off.png',
                'image_on': 'https://collections.samathey.fr/decouvrir/static/Cadre_1_Clic.png',
                'video_id': '2hD8sSnelHs',
            },
            {
                'title': "Accident de l'archevêché",
                'image_off': 'https://collections.samathey.fr/decouvrir/static/Cadre_2_Off.png',
                'image_on': 'https://collections.samathey.fr/decouvrir/static/Cadre_2_Clic.png',
                'video_id': 'dQw4w9WgXcQ',  # Replace with actual video ID
            },
            {
                'title': "Bateau « Touriste »",
                'image_off': 'https://collections.samathey.fr/decouvrir/static/Cadre_3_Off.png',
                'image_on': 'https://collections.samathey.fr/decouvrir/static/Cadre_3_Clic.png',
                'video_id': '6462WnYcRxo',
            },
            {
                'title': "Machine de Marly",
                'image_off': 'https://collections.samathey.fr/decouvrir/static/Cadre_4_Off.png',
                'image_on': 'https://collections.samathey.fr/decouvrir/static/Cadre_4_Clic.png',
                'video_id': 'h-bLPdvk4BU',
            },
            {
                'title': "Yacht « Le Druide »",
                'image_off': 'https://collections.samathey.fr/decouvrir/static/Cadre_5_Off.png',
                'image_on': 'https://collections.samathey.fr/decouvrir/static/Cadre_5_Clic.png',
                'video_id': 'J-VMocHfFb8',
            },
            {
                'title': "La Pénichienne",
                'image_off': 'https://collections.samathey.fr/decouvrir/static/Cadre_6_Off.png',
                'image_on': 'https://collections.samathey.fr/decouvrir/static/Cadre_6_Clic.png',
                'video_id': '0ftXAcvLukY',
            },
        ]

        return render(request, 'decouvrir.html', {'paintings': paintings})

    except Exception as e:
        return HttpResponse(f"<h1>Découvrir Error</h1><pre>{traceback.format_exc()}</pre>")


def animated_gallery(request):
    """Animated postcards gallery page"""
    try:
        # Get all postcards with animations
        animated_postcards = Postcard.objects.exclude(
            animated_url=''
        ).exclude(
            animated_url__isnull=True
        ).order_by('-likes_count', 'number')

        # Get user's likes if authenticated
        user_likes = set()
        if request.user.is_authenticated:
            user_likes = set(
                PostcardLike.objects.filter(
                    user=request.user,
                    is_animated_like=True
                ).values_list('postcard_id', flat=True)
            )
        elif request.session.session_key:
            user_likes = set(
                PostcardLike.objects.filter(
                    session_key=request.session.session_key,
                    is_animated_like=True
                ).values_list('postcard_id', flat=True)
            )

        context = {
            'postcards': animated_postcards,
            'user_likes': user_likes,
            'total_count': animated_postcards.count(),
        }

        return render(request, 'animated_gallery.html', context)

    except Exception as e:
        return HttpResponse(f"<h1>Animated Gallery Error</h1><pre>{traceback.format_exc()}</pre>")


@login_required
def profile(request):
    """User profile page"""
    try:
        context = {
            'user': request.user,
        }
        return render(request, 'profile.html', context)
    except Exception as e:
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
                user=request.user if request.user.is_authenticated else None,
                ip_address=get_client_ip(request)
            )

        postcards_with_images = postcards.exclude(vignette_url='').exclude(vignette_url__isnull=True)

        # Get user's likes
        user_likes = set()
        if request.user.is_authenticated:
            user_likes = set(
                PostcardLike.objects.filter(
                    user=request.user,
                    is_animated_like=False
                ).values_list('postcard_id', flat=True)
            )
        elif request.session.session_key:
            user_likes = set(
                PostcardLike.objects.filter(
                    session_key=request.session.session_key,
                    is_animated_like=False
                ).values_list('postcard_id', flat=True)
            )

        context = {
            'postcards': postcards_with_images[:50],
            'themes': themes,
            'query': query,
            'total_count': postcards.count(),
            'slideshow_postcards': postcards_with_images[:20],
            'user': request.user,
            'user_likes': user_likes,
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
                message.ip_address = get_client_ip(request)
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

        # Check if user has liked
        has_liked = False
        if request.user.is_authenticated:
            has_liked = PostcardLike.objects.filter(
                postcard=postcard,
                user=request.user,
                is_animated_like=False
            ).exists()
        elif request.session.session_key:
            has_liked = PostcardLike.objects.filter(
                postcard=postcard,
                session_key=request.session.session_key,
                is_animated_like=False
            ).exists()

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
            'animated_urls': postcard.get_animated_urls(),
            'likes_count': postcard.likes_count,
            'has_liked': has_liked,
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


@require_http_methods(["POST"])
def like_postcard(request, postcard_id):
    """API endpoint to like/unlike a postcard"""
    try:
        postcard = get_object_or_404(Postcard, id=postcard_id)
        is_animated = request.POST.get('is_animated', 'false').lower() == 'true'

        if not request.session.session_key:
            request.session.create()

        # Check for existing like
        like_kwargs = {
            'postcard': postcard,
            'is_animated_like': is_animated,
        }

        if request.user.is_authenticated:
            like_kwargs['user'] = request.user
        else:
            like_kwargs['session_key'] = request.session.session_key

        existing_like = PostcardLike.objects.filter(**like_kwargs).first()

        if existing_like:
            # Unlike
            existing_like.delete()
            postcard.likes_count = max(0, postcard.likes_count - 1)
            postcard.save(update_fields=['likes_count'])
            liked = False
        else:
            # Like
            like_kwargs['ip_address'] = get_client_ip(request)
            PostcardLike.objects.create(**like_kwargs)
            postcard.likes_count += 1
            postcard.save(update_fields=['likes_count'])
            liked = True

        return JsonResponse({
            'success': True,
            'liked': liked,
            'likes_count': postcard.likes_count
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@require_http_methods(["POST"])
def suggest_animation(request, postcard_id):
    """API endpoint to submit animation suggestion"""
    try:
        postcard = get_object_or_404(Postcard, id=postcard_id)
        description = request.POST.get('description', '').strip()

        if not description:
            return JsonResponse({'error': 'Description required'}, status=400)

        if len(description) < 10:
            return JsonResponse({'error': 'Description too short'}, status=400)

        suggestion = AnimationSuggestion.objects.create(
            postcard=postcard,
            user=request.user if request.user.is_authenticated else None,
            description=description,
            ip_address=get_client_ip(request)
        )

        return JsonResponse({
            'success': True,
            'message': 'Suggestion enregistrée avec succès!'
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


# ============================================
# ADMIN DASHBOARD VIEWS
# ============================================

@user_passes_test(is_admin)
def admin_dashboard(request):
    """Custom admin dashboard with enhanced metrics"""
    try:
        today = timezone.now().date()
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)

        # Basic stats
        total_users = CustomUser.objects.count()
        new_users_week = CustomUser.objects.filter(date_joined__date__gte=week_ago).count()
        new_users_month = CustomUser.objects.filter(date_joined__date__gte=month_ago).count()

        total_postcards = Postcard.objects.count()
        postcards_with_images = Postcard.objects.exclude(vignette_url='').exclude(vignette_url__isnull=True).count()
        animated_postcards = Postcard.objects.exclude(animated_url='').exclude(animated_url__isnull=True).count()

        # Engagement stats
        total_likes = PostcardLike.objects.count()
        likes_week = PostcardLike.objects.filter(created_at__date__gte=week_ago).count()
        total_suggestions = AnimationSuggestion.objects.count()
        pending_suggestions = AnimationSuggestion.objects.filter(status='pending').count()

        # Search stats
        total_searches = SearchLog.objects.count()
        today_searches = SearchLog.objects.filter(created_at__date=today).count()
        week_searches = SearchLog.objects.filter(created_at__date__gte=week_ago).count()

        # Page views
        total_views = PageView.objects.count()
        today_views = PageView.objects.filter(timestamp__date=today).count()
        week_views = PageView.objects.filter(timestamp__date__gte=week_ago).count()

        # Top content
        top_postcards = Postcard.objects.order_by('-views_count')[:10]
        top_liked = Postcard.objects.order_by('-likes_count')[:10]
        top_searches = SearchLog.objects.values('keyword').annotate(
            count=Count('id')
        ).order_by('-count')[:10]

        # Recent activity
        recent_users = CustomUser.objects.order_by('-date_joined')[:10]
        recent_searches = SearchLog.objects.order_by('-created_at')[:15]
        recent_messages = ContactMessage.objects.order_by('-created_at')[:10]
        recent_suggestions = AnimationSuggestion.objects.order_by('-created_at')[:10]
        recent_likes = PostcardLike.objects.order_by('-created_at')[:20]

        # User categories breakdown
        user_categories = {
            'unverified': CustomUser.objects.filter(category='subscribed_unverified').count(),
            'verified': CustomUser.objects.filter(category='subscribed_verified').count(),
            'postman': CustomUser.objects.filter(category='postman').count(),
            'viewer': CustomUser.objects.filter(category='viewer').count(),
            'staff': CustomUser.objects.filter(is_staff=True).count(),
        }

        # Daily stats for charts (last 14 days)
        daily_stats = []
        for i in range(14):
            date = today - timedelta(days=13 - i)
            daily_stats.append({
                'date': date.strftime('%d/%m'),
                'views': PageView.objects.filter(timestamp__date=date).count(),
                'searches': SearchLog.objects.filter(created_at__date=date).count(),
                'likes': PostcardLike.objects.filter(created_at__date=date).count(),
                'users': CustomUser.objects.filter(date_joined__date=date).count(),
            })

        context = {
            # Basic counts
            'total_users': total_users,
            'new_users_week': new_users_week,
            'new_users_month': new_users_month,
            'total_postcards': total_postcards,
            'postcards_with_images': postcards_with_images,
            'animated_postcards': animated_postcards,
            'total_themes': Theme.objects.count(),

            # Engagement
            'total_likes': total_likes,
            'likes_week': likes_week,
            'total_suggestions': total_suggestions,
            'pending_suggestions': pending_suggestions,

            # Messages
            'total_messages': ContactMessage.objects.count(),
            'unread_messages': ContactMessage.objects.filter(is_read=False).count(),

            # Searches
            'total_searches': total_searches,
            'today_searches': today_searches,
            'week_searches': week_searches,

            # Views
            'total_views': total_views,
            'today_views': today_views,
            'week_views': week_views,

            # Top content
            'top_postcards': top_postcards,
            'top_liked': top_liked,
            'top_searches': top_searches,

            # Recent activity
            'recent_users': recent_users,
            'recent_searches': recent_searches,
            'recent_messages': recent_messages,
            'recent_suggestions': recent_suggestions,
            'recent_likes': recent_likes,

            # Categories
            'user_categories': user_categories,
            'user_categories_choices': CustomUser.USER_CATEGORIES,

            # Charts data
            'daily_stats': json.dumps(daily_stats),
        }

        return render(request, 'admin_dashboard.html', context)

    except Exception as e:
        return HttpResponse(f"<h1>Admin Error</h1><pre>{traceback.format_exc()}</pre>")


@user_passes_test(is_admin)
def admin_stats_api(request):
    """API for dashboard statistics"""
    try:
        today = timezone.now().date()

        # Get daily views for last 14 days
        daily_views = []
        for i in range(14):
            date = today - timedelta(days=13 - i)
            count = PageView.objects.filter(timestamp__date=date).count()
            daily_views.append({
                'date': date.strftime('%d/%m'),
                'count': count
            })

        # Get daily searches
        daily_searches = []
        for i in range(14):
            date = today - timedelta(days=13 - i)
            count = SearchLog.objects.filter(created_at__date=date).count()
            daily_searches.append({
                'date': date.strftime('%d/%m'),
                'count': count
            })

        # Get daily likes
        daily_likes = []
        for i in range(14):
            date = today - timedelta(days=13 - i)
            count = PostcardLike.objects.filter(created_at__date=date).count()
            daily_likes.append({
                'date': date.strftime('%d/%m'),
                'count': count
            })

        # Top search terms
        top_searches = SearchLog.objects.values('keyword').annotate(
            count=Count('id')
        ).order_by('-count')[:10]

        # Hourly distribution (today)
        hourly_views = []
        for hour in range(24):
            count = PageView.objects.filter(
                timestamp__date=today,
                timestamp__hour=hour
            ).count()
            hourly_views.append({
                'hour': f'{hour:02d}:00',
                'count': count
            })

        return JsonResponse({
            'daily_views': daily_views,
            'daily_searches': daily_searches,
            'daily_likes': daily_likes,
            'hourly_views': hourly_views,
            'top_searches': list(top_searches),
            'total_users': CustomUser.objects.count(),
            'total_postcards': Postcard.objects.count(),
            'total_likes': PostcardLike.objects.count(),
            'animated_count': Postcard.objects.exclude(animated_url='').count(),
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
            'likes_count': p.likes_count,
            'has_vignette': bool(p.vignette_url),
            'has_grande': bool(p.grande_url),
            'has_dos': bool(p.dos_url),
            'has_zoom': bool(p.zoom_url),
            'has_animated': bool(p.animated_url),
            'animated_count': len(p.get_animated_urls()),
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
                'animated_url': postcard.animated_url,
                'animated_urls': postcard.get_animated_urls(),
                'views_count': postcard.views_count,
                'zoom_count': postcard.zoom_count,
                'likes_count': postcard.likes_count,
            })

        elif request.method == 'PUT':
            data = json.loads(request.body)

            for field in ['number', 'title', 'description', 'keywords', 'rarity',
                          'vignette_url', 'grande_url', 'dos_url', 'zoom_url', 'animated_url']:
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


@user_passes_test(is_admin)
def admin_suggestions_api(request):
    """API for animation suggestions management"""
    if request.method == 'GET':
        suggestions = AnimationSuggestion.objects.all().order_by('-created_at')[:50]
        data = [{
            'id': s.id,
            'postcard_number': s.postcard.number,
            'postcard_title': s.postcard.title[:30],
            'description': s.description[:100],
            'status': s.status,
            'user': s.user.username if s.user else 'Anonyme',
            'created_at': s.created_at.strftime('%d/%m/%Y %H:%M'),
        } for s in suggestions]
        return JsonResponse({'suggestions': data})

    return JsonResponse({'error': 'Method not allowed'}, status=405)


@user_passes_test(is_admin)
@require_http_methods(["PUT"])
def admin_suggestion_detail(request, suggestion_id):
    """Update suggestion status"""
    try:
        suggestion = AnimationSuggestion.objects.get(id=suggestion_id)
        data = json.loads(request.body)

        if 'status' in data:
            suggestion.status = data['status']
            suggestion.reviewed_at = timezone.now()
            suggestion.reviewed_by = request.user
            suggestion.save()

        return JsonResponse({'success': True})
    except AnimationSuggestion.DoesNotExist:
        return JsonResponse({'error': 'Not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# Legacy compatibility
def update_user_category(request, user_id):
    return admin_user_detail(request, user_id)


def delete_user(request, user_id):
    return admin_user_detail(request, user_id)


# Image serving (keep from original)
def serve_postcard_image(request, image_type, number):
    """Serve postcard image - proxy to OVH"""
    from django.http import Http404
    import hashlib

    valid_types = ['vignette', 'grande', 'dos', 'zoom']
    image_type = image_type.lower()

    if image_type not in valid_types:
        raise Http404("Invalid image type")

    number = ''.join(filter(str.isdigit, str(number).split('.')[0]))
    if not number:
        raise Http404("Invalid number")

    # Redirect to OVH directly
    from django.shortcuts import redirect
    base_url = 'https://collections.samathey.fr/cartes'
    folder_map = {
        'vignette': 'Vignette',
        'grande': 'Grande',
        'dos': 'Dos',
        'zoom': 'Zoom',
    }

    num_padded = number.zfill(6)
    url = f"{base_url}/{folder_map[image_type]}/{num_padded}.jpg"

    return redirect(url)


def check_ftp_images(request):
    """Admin view to check images"""
    if not request.user.is_staff:
        from django.http import Http404
        raise Http404()

    return JsonResponse({'message': 'Check FTP images endpoint'})


@user_passes_test(is_admin)
def admin_next_postcard_number(request):
    """Get the next available postcard number"""
    try:
        # Get the highest number
        last_postcard = Postcard.objects.order_by('-number').first()

        if last_postcard:
            # Extract numeric part and increment
            num_str = ''.join(filter(str.isdigit, str(last_postcard.number)))
            if num_str:
                next_num = int(num_str) + 1
            else:
                next_num = 1
        else:
            next_num = 1

        return JsonResponse({
            'next_number': next_num,
            'formatted': str(next_num).zfill(6)
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
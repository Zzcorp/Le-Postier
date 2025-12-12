# core/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Q, Count
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from datetime import timedelta
import traceback
import json

from .models import (
    CustomUser, Postcard, PostcardLike, AnimationSuggestion, Theme,
    ContactMessage, SearchLog, PageView, UserActivity, SystemLog, IntroSeen,
    SentPostcard, PostcardComment
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

    if request.user.is_authenticated:
        if request.user.last_intro_seen == today:
            return False
        return True

    if not request.session.session_key:
        request.session.create()

    session_key = request.session.session_key
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
    redirect_url = request.GET.get('next', '/')
    return render(request, 'intro.html', {'redirect_url': redirect_url})


def home(request):
    """Home page view"""
    try:
        if should_show_intro(request):
            return redirect(f'/intro/?next=/')

        # Get animated postcards for background video
        all_videos = []
        for postcard in Postcard.objects.all()[:100]:
            urls = postcard.get_animated_urls()
            all_videos.extend(urls)
            if len(all_videos) >= 50:
                break

        return render(request, 'home.html', {
            'animated_videos': all_videos[:50]
        })
    except Exception as e:
        return HttpResponse(f"<h1>Home Error</h1><pre>{traceback.format_exc()}</pre>")


def browse(request):
    """Browse page - search and display postcards"""
    try:
        query = request.GET.get('keywords_input', '').strip()

        # Start with all postcards
        postcards = Postcard.objects.all()
        themes = Theme.objects.all()

        # Apply search filter
        if query:
            postcards = postcards.filter(
                Q(title__icontains=query) |
                Q(keywords__icontains=query) |
                Q(number__icontains=query) |
                Q(description__icontains=query)
            )

            # Log search
            SearchLog.objects.create(
                keyword=query,
                results_count=postcards.count(),
                user=request.user if request.user.is_authenticated else None,
                ip_address=get_client_ip(request)
            )

        # Convert to list and filter those with images
        postcards_list = list(postcards[:200])
        postcards_with_images = [p for p in postcards_list if p.has_vignette()]

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
            'total_count': Postcard.objects.count(),
            'displayed_count': min(len(postcards_with_images), 50),
            'slideshow_postcards': postcards_with_images[:20],
            'user': request.user,
            'user_likes': user_likes,
        }

        return render(request, 'browse.html', context)

    except Exception as e:
        return HttpResponse(f"<h1>Browse Error</h1><pre>{traceback.format_exc()}</pre>")


def get_postcard_detail(request, postcard_id):
    """API endpoint for postcard details"""
    try:
        postcard = Postcard.objects.get(id=postcard_id)

        # Increment view count
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

        # Check view permissions for rare cards
        can_view_full = True
        if postcard.rarity == 'very_rare':
            if not request.user.is_authenticated:
                can_view_full = False
            elif hasattr(request.user, 'can_view_very_rare') and not request.user.can_view_very_rare():
                can_view_full = False

        if not can_view_full:
            member_card_url = '/static/images/Carte_Membre_4.jpeg'
            data = {
                'id': postcard.id,
                'number': postcard.number,
                'title': postcard.title,
                'description': 'Carte réservée aux membres',
                'keywords': '',
                'rarity': postcard.rarity,
                'vignette_url': member_card_url,
                'grande_url': member_card_url,
                'dos_url': member_card_url,
                'zoom_url': member_card_url,
                'animated_urls': [],
                'likes_count': postcard.likes_count,
                'has_liked': has_liked,
                'is_restricted': True,
            }
        else:
            data = {
                'id': postcard.id,
                'number': postcard.number,
                'title': postcard.title,
                'description': postcard.description,
                'keywords': postcard.keywords,
                'rarity': postcard.rarity,
                'vignette_url': postcard.get_vignette_url(),
                'grande_url': postcard.get_grande_url(),
                'dos_url': postcard.get_dos_url(),
                'zoom_url': postcard.get_zoom_url(),
                'animated_urls': postcard.get_animated_urls(),
                'likes_count': postcard.likes_count,
                'has_liked': has_liked,
                'is_restricted': False,
            }

        return JsonResponse(data)

    except Postcard.DoesNotExist:
        return JsonResponse({'error': 'Not found'}, status=404)


def animated_gallery(request):
    """Animated postcards gallery page"""
    try:
        # Get all postcards and filter those with animations
        all_postcards = Postcard.objects.all().order_by('-likes_count', 'number')
        animated_postcards = [p for p in all_postcards if p.has_animation()]

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
            'total_count': len(animated_postcards),
        }

        return render(request, 'animated_gallery.html', context)

    except Exception as e:
        return HttpResponse(f"<h1>Animated Gallery Error</h1><pre>{traceback.format_exc()}</pre>")


def gallery(request):
    """Gallery page"""
    try:
        all_postcards = list(Postcard.objects.all().order_by('?')[:100])
        postcards = [p for p in all_postcards if p.has_vignette()][:50]

        return render(request, 'gallery.html', {
            'postcards': postcards,
            'user': request.user,
        })
    except Exception as e:
        return HttpResponse(f"<h1>Gallery Error</h1><pre>{traceback.format_exc()}</pre>")


def presentation(request):
    """Presentation page"""
    return render(request, 'presentation.html')


def decouvrir(request):
    """Découvrir page - 6 paintings with videos"""
    paintings = [
        {
            'title': "Ascenseur de la Terrasse",
            'image_off': '/static/images/decouvrir/Cadre_1_Off.png',
            'image_on': '/static/images/decouvrir/Cadre_1_Clic.png',
            'video_id': '2hD8sSnelHs',
        },
        {
            'title': "Accident de l'archevêché",
            'image_off': '/static/images/decouvrir/Cadre_2_Off.png',
            'image_on': '/static/images/decouvrir/Cadre_2_Clic.png',
            'video_id': 'dQw4w9WgXcQ',
        },
        {
            'title': "Bateau « Touriste »",
            'image_off': '/static/images/decouvrir/Cadre_3_Off.png',
            'image_on': '/static/images/decouvrir/Cadre_3_Clic.png',
            'video_id': '6462WnYcRxo',
        },
        {
            'title': "Machine de Marly",
            'image_off': '/static/images/decouvrir/Cadre_4_Off.png',
            'image_on': '/static/images/decouvrir/Cadre_4_Clic.png',
            'video_id': 'h-bLPdvk4BU',
        },
        {
            'title': "Yacht « Le Druide »",
            'image_off': '/static/images/decouvrir/Cadre_5_Off.png',
            'image_on': '/static/images/decouvrir/Cadre_5_Clic.png',
            'video_id': 'J-VMocHfFb8',
        },
        {
            'title': "La Pénichienne",
            'image_off': '/static/images/decouvrir/Cadre_6_Off.png',
            'image_on': '/static/images/decouvrir/Cadre_6_Clic.png',
            'video_id': '0ftXAcvLukY',
        },
    ]
    return render(request, 'decouvrir.html', {'paintings': paintings})


def contact(request):
    """Contact page"""
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


def register(request):
    """Registration page"""
    if request.method == 'POST':
        form = SimpleRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('home')
    else:
        form = SimpleRegistrationForm()

    return render(request, 'register.html', {'form': form})


def login_view(request):
    """Login page"""
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


def logout_view(request):
    """Logout"""
    logout(request)
    return redirect('home')


@login_required
def profile(request):
    """User profile page"""
    return render(request, 'profile.html', {'user': request.user})


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
            'zoom_url': postcard.get_zoom_url() if can_view else '',
            'grande_url': postcard.get_grande_url() if can_view else '',
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
            existing_like.delete()
            postcard.likes_count = max(0, postcard.likes_count - 1)
            postcard.save(update_fields=['likes_count'])
            liked = False
        else:
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

        AnimationSuggestion.objects.create(
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
    """Custom admin dashboard"""
    try:
        today = timezone.now().date()
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)

        # User stats
        total_users = CustomUser.objects.count()
        new_users_week = CustomUser.objects.filter(date_joined__date__gte=week_ago).count()
        new_users_month = CustomUser.objects.filter(date_joined__date__gte=month_ago).count()

        # Postcard stats
        total_postcards = Postcard.objects.count()

        # Sample postcards for image/animation counts
        all_postcards = list(Postcard.objects.all()[:500])
        postcards_with_images = sum(1 for p in all_postcards if p.has_vignette())
        animated_postcards = sum(1 for p in all_postcards if p.has_animation())

        # Engagement stats
        total_likes = PostcardLike.objects.count()
        likes_week = PostcardLike.objects.filter(created_at__date__gte=week_ago).count()
        total_suggestions = AnimationSuggestion.objects.count()
        pending_suggestions = AnimationSuggestion.objects.filter(status='pending').count()

        # Search stats
        total_searches = SearchLog.objects.count()
        today_searches = SearchLog.objects.filter(created_at__date=today).count()
        week_searches = SearchLog.objects.filter(created_at__date__gte=week_ago).count()

        # Page view stats
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

        # User categories
        user_categories = {
            'unverified': CustomUser.objects.filter(category='subscribed_unverified').count(),
            'verified': CustomUser.objects.filter(category='subscribed_verified').count(),
            'postman': CustomUser.objects.filter(category='postman').count(),
            'viewer': CustomUser.objects.filter(category='viewer').count(),
            'staff': CustomUser.objects.filter(is_staff=True).count(),
        }

        # Daily stats for chart
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
            'total_users': total_users,
            'new_users_week': new_users_week,
            'new_users_month': new_users_month,
            'total_postcards': total_postcards,
            'postcards_with_images': postcards_with_images,
            'animated_postcards': animated_postcards,
            'total_themes': Theme.objects.count(),
            'total_likes': total_likes,
            'likes_week': likes_week,
            'total_suggestions': total_suggestions,
            'pending_suggestions': pending_suggestions,
            'total_messages': ContactMessage.objects.count(),
            'unread_messages': ContactMessage.objects.filter(is_read=False).count(),
            'total_searches': total_searches,
            'today_searches': today_searches,
            'week_searches': week_searches,
            'total_views': total_views,
            'today_views': today_views,
            'week_views': week_views,
            'top_postcards': top_postcards,
            'top_liked': top_liked,
            'top_searches': top_searches,
            'recent_users': recent_users,
            'recent_searches': recent_searches,
            'recent_messages': recent_messages,
            'recent_suggestions': recent_suggestions,
            'recent_likes': recent_likes,
            'user_categories': user_categories,
            'user_categories_choices': CustomUser.USER_CATEGORIES,
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

        # Daily views
        daily_views = []
        for i in range(14):
            date = today - timedelta(days=13 - i)
            count = PageView.objects.filter(timestamp__date=date).count()
            daily_views.append({'date': date.strftime('%d/%m'), 'count': count})

        # Daily searches
        daily_searches = []
        for i in range(14):
            date = today - timedelta(days=13 - i)
            count = SearchLog.objects.filter(created_at__date=date).count()
            daily_searches.append({'date': date.strftime('%d/%m'), 'count': count})

        # Count animated postcards
        all_postcards = list(Postcard.objects.all()[:500])
        animated_count = sum(1 for p in all_postcards if p.has_animation())

        return JsonResponse({
            'daily_views': daily_views,
            'daily_searches': daily_searches,
            'total_users': CustomUser.objects.count(),
            'total_postcards': Postcard.objects.count(),
            'total_likes': PostcardLike.objects.count(),
            'animated_count': animated_count,
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
            'has_vignette': p.has_vignette(),
            'has_grande': bool(p.get_grande_url()),
            'has_dos': bool(p.get_dos_url()),
            'has_zoom': bool(p.get_zoom_url()),
            'has_animated': p.has_animation(),
            'animated_count': p.video_count(),
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
                'vignette_url': postcard.get_vignette_url(),
                'grande_url': postcard.get_grande_url(),
                'dos_url': postcard.get_dos_url(),
                'zoom_url': postcard.get_zoom_url(),
                'animated_urls': postcard.get_animated_urls(),
                'views_count': postcard.views_count,
                'zoom_count': postcard.zoom_count,
                'likes_count': postcard.likes_count,
            })

        elif request.method == 'PUT':
            data = json.loads(request.body)
            for field in ['number', 'title', 'description', 'keywords', 'rarity']:
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


def update_user_category(request, user_id):
    """Legacy endpoint"""
    return admin_user_detail(request, user_id)


def delete_user(request, user_id):
    """Legacy endpoint"""
    return admin_user_detail(request, user_id)


@user_passes_test(is_admin)
def admin_next_postcard_number(request):
    """Get the next available postcard number"""
    try:
        last_postcard = Postcard.objects.order_by('-number').first()
        if last_postcard:
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


# ============================================
# LA POSTE - SOCIAL HUB VIEWS
# ============================================

@login_required
def la_poste(request):
    """La Poste - Social hub for sending postcards"""
    received = SentPostcard.objects.filter(
        recipient=request.user
    ).select_related('sender', 'postcard')[:20]

    sent = SentPostcard.objects.filter(
        sender=request.user
    ).select_related('recipient', 'postcard')[:20]

    public_postcards = SentPostcard.objects.filter(
        visibility='public'
    ).select_related('sender', 'postcard').prefetch_related('comments')[:30]

    unread_count = SentPostcard.objects.filter(
        recipient=request.user,
        is_read=False
    ).count()

    # Get postcards with images for selection
    all_postcards = list(Postcard.objects.all()[:100])
    available_postcards = [p for p in all_postcards if p.has_vignette()][:50]

    context = {
        'received_postcards': received,
        'sent_postcards': sent,
        'public_postcards': public_postcards,
        'unread_count': unread_count,
        'available_postcards': available_postcards,
    }

    return render(request, 'la_poste.html', context)


@login_required
@require_http_methods(["POST"])
def send_postcard(request):
    """Send a postcard to another user or post publicly"""
    try:
        data = json.loads(request.body)

        message = data.get('message', '').strip()
        if not message or len(message) < 5:
            return JsonResponse({'error': 'Message trop court (min 5 caractères)'}, status=400)

        visibility = data.get('visibility', 'private')
        recipient_username = data.get('recipient')
        postcard_id = data.get('postcard_id')

        recipient = None
        if visibility == 'private':
            if not recipient_username:
                return JsonResponse({'error': 'Destinataire requis pour un envoi privé'}, status=400)
            try:
                recipient = CustomUser.objects.get(username=recipient_username)
            except CustomUser.DoesNotExist:
                return JsonResponse({'error': 'Utilisateur non trouvé'}, status=404)

            if recipient == request.user:
                return JsonResponse({'error': 'Vous ne pouvez pas vous envoyer une carte'}, status=400)

        postcard = None
        if postcard_id:
            try:
                postcard = Postcard.objects.get(id=postcard_id)
            except Postcard.DoesNotExist:
                pass

        sent_postcard = SentPostcard.objects.create(
            sender=request.user,
            recipient=recipient,
            postcard=postcard,
            message=message,
            visibility=visibility
        )

        return JsonResponse({
            'success': True,
            'postcard_id': sent_postcard.id,
            'message': 'Carte postale envoyée!' if visibility == 'private' else 'Carte publiée!'
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
def get_user_postcards(request):
    """Get user's received and sent postcards"""
    tab = request.GET.get('tab', 'received')

    if tab == 'received':
        postcards = SentPostcard.objects.filter(
            recipient=request.user
        ).select_related('sender', 'postcard')
    else:
        postcards = SentPostcard.objects.filter(
            sender=request.user
        ).select_related('recipient', 'postcard')

    data = [{
        'id': p.id,
        'sender': p.sender.username,
        'sender_signature': p.sender.signature_image.url if p.sender.signature_image else None,
        'recipient': p.recipient.username if p.recipient else None,
        'message': p.message,
        'image_url': p.get_image_url(),
        'postcard_title': p.postcard.title if p.postcard else None,
        'visibility': p.visibility,
        'is_read': p.is_read,
        'created_at': p.created_at.strftime('%d/%m/%Y %H:%M'),
    } for p in postcards[:50]]

    return JsonResponse({'postcards': data})


@login_required
def get_public_postcards(request):
    """Get public postcards (wall)"""
    postcards = SentPostcard.objects.filter(
        visibility='public'
    ).select_related('sender', 'postcard').prefetch_related(
        'comments', 'comments__user'
    )[:50]

    data = [{
        'id': p.id,
        'sender': p.sender.username,
        'sender_signature': p.sender.signature_image.url if p.sender.signature_image else None,
        'message': p.message,
        'image_url': p.get_image_url(),
        'postcard_title': p.postcard.title if p.postcard else None,
        'created_at': p.created_at.strftime('%d/%m/%Y %H:%M'),
        'comments': [{
            'user': c.user.username,
            'message': c.message,
            'created_at': c.created_at.strftime('%d/%m/%Y %H:%M'),
        } for c in p.comments.all()[:10]],
        'comment_count': p.comments.count(),
    } for p in postcards]

    return JsonResponse({'postcards': data})


@login_required
@require_http_methods(["POST"])
def mark_postcard_read(request, postcard_id):
    """Mark a received postcard as read"""
    try:
        postcard = SentPostcard.objects.get(id=postcard_id, recipient=request.user)
        postcard.is_read = True
        postcard.save(update_fields=['is_read'])
        return JsonResponse({'success': True})
    except SentPostcard.DoesNotExist:
        return JsonResponse({'error': 'Not found'}, status=404)


@login_required
@require_http_methods(["POST"])
def add_comment(request, postcard_id):
    """Add comment to a public postcard"""
    try:
        postcard = SentPostcard.objects.get(id=postcard_id, visibility='public')
        data = json.loads(request.body)
        message = data.get('message', '').strip()

        if not message or len(message) < 2:
            return JsonResponse({'error': 'Commentaire trop court'}, status=400)

        comment = PostcardComment.objects.create(
            sent_postcard=postcard,
            user=request.user,
            message=message
        )

        return JsonResponse({
            'success': True,
            'comment': {
                'user': comment.user.username,
                'message': comment.message,
                'created_at': comment.created_at.strftime('%d/%m/%Y %H:%M'),
            }
        })
    except SentPostcard.DoesNotExist:
        return JsonResponse({'error': 'Not found'}, status=404)


@login_required
def search_users(request):
    """Search users for autocomplete"""
    query = request.GET.get('q', '').strip()

    if len(query) < 2:
        return JsonResponse({'users': []})

    users = CustomUser.objects.filter(
        username__icontains=query
    ).exclude(
        id=request.user.id
    ).values('username', 'category')[:10]

    return JsonResponse({'users': list(users)})


@login_required
@require_http_methods(["POST"])
def update_profile(request):
    """Update user profile"""
    try:
        data = json.loads(request.body)

        if 'bio' in data:
            request.user.bio = data['bio'][:500]
            request.user.save(update_fields=['bio'])

        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@require_http_methods(["POST"])
def upload_signature(request):
    """Upload user signature image"""
    try:
        if 'signature' not in request.FILES:
            return JsonResponse({'error': 'No file provided'}, status=400)

        file = request.FILES['signature']

        if file.size > 2 * 1024 * 1024:
            return JsonResponse({'error': 'File too large'}, status=400)

        if not file.content_type.startswith('image/'):
            return JsonResponse({'error': 'Invalid file type'}, status=400)

        request.user.signature_image = file
        request.user.save(update_fields=['signature_image'])

        return JsonResponse({
            'success': True,
            'url': request.user.signature_image.url
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)
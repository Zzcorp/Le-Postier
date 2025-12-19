# core/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from datetime import timedelta
import traceback
import json
from django.db.models import Sum, Avg, F, Q, Count
from django.db.models.functions import TruncDate, TruncHour
from collections import defaultdict

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
    """Home page view - OPTIMIZED: Only pass video URLs, don't preload"""
    try:
        if should_show_intro(request):
            return redirect(f'/intro/?next=/')

        # Get only a small batch of video URLs for the carousel
        # Don't load all videos - just get URLs and let JS handle lazy loading
        video_urls = []

        # Quick query to get postcards with animations (limit to 20)
        postcards_with_videos = Postcard.objects.filter(
            has_images=True
        ).order_by('?')[:30]  # Random 30 for variety

        for postcard in postcards_with_videos:
            urls = postcard.get_animated_urls()
            if urls:
                video_urls.append(urls[0])  # Only first video per postcard
                if len(video_urls) >= 15:  # Limit to 15 videos max
                    break

        return render(request, 'home.html', {
            'animated_videos': video_urls[:15]
        })
    except Exception as e:
        return HttpResponse(f"<h1>Home Error</h1><pre>{traceback.format_exc()}</pre>")


def browse(request):
    """Browse page - OPTIMIZED: Removed heavy operations"""
    import unicodedata

    def remove_accents(text):
        """Remove accents from text for comparison"""
        if not text:
            return text
        normalized = unicodedata.normalize('NFD', text)
        return ''.join(char for char in normalized if unicodedata.category(char) != 'Mn')

    try:
        query = request.GET.get('keywords_input', '').strip()

        # Start with all postcards that have images (faster filter)
        postcards = Postcard.objects.filter(has_images=True)
        themes = Theme.objects.all()[:20]  # Limit themes

        # Apply search filter
        if query:
            normalized_query = remove_accents(query.lower())
            search_terms = normalized_query.split()

            # Use database filtering first
            broad_q = Q()
            for term in search_terms:
                term_q = (
                        Q(title__icontains=term) |
                        Q(keywords__icontains=term) |
                        Q(number__icontains=term)
                )
                broad_q |= term_q

            for term in query.split():
                term_q = (
                        Q(title__icontains=term) |
                        Q(keywords__icontains=term) |
                        Q(number__icontains=term)
                )
                broad_q |= term_q

            postcards = postcards.filter(broad_q).distinct()

            # Log search
            SearchLog.objects.create(
                keyword=query,
                results_count=postcards.count(),
                user=request.user if request.user.is_authenticated else None,
                ip_address=get_client_ip(request)
            )

        # Order and limit - DON'T iterate through all
        postcards = postcards.order_by('number')[:100]

        # Get user's likes efficiently
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
            'postcards': postcards,
            'themes': themes,
            'query': query,
            'total_count': Postcard.objects.count(),
            'displayed_count': postcards.count(),
            'user': request.user,
            'user_likes': user_likes,
        }

        return render(request, 'browse.html', context)

    except Exception as e:
        import traceback
        return HttpResponse(f"<h1>Browse Error</h1><pre>{traceback.format_exc()}</pre>")


def animated_gallery(request):
    """Animated postcards gallery page"""
    try:
        # Get all postcards that have animations
        all_postcards = Postcard.objects.all().order_by('-likes_count', 'number')

        # Filter to only those with actual animation files
        animated_postcards = []
        for postcard in all_postcards:
            video_urls = postcard.get_animated_urls()
            if video_urls:  # This checks for actual files
                # Add video_count attribute for template
                postcard.video_count = len(video_urls)
                animated_postcards.append(postcard)
                if len(animated_postcards) >= 100:  # Limit for performance
                    break

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
        import traceback
        return HttpResponse(f"<h1>Animated Gallery Error</h1><pre>{traceback.format_exc()}</pre>")


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

        # Check view permissions for VERY RARE cards only
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
                'description': 'Cette carte très rare est réservée aux membres privilégiés',
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


def gallery(request):
    """Gallery page"""
    try:
        all_postcards = list(Postcard.objects.filter(has_images=True).order_by('?')[:50])
        return render(request, 'gallery.html', {
            'postcards': all_postcards,
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
    """Contact page with email sending"""
    from django.core.mail import send_mail
    from django.conf import settings

    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            message = form.save(commit=False)
            if request.user.is_authenticated:
                message.user = request.user
            message.ip_address = get_client_ip(request)
            message.save()

            # Send email notification
            try:
                user_info = ""
                if request.user.is_authenticated:
                    user_info = f"\n\nUtilisateur: {request.user.username} ({request.user.email})"
                else:
                    user_info = "\n\nUtilisateur: Anonyme"

                email_body = f"""Nouveau message de contact sur Le Postier:

{message.message}
{user_info}
IP: {message.ip_address}
Date: {message.created_at.strftime('%d/%m/%Y %H:%M')}

---
Ce message a été envoyé depuis le formulaire de contact du site Le Postier.
"""

                send_mail(
                    subject='[Le Postier] Nouveau message de contact',
                    message=email_body,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=['sam@samathey.com'],
                    fail_silently=True,
                )
            except Exception as e:
                print(f"Email sending failed: {e}")

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
        postcards_with_images = Postcard.objects.filter(has_images=True).count()

        # Approximate animated count (don't check files)
        animated_postcards = postcards_with_images // 10  # Rough estimate

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

        daily_views = []
        for i in range(14):
            date = today - timedelta(days=13 - i)
            count = PageView.objects.filter(timestamp__date=date).count()
            daily_views.append({'date': date.strftime('%d/%m'), 'count': count})

        daily_searches = []
        for i in range(14):
            date = today - timedelta(days=13 - i)
            count = SearchLog.objects.filter(created_at__date=date).count()
            daily_searches.append({'date': date.strftime('%d/%m'), 'count': count})

        return JsonResponse({
            'daily_views': daily_views,
            'daily_searches': daily_searches,
            'total_users': CustomUser.objects.count(),
            'total_postcards': Postcard.objects.count(),
            'total_likes': PostcardLike.objects.count(),
            'animated_count': Postcard.objects.filter(has_images=True).count() // 10,
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
            'has_vignette': p.has_images,
            'has_grande': p.has_images,
            'has_dos': False,
            'has_zoom': False,
            'has_animated': False,
            'animated_count': 0,
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

    # Get postcards with images for selection - simplified
    available_postcards = Postcard.objects.filter(has_images=True)[:50]

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


@user_passes_test(is_admin)
@require_http_methods(["POST"])
def admin_upload_media(request):
    """Admin endpoint to upload media files."""
    from django.conf import settings
    from pathlib import Path

    if 'file' not in request.FILES:
        return JsonResponse({'error': 'No file provided'}, status=400)

    file = request.FILES['file']
    folder = request.POST.get('folder', 'Vignette')

    valid_folders = ['Vignette', 'Grande', 'Dos', 'Zoom', 'animated_cp']
    if folder not in valid_folders:
        return JsonResponse({'error': f'Invalid folder: {folder}'}, status=400)

    media_root = Path(settings.MEDIA_ROOT)
    if folder == 'animated_cp':
        dest_dir = media_root / 'animated_cp'
    else:
        dest_dir = media_root / 'postcards' / folder

    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = dest_dir / file.name

    try:
        with open(dest_path, 'wb+') as destination:
            for chunk in file.chunks():
                destination.write(chunk)

        return JsonResponse({
            'success': True,
            'filename': file.name,
            'path': str(dest_path)
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@user_passes_test(is_admin)
def admin_media_stats(request):
    """Get media storage statistics."""
    from django.conf import settings
    from pathlib import Path
    import os

    media_root = Path(settings.MEDIA_ROOT)

    stats = {
        'media_root': str(media_root),
        'exists': media_root.exists(),
        'folders': {}
    }

    if media_root.exists():
        for folder in ['Vignette', 'Grande', 'Dos', 'Zoom']:
            folder_path = media_root / 'postcards' / folder
            if folder_path.exists():
                count = len(list(folder_path.glob('*.*')))
                stats['folders'][folder] = count
            else:
                stats['folders'][folder] = 0

        animated_path = media_root / 'animated_cp'
        if animated_path.exists():
            stats['folders']['animated_cp'] = len(list(animated_path.glob('*.*')))
        else:
            stats['folders']['animated_cp'] = 0

        total_size = 0
        for root, dirs, files in os.walk(media_root):
            for f in files:
                total_size += os.path.getsize(os.path.join(root, f))

        stats['total_size_mb'] = round(total_size / (1024 * 1024), 2)

    return JsonResponse(stats)


@user_passes_test(is_admin)
def debug_postcard_images(request, postcard_id):
    """Debug endpoint to check image paths for a postcard"""
    try:
        from django.conf import settings
        postcard = Postcard.objects.get(id=postcard_id)
        debug_info = {
            'postcard': {
                'id': postcard.id,
                'number': postcard.number,
                'padded_number': postcard.get_padded_number(),
            },
            'urls': {
                'vignette': postcard.get_vignette_url(),
                'grande': postcard.get_grande_url(),
                'dos': postcard.get_dos_url(),
                'zoom': postcard.get_zoom_url(),
                'animated': postcard.get_animated_urls(),
            },
            'settings': {
                'MEDIA_ROOT': str(settings.MEDIA_ROOT),
                'MEDIA_URL': settings.MEDIA_URL,
            }
        }
        return JsonResponse(debug_info, json_dumps_params={'indent': 2})
    except Postcard.DoesNotExist:
        return JsonResponse({'error': 'Postcard not found'}, status=404)


def debug_browse(request):
    """Debug view to check postcard images"""
    from django.conf import settings
    from pathlib import Path

    output = []
    output.append(f"MEDIA_ROOT: {settings.MEDIA_ROOT}")
    output.append(f"MEDIA_URL: {settings.MEDIA_URL}")
    output.append("")

    media_root = Path(settings.MEDIA_ROOT)
    for folder in ['Vignette', 'Grande', 'Dos', 'Zoom']:
        folder_path = media_root / 'postcards' / folder
        if folder_path.exists():
            files = list(folder_path.glob('*.*'))
            output.append(f"{folder}: {len(files)} files")
            if files[:3]:
                output.append(f"  Sample: {', '.join(f.name for f in files[:3])}")
        else:
            output.append(f"{folder}: NOT FOUND")

    output.append("")

    total = Postcard.objects.count()
    output.append(f"Database: {total} postcards")

    postcards = Postcard.objects.all()[:5]
    for p in postcards:
        vignette = p.get_vignette_url()
        output.append(f"  {p.number}: vignette={vignette or 'NOT FOUND'}")

    return HttpResponse("<pre>" + "\n".join(output) + "</pre>")


def debug_media(request):
    """Debug view to check media configuration"""
    from django.conf import settings
    from pathlib import Path
    import os

    is_render = os.environ.get('RENDER', 'false').lower() == 'true'
    persistent_exists = Path('/var/data').exists()

    if is_render or persistent_exists:
        actual_media_root = Path('/var/data/media')
    else:
        actual_media_root = Path(settings.MEDIA_ROOT)

    output = []
    output.append("=" * 60)
    output.append("MEDIA DEBUG INFO")
    output.append("=" * 60)
    output.append("")
    output.append(f"RENDER env: {os.environ.get('RENDER', 'not set')}")
    output.append(f"/var/data exists: {persistent_exists}")
    output.append(f"settings.MEDIA_ROOT: {settings.MEDIA_ROOT}")
    output.append(f"Actual MEDIA_ROOT used: {actual_media_root}")
    output.append(f"MEDIA_URL: {settings.MEDIA_URL}")
    output.append(f"Media root exists: {actual_media_root.exists()}")
    output.append("")

    for folder in ['Vignette', 'Grande', 'Dos', 'Zoom']:
        folder_path = actual_media_root / 'postcards' / folder
        if folder_path.exists():
            files = list(folder_path.glob('*.*'))
            output.append(f"{folder}: {len(files)} files")
            if files[:3]:
                output.append(f"  Sample: {', '.join(f.name for f in files[:3])}")
        else:
            output.append(f"{folder}: NOT FOUND at {folder_path}")

    animated_path = actual_media_root / 'animated_cp'
    if animated_path.exists():
        files = list(animated_path.glob('*.*'))
        output.append(f"animated_cp: {len(files)} files")
    else:
        output.append(f"animated_cp: NOT FOUND at {animated_path}")

    output.append("")

    from core.models import Postcard
    total = Postcard.objects.count()
    with_images = Postcard.objects.filter(has_images=True).count()
    output.append(f"Database: {total} postcards, {with_images} with images")

    if total > 0:
        sample = Postcard.objects.first()
        output.append("")
        output.append(f"Sample postcard #{sample.number}:")
        output.append(f"  get_vignette_url(): {sample.get_vignette_url() or 'NOT FOUND'}")
        output.append(f"  get_grande_url(): {sample.get_grande_url() or 'NOT FOUND'}")
        output.append(f"  get_animated_urls(): {sample.get_animated_urls()}")

    output.append("")
    output.append("=" * 60)

    return HttpResponse("<pre>" + "\n".join(output) + "</pre>", content_type="text/plain")


# Add these imports at the top of core/views.py
from django.db.models import Sum, Avg, F, Q, Count
from django.db.models.functions import TruncDate, TruncHour
from collections import defaultdict


# Add these new admin views

@user_passes_test(is_admin)
def admin_dashboard(request):
    """Enhanced custom admin dashboard with comprehensive analytics"""
    try:
        today = timezone.now().date()
        yesterday = today - timedelta(days=1)
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)

        # Import models
        from .models import (
            CustomUser, Postcard, PostcardLike, AnimationSuggestion, Theme,
            ContactMessage, SearchLog, PageView, UserActivity, VisitorSession,
            RealTimeVisitor, PostcardInteraction, DailyAnalytics, IPLocation
        )

        # ============================================
        # REAL-TIME METRICS
        # ============================================

        # Clean up old real-time visitors first
        five_minutes_ago = timezone.now() - timedelta(minutes=5)
        RealTimeVisitor.objects.filter(last_activity__lt=five_minutes_ago).delete()

        active_visitors = RealTimeVisitor.objects.all()
        active_visitor_count = active_visitors.count()

        active_visitors_list = list(active_visitors.values(
            'ip_address', 'country', 'city', 'current_page',
            'device_type', 'browser', 'last_activity', 'user__username'
        )[:20])

        # ============================================
        # USER STATISTICS
        # ============================================

        total_users = CustomUser.objects.count()
        new_users_today = CustomUser.objects.filter(date_joined__date=today).count()
        new_users_week = CustomUser.objects.filter(date_joined__date__gte=week_ago).count()
        new_users_month = CustomUser.objects.filter(date_joined__date__gte=month_ago).count()

        # User categories breakdown
        user_categories = {
            'unverified': CustomUser.objects.filter(category='subscribed_unverified').count(),
            'verified': CustomUser.objects.filter(category='subscribed_verified').count(),
            'postman': CustomUser.objects.filter(category='postman').count(),
            'viewer': CustomUser.objects.filter(category='viewer').count(),
            'staff': CustomUser.objects.filter(is_staff=True).count(),
        }

        # ============================================
        # POSTCARD STATISTICS
        # ============================================

        total_postcards = Postcard.objects.count()

        # Get postcards with images (sample)
        all_postcards = list(Postcard.objects.all()[:500])
        postcards_with_images = sum(1 for p in all_postcards if p.has_vignette())
        animated_postcards = sum(1 for p in all_postcards if p.has_animation())

        # Top viewed postcards
        top_viewed_postcards = Postcard.objects.order_by('-views_count')[:10]

        # Top liked postcards
        top_liked_postcards = Postcard.objects.order_by('-likes_count')[:10]

        # Most zoomed postcards
        top_zoomed_postcards = Postcard.objects.order_by('-zoom_count')[:10]

        # Recent postcard interactions
        recent_interactions = PostcardInteraction.objects.select_related(
            'postcard', 'user'
        ).order_by('-timestamp')[:50]

        # ============================================
        # ENGAGEMENT METRICS
        # ============================================

        total_likes = PostcardLike.objects.count()
        likes_today = PostcardLike.objects.filter(created_at__date=today).count()
        likes_week = PostcardLike.objects.filter(created_at__date__gte=week_ago).count()

        total_suggestions = AnimationSuggestion.objects.count()
        pending_suggestions = AnimationSuggestion.objects.filter(status='pending').count()

        # ============================================
        # TRAFFIC & VISITOR ANALYTICS
        # ============================================

        # Page views
        total_views = PageView.objects.count()
        views_today = PageView.objects.filter(timestamp__date=today).count()
        views_week = PageView.objects.filter(timestamp__date__gte=week_ago).count()

        # Visitor sessions
        total_sessions = VisitorSession.objects.count()
        sessions_today = VisitorSession.objects.filter(first_visit__date=today).count()
        sessions_week = VisitorSession.objects.filter(first_visit__date__gte=week_ago).count()

        # Unique visitors (by IP)
        unique_visitors_today = VisitorSession.objects.filter(
            first_visit__date=today
        ).values('ip_address').distinct().count()

        unique_visitors_week = VisitorSession.objects.filter(
            first_visit__date__gte=week_ago
        ).values('ip_address').distinct().count()

        # ============================================
        # GEOGRAPHIC DATA
        # ============================================

        # Top countries
        top_countries = list(
            VisitorSession.objects.exclude(country='')
            .exclude(country='Unknown')
            .exclude(country='Local')
            .values('country', 'country_code')
            .annotate(count=Count('id'))
            .order_by('-count')[:15]
        )

        # Top cities
        top_cities = list(
            VisitorSession.objects.exclude(city='')
            .values('city', 'country')
            .annotate(count=Count('id'))
            .order_by('-count')[:15]
        )

        # Country breakdown for today
        countries_today = list(
            VisitorSession.objects.filter(first_visit__date=today)
            .exclude(country='')
            .values('country')
            .annotate(count=Count('id'))
            .order_by('-count')[:10]
        )

        # ============================================
        # DEVICE & BROWSER ANALYTICS
        # ============================================

        # Device types
        device_breakdown = {
            'mobile': VisitorSession.objects.filter(device_type='mobile').count(),
            'tablet': VisitorSession.objects.filter(device_type='tablet').count(),
            'desktop': VisitorSession.objects.filter(device_type='desktop').count(),
            'other': VisitorSession.objects.exclude(
                device_type__in=['mobile', 'tablet', 'desktop']
            ).count(),
        }

        # Top browsers
        top_browsers = list(
            VisitorSession.objects.exclude(browser='')
            .values('browser')
            .annotate(count=Count('id'))
            .order_by('-count')[:10]
        )

        # Top operating systems
        top_os = list(
            VisitorSession.objects.exclude(os='')
            .values('os')
            .annotate(count=Count('id'))
            .order_by('-count')[:10]
        )

        # ============================================
        # TRAFFIC SOURCES
        # ============================================

        # Top referrers
        top_referrers = list(
            VisitorSession.objects.exclude(referrer_domain='')
            .exclude(referrer_domain='direct')
            .values('referrer_domain')
            .annotate(count=Count('id'))
            .order_by('-count')[:15]
        )

        # Direct vs referral traffic
        direct_traffic = VisitorSession.objects.filter(
            Q(referrer_domain='direct') | Q(referrer_domain='')
        ).count()
        referral_traffic = total_sessions - direct_traffic

        # ============================================
        # SEARCH ANALYTICS
        # ============================================

        total_searches = SearchLog.objects.count()
        searches_today = SearchLog.objects.filter(created_at__date=today).count()
        searches_week = SearchLog.objects.filter(created_at__date__gte=week_ago).count()

        # Top searches all time
        top_searches_all = list(
            SearchLog.objects.values('keyword')
            .annotate(count=Count('id'), avg_results=Avg('results_count'))
            .order_by('-count')[:20]
        )

        # Top searches today
        top_searches_today = list(
            SearchLog.objects.filter(created_at__date=today)
            .values('keyword')
            .annotate(count=Count('id'))
            .order_by('-count')[:10]
        )

        # Searches with no results
        zero_result_searches = list(
            SearchLog.objects.filter(results_count=0)
            .values('keyword')
            .annotate(count=Count('id'))
            .order_by('-count')[:10]
        )

        # ============================================
        # MESSAGES & CONTACT
        # ============================================

        total_messages = ContactMessage.objects.count()
        unread_messages = ContactMessage.objects.filter(is_read=False).count()
        messages_today = ContactMessage.objects.filter(created_at__date=today).count()

        recent_messages = ContactMessage.objects.order_by('-created_at')[:10]

        # ============================================
        # IP ADDRESS ANALYSIS
        # ============================================

        # Most active IPs
        most_active_ips = list(
            VisitorSession.objects.exclude(ip_address__isnull=True)
            .values('ip_address', 'country', 'city', 'isp')
            .annotate(
                session_count=Count('id'),
                total_page_views=Sum('page_views')
            )
            .order_by('-session_count')[:20]
        )

        # Suspicious IPs (many sessions, might be bots)
        suspicious_ips = list(
            VisitorSession.objects.exclude(ip_address__isnull=True)
            .values('ip_address', 'country', 'is_bot')
            .annotate(count=Count('id'))
            .filter(count__gt=50)
            .order_by('-count')[:10]
        )

        # VPN/Proxy users
        vpn_proxy_count = IPLocation.objects.filter(
            Q(is_vpn=True) | Q(is_proxy=True)
        ).count()

        # ============================================
        # TIME-BASED ANALYTICS
        # ============================================

        # Hourly traffic today
        hourly_traffic = list(
            PageView.objects.filter(timestamp__date=today)
            .annotate(hour=TruncHour('timestamp'))
            .values('hour')
            .annotate(count=Count('id'))
            .order_by('hour')
        )

        # Daily stats for charts (last 30 days)
        daily_stats = []
        for i in range(30):
            date = today - timedelta(days=29 - i)
            daily_stats.append({
                'date': date.strftime('%d/%m'),
                'full_date': date.strftime('%Y-%m-%d'),
                'views': PageView.objects.filter(timestamp__date=date).count(),
                'sessions': VisitorSession.objects.filter(first_visit__date=date).count(),
                'searches': SearchLog.objects.filter(created_at__date=date).count(),
                'likes': PostcardLike.objects.filter(created_at__date=date).count(),
                'users': CustomUser.objects.filter(date_joined__date=date).count(),
            })

        # Peak hours analysis (last 7 days)
        peak_hours = list(
            PageView.objects.filter(timestamp__date__gte=week_ago)
            .annotate(hour=TruncHour('timestamp'))
            .values('hour')
            .annotate(count=Count('id'))
            .order_by('-count')[:5]
        )

        # ============================================
        # RECENT ACTIVITY FEEDS
        # ============================================

        recent_users = CustomUser.objects.order_by('-date_joined')[:15]
        recent_searches = SearchLog.objects.order_by('-created_at')[:20]
        recent_likes = PostcardLike.objects.select_related('postcard', 'user').order_by('-created_at')[:25]
        recent_suggestions = AnimationSuggestion.objects.select_related('postcard', 'user').order_by('-created_at')[:15]

        # ============================================
        # PERFORMANCE METRICS
        # ============================================

        # Average session duration
        avg_session_duration = VisitorSession.objects.aggregate(
            avg=Avg('total_time_spent')
        )['avg'] or 0

        # Bounce rate (sessions with only 1 page view)
        single_page_sessions = VisitorSession.objects.filter(page_views=1).count()
        bounce_rate = (single_page_sessions / total_sessions * 100) if total_sessions > 0 else 0

        # Pages per session
        pages_per_session = VisitorSession.objects.aggregate(
            avg=Avg('page_views')
        )['avg'] or 0

        # ============================================
        # POSTCARD POPULARITY BREAKDOWN
        # ============================================

        # Postcards by rarity engagement
        rarity_stats = {
            'common': Postcard.objects.filter(rarity='common').aggregate(
                total_views=Sum('views_count'),
                total_likes=Sum('likes_count'),
                total_zooms=Sum('zoom_count')
            ),
            'rare': Postcard.objects.filter(rarity='rare').aggregate(
                total_views=Sum('views_count'),
                total_likes=Sum('likes_count'),
                total_zooms=Sum('zoom_count')
            ),
            'very_rare': Postcard.objects.filter(rarity='very_rare').aggregate(
                total_views=Sum('views_count'),
                total_likes=Sum('likes_count'),
                total_zooms=Sum('zoom_count')
            ),
        }

        context = {
            # Real-time
            'active_visitor_count': active_visitor_count,
            'active_visitors_list': active_visitors_list,

            # Users
            'total_users': total_users,
            'new_users_today': new_users_today,
            'new_users_week': new_users_week,
            'new_users_month': new_users_month,
            'user_categories': user_categories,
            'user_categories_choices': CustomUser.USER_CATEGORIES,
            'recent_users': recent_users,

            # Postcards
            'total_postcards': total_postcards,
            'postcards_with_images': postcards_with_images,
            'animated_postcards': animated_postcards,
            'top_viewed_postcards': top_viewed_postcards,
            'top_liked_postcards': top_liked_postcards,
            'top_zoomed_postcards': top_zoomed_postcards,
            'recent_interactions': recent_interactions,
            'rarity_stats': rarity_stats,

            # Engagement
            'total_likes': total_likes,
            'likes_today': likes_today,
            'likes_week': likes_week,
            'total_suggestions': total_suggestions,
            'pending_suggestions': pending_suggestions,
            'recent_likes': recent_likes,
            'recent_suggestions': recent_suggestions,

            # Traffic
            'total_views': total_views,
            'views_today': views_today,
            'views_week': views_week,
            'total_sessions': total_sessions,
            'sessions_today': sessions_today,
            'unique_visitors_today': unique_visitors_today,
            'unique_visitors_week': unique_visitors_week,

            # Geographic
            'top_countries': top_countries,
            'top_cities': top_cities,
            'countries_today': countries_today,

            # Devices & Browsers
            'device_breakdown': device_breakdown,
            'top_browsers': top_browsers,
            'top_os': top_os,

            # Traffic sources
            'top_referrers': top_referrers,
            'direct_traffic': direct_traffic,
            'referral_traffic': referral_traffic,

            # Search
            'total_searches': total_searches,
            'searches_today': searches_today,
            'searches_week': searches_week,
            'top_searches_all': top_searches_all,
            'top_searches_today': top_searches_today,
            'zero_result_searches': zero_result_searches,
            'recent_searches': recent_searches,

            # Messages
            'total_messages': total_messages,
            'unread_messages': unread_messages,
            'messages_today': messages_today,
            'recent_messages': recent_messages,

            # IP Analysis
            'most_active_ips': most_active_ips,
            'suspicious_ips': suspicious_ips,
            'vpn_proxy_count': vpn_proxy_count,

            # Time-based
            'hourly_traffic': json.dumps([
                {'hour': h['hour'].strftime('%H:00') if h['hour'] else '00:00', 'count': h['count']}
                for h in hourly_traffic
            ]),
            'daily_stats': json.dumps(daily_stats),
            'peak_hours': peak_hours,

            # Performance
            'avg_session_duration': int(avg_session_duration),
            'bounce_rate': round(bounce_rate, 1),
            'pages_per_session': round(pages_per_session, 1),

            # Themes
            'total_themes': Theme.objects.count(),
        }

        return render(request, 'admin_dashboard.html', context)

    except Exception as e:
        import traceback
        return HttpResponse(f"<h1>Admin Error</h1><pre>{traceback.format_exc()}</pre>")


@user_passes_test(is_admin)
def admin_realtime_api(request):
    """API endpoint for real-time visitor data"""
    from .models import RealTimeVisitor

    # Clean up old visitors
    five_minutes_ago = timezone.now() - timedelta(minutes=5)
    RealTimeVisitor.objects.filter(last_activity__lt=five_minutes_ago).delete()

    visitors = RealTimeVisitor.objects.all()

    data = {
        'count': visitors.count(),
        'visitors': list(visitors.values(
            'ip_address', 'country', 'city', 'current_page',
            'device_type', 'browser', 'last_activity', 'user__username'
        )[:30])
    }

    # Add timestamp for each visitor
    for v in data['visitors']:
        if v['last_activity']:
            v['last_activity'] = v['last_activity'].strftime('%H:%M:%S')

    return JsonResponse(data)


@user_passes_test(is_admin)
def admin_geographic_api(request):
    """API endpoint for geographic analytics"""
    from .models import VisitorSession

    period = request.GET.get('period', 'all')

    if period == 'today':
        sessions = VisitorSession.objects.filter(first_visit__date=timezone.now().date())
    elif period == 'week':
        sessions = VisitorSession.objects.filter(
            first_visit__date__gte=timezone.now().date() - timedelta(days=7)
        )
    elif period == 'month':
        sessions = VisitorSession.objects.filter(
            first_visit__date__gte=timezone.now().date() - timedelta(days=30)
        )
    else:
        sessions = VisitorSession.objects.all()

    # Countries with coordinates
    countries = list(
        sessions.exclude(country='')
        .exclude(latitude__isnull=True)
        .values('country', 'country_code', 'latitude', 'longitude')
        .annotate(count=Count('id'))
        .order_by('-count')[:50]
    )

    # Cities
    cities = list(
        sessions.exclude(city='')
        .exclude(latitude__isnull=True)
        .values('city', 'country', 'latitude', 'longitude')
        .annotate(count=Count('id'))
        .order_by('-count')[:100]
    )

    return JsonResponse({
        'countries': countries,
        'cities': cities,
    })


@user_passes_test(is_admin)
def admin_ip_lookup(request, ip_address):
    """API endpoint to lookup IP address details"""
    from .models import VisitorSession, IPLocation
    from .utils import get_ip_location

    # Get location data
    location = get_ip_location(ip_address)

    # Get sessions from this IP
    sessions = VisitorSession.objects.filter(ip_address=ip_address)

    session_data = list(sessions.values(
        'session_key', 'first_visit', 'last_activity',
        'page_views', 'device_type', 'browser', 'os',
        'landing_page', 'user__username'
    ).order_by('-last_activity')[:20])

    # Format dates
    for s in session_data:
        if s['first_visit']:
            s['first_visit'] = s['first_visit'].strftime('%d/%m/%Y %H:%M')
        if s['last_activity']:
            s['last_activity'] = s['last_activity'].strftime('%d/%m/%Y %H:%M')

    return JsonResponse({
        'ip_address': ip_address,
        'location': location,
        'total_sessions': sessions.count(),
        'total_page_views': sessions.aggregate(total=Sum('page_views'))['total'] or 0,
        'sessions': session_data,
    })


@user_passes_test(is_admin)
def admin_postcard_analytics(request, postcard_id):
    """API endpoint for detailed postcard analytics"""
    from .models import Postcard, PostcardInteraction, PostcardLike

    try:
        postcard = Postcard.objects.get(id=postcard_id)
    except Postcard.DoesNotExist:
        return JsonResponse({'error': 'Postcard not found'}, status=404)

    # Interaction breakdown
    interactions = PostcardInteraction.objects.filter(postcard=postcard)

    interaction_types = dict(
        interactions.values('interaction_type')
        .annotate(count=Count('id'))
        .values_list('interaction_type', 'count')
    )

    # Geographic breakdown of views
    country_breakdown = list(
        interactions.filter(interaction_type='view')
        .exclude(country='')
        .values('country')
        .annotate(count=Count('id'))
        .order_by('-count')[:10]
    )

    # Device breakdown
    device_breakdown = dict(
        interactions.values('device_type')
        .annotate(count=Count('id'))
        .values_list('device_type', 'count')
    )

    # Daily views over last 30 days
    thirty_days_ago = timezone.now().date() - timedelta(days=30)
    daily_views = list(
        interactions.filter(
            interaction_type='view',
            timestamp__date__gte=thirty_days_ago
        )
        .annotate(date=TruncDate('timestamp'))
        .values('date')
        .annotate(count=Count('id'))
        .order_by('date')
    )

    # Format dates
    for d in daily_views:
        if d['date']:
            d['date'] = d['date'].strftime('%d/%m')

    # Recent likes
    recent_likes = list(
        PostcardLike.objects.filter(postcard=postcard)
        .select_related('user')
        .order_by('-created_at')[:20]
        .values('user__username', 'ip_address', 'created_at', 'is_animated_like')
    )

    for like in recent_likes:
        if like['created_at']:
            like['created_at'] = like['created_at'].strftime('%d/%m/%Y %H:%M')

    return JsonResponse({
        'postcard': {
            'id': postcard.id,
            'number': postcard.number,
            'title': postcard.title,
            'rarity': postcard.rarity,
            'views_count': postcard.views_count,
            'zoom_count': postcard.zoom_count,
            'likes_count': postcard.likes_count,
            'has_animation': postcard.has_animation(),
            'vignette_url': postcard.get_vignette_url(),
        },
        'interaction_types': interaction_types,
        'country_breakdown': country_breakdown,
        'device_breakdown': device_breakdown,
        'daily_views': daily_views,
        'recent_likes': recent_likes,
    })


@user_passes_test(is_admin)
def admin_export_data(request):
    """Export analytics data as CSV"""
    import csv
    from django.http import HttpResponse

    export_type = request.GET.get('type', 'sessions')
    period = request.GET.get('period', 'week')

    # Determine date range
    if period == 'today':
        start_date = timezone.now().date()
    elif period == 'week':
        start_date = timezone.now().date() - timedelta(days=7)
    elif period == 'month':
        start_date = timezone.now().date() - timedelta(days=30)
    else:
        start_date = None

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="analytics_{export_type}_{period}.csv"'

    writer = csv.writer(response)

    if export_type == 'sessions':
        from .models import VisitorSession

        writer.writerow([
            'Session Key', 'IP Address', 'Country', 'City', 'Device',
            'Browser', 'OS', 'Page Views', 'First Visit', 'Last Activity',
            'Referrer', 'Landing Page', 'Is Bot'
        ])

        sessions = VisitorSession.objects.all()
        if start_date:
            sessions = sessions.filter(first_visit__date__gte=start_date)

        for s in sessions[:10000]:  # Limit to 10k rows
            writer.writerow([
                s.session_key[:20], s.ip_address, s.country, s.city,
                s.device_type, s.browser, s.os, s.page_views,
                s.first_visit.strftime('%Y-%m-%d %H:%M') if s.first_visit else '',
                s.last_activity.strftime('%Y-%m-%d %H:%M') if s.last_activity else '',
                s.referrer_domain, s.landing_page, s.is_bot
            ])

    elif export_type == 'searches':
        from .models import SearchLog

        writer.writerow(['Keyword', 'Results Count', 'User', 'IP Address', 'Date'])

        searches = SearchLog.objects.all()
        if start_date:
            searches = searches.filter(created_at__date__gte=start_date)

        for s in searches[:10000]:
            writer.writerow([
                s.keyword, s.results_count,
                s.user.username if s.user else '',
                s.ip_address,
                s.created_at.strftime('%Y-%m-%d %H:%M') if s.created_at else ''
            ])

    elif export_type == 'likes':
        from .models import PostcardLike

        writer.writerow(['Postcard Number', 'User', 'IP Address', 'Is Animated', 'Date'])

        likes = PostcardLike.objects.select_related('postcard', 'user')
        if start_date:
            likes = likes.filter(created_at__date__gte=start_date)

        for l in likes[:10000]:
            writer.writerow([
                l.postcard.number if l.postcard else '',
                l.user.username if l.user else '',
                l.ip_address,
                l.is_animated_like,
                l.created_at.strftime('%Y-%m-%d %H:%M') if l.created_at else ''
            ])

    return response
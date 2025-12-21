from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.contrib.auth import login, authenticate, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required, user_passes_test
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from datetime import timedelta
import traceback
import json
from django.db.models import Sum, Avg, F, Q, Count
from django.db.models.functions import TruncDate, TruncHour, TruncMonth
from collections import defaultdict
from .utils import get_client_ip, get_location_from_ip, parse_user_agent_string, get_country_flag_emoji, format_duration
import unicodedata

from .models import (
    CustomUser, Postcard, PostcardLike, AnimationSuggestion, Theme,
    ContactMessage, SearchLog, PageView, UserActivity, SystemLog, IntroSeen,
    SentPostcard, PostcardComment, UserConnection, VisitorSession,
    RealTimeVisitor, PostcardInteraction, DailyAnalytics, IPLocation
)
from .forms import (
    ContactForm, SimpleRegistrationForm, VerificationCodeForm,
    SetPasswordForm, ProfileUpdateForm
)


def robots_txt(request):
    """Serve robots.txt"""
    return render(request, 'robots.txt', content_type='text/plain')


def sitemap_xml(request):
    """Generate sitemap.xml dynamically"""
    base_url = 'https://collections.samathey.fr'

    static_pages = [
        {'loc': '/', 'changefreq': 'weekly', 'priority': '1.0'},
        {'loc': '/presentation/', 'changefreq': 'monthly', 'priority': '0.8'},
        {'loc': '/decouvrir/', 'changefreq': 'monthly', 'priority': '0.7'},
        {'loc': '/contact/', 'changefreq': 'monthly', 'priority': '0.6'},
        {'loc': '/parcourir/', 'changefreq': 'daily', 'priority': '0.9'},
        {'loc': '/cp-animes/', 'changefreq': 'weekly', 'priority': '0.8'},
        {'loc': '/connexion/', 'changefreq': 'yearly', 'priority': '0.3'},
        {'loc': '/inscription/', 'changefreq': 'yearly', 'priority': '0.3'},
    ]

    xml_content = '''<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
'''
    for page in static_pages:
        xml_content += f'''
    <url>
        <loc>{base_url}{page['loc']}</loc>
        <changefreq>{page['changefreq']}</changefreq>
        <priority>{page['priority']}</priority>
    </url>'''

    xml_content += '''
</urlset>'''

    return HttpResponse(xml_content, content_type='application/xml')


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


def log_activity(user, action, details='', request=None, related_postcard=None, related_user=None):
    """Log user activity"""
    UserActivity.objects.create(
        user=user,
        action=action,
        details=details,
        ip_address=get_client_ip(request) if request else None,
        session_key=request.session.session_key if request and request.session.session_key else '',
        related_postcard=related_postcard,
        related_user=related_user,
    )


def send_verification_email(user):
    """Send verification code email to user"""
    code = user.generate_new_verification_code()

    subject = 'Vérification de votre compte - Le Postier'

    html_message = render_to_string('emails/verification_code.html', {
        'user': user,
        'code': code,
    })

    plain_message = f"""
Bonjour {user.username},

Votre code de vérification est : {code}

Ce code expire dans 30 minutes.

Si vous n'avez pas créé de compte sur Le Postier, ignorez cet email.

Cordialement,
L'équipe Le Postier
    """

    try:
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )
        return True
    except Exception as e:
        print(f"Error sending verification email: {e}")
        return False


# ============================================
# REGISTRATION & VERIFICATION VIEWS
# ============================================

def register(request):
    """Registration page - Step 1: Enter username and email"""
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        form = SimpleRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()

            if send_verification_email(user):
                request.session['pending_verification_user_id'] = user.id
                return redirect('verify_email')
            else:
                request.session['pending_verification_user_id'] = user.id
                return redirect('verify_email')
    else:
        form = SimpleRegistrationForm()

    return render(request, 'register.html', {'form': form})


def verify_email(request):
    """Verify email with code - Step 2"""
    user_id = request.session.get('pending_verification_user_id')

    if not user_id:
        return redirect('register')

    try:
        user = CustomUser.objects.get(id=user_id)
    except CustomUser.DoesNotExist:
        return redirect('register')

    if user.email_verified:
        return redirect('set_password')

    error = None

    if request.method == 'POST':
        form = VerificationCodeForm(request.POST)
        if form.is_valid():
            code = form.cleaned_data['code']

            if user.verification_code == code and user.is_verification_code_valid():
                user.email_verified = True
                user.category = 'subscribed_verified'
                user.verification_code = None
                user.save()

                log_activity(user, 'verify_email', 'Email vérifié avec succès', request)

                return redirect('set_password')
            else:
                if not user.is_verification_code_valid():
                    error = "Ce code a expiré. Veuillez demander un nouveau code."
                else:
                    error = "Code incorrect. Veuillez réessayer."
    else:
        form = VerificationCodeForm()

    return render(request, 'verify_email.html', {
        'form': form,
        'email': user.email,
        'error': error,
    })


def resend_verification_code(request):
    """Resend verification code"""
    user_id = request.session.get('pending_verification_user_id')

    if not user_id:
        return JsonResponse({'error': 'Session expirée'}, status=400)

    try:
        user = CustomUser.objects.get(id=user_id)
    except CustomUser.DoesNotExist:
        return JsonResponse({'error': 'Utilisateur non trouvé'}, status=404)

    if user.email_verified:
        return JsonResponse({'error': 'Email déjà vérifié'}, status=400)

    if send_verification_email(user):
        return JsonResponse({'success': True, 'message': 'Code envoyé!'})
    else:
        return JsonResponse({'error': 'Erreur lors de l\'envoi'}, status=500)


def set_password(request):
    """Set password after email verification - Step 3"""
    user_id = request.session.get('pending_verification_user_id')

    if not user_id:
        return redirect('register')

    try:
        user = CustomUser.objects.get(id=user_id)
    except CustomUser.DoesNotExist:
        return redirect('register')

    if not user.email_verified:
        return redirect('verify_email')

    if user.password_set and user.has_usable_password():
        del request.session['pending_verification_user_id']
        return redirect('login')

    if request.method == 'POST':
        form = SetPasswordForm(request.POST)
        if form.is_valid():
            password = form.cleaned_data['password1']
            user.set_password(password)
            user.password_set = True
            user.save()

            del request.session['pending_verification_user_id']

            login(request, user)
            log_activity(user, 'register', 'Inscription terminée', request)

            return redirect('registration_complete')
    else:
        form = SetPasswordForm()

    return render(request, 'set_password.html', {
        'form': form,
        'username': user.username,
    })


def registration_complete(request):
    """Registration complete page"""
    if not request.user.is_authenticated:
        return redirect('login')
    return render(request, 'registration_complete.html')


def login_view(request):
    """Login page"""
    if request.user.is_authenticated:
        return redirect('home')

    error = None
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        try:
            user = CustomUser.objects.get(username=username)

            if not user.password_set or not user.has_usable_password():
                request.session['pending_verification_user_id'] = user.id
                if not user.email_verified:
                    return redirect('verify_email')
                else:
                    return redirect('set_password')
        except CustomUser.DoesNotExist:
            pass

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            log_activity(user, 'login', 'Connexion réussie', request)
            next_url = request.GET.get('next', '/')
            return redirect(next_url)
        else:
            error = "Nom d'utilisateur ou mot de passe incorrect."

    return render(request, 'login.html', {'error': error})


def logout_view(request):
    """Logout"""
    if request.user.is_authenticated:
        log_activity(request.user, 'logout', 'Déconnexion', request)
    logout(request)
    return redirect('home')


# ============================================
# PROFILE VIEWS
# ============================================

@login_required
def profile_view(request):
    """User profile dashboard"""
    user = request.user

    # Get actual counts from database
    postcards_sent = SentPostcard.objects.filter(sender=user).count()
    postcards_received = SentPostcard.objects.filter(recipient=user).count()
    unread_postcards = SentPostcard.objects.filter(recipient=user, is_read=False).count()
    total_likes = PostcardLike.objects.filter(user=user).count()
    suggestions_count = AnimationSuggestion.objects.filter(user=user).count()

    # Get connections (users with whom postcards were exchanged)
    sent_to_ids = SentPostcard.objects.filter(sender=user).exclude(recipient__isnull=True).values_list('recipient_id',
                                                                                                       flat=True)
    received_from_ids = SentPostcard.objects.filter(recipient=user).values_list('sender_id', flat=True)
    connection_ids = set(sent_to_ids) | set(received_from_ids)
    connections_count = len(connection_ids)

    # Get total views (postcards this user has viewed)
    total_views = UserActivity.objects.filter(user=user, action='postcard_view').count()

    stats = {
        'postcards_sent': postcards_sent,
        'postcards_received': postcards_received,
        'unread_postcards': unread_postcards,
        'likes_given': total_likes,
        'suggestions': suggestions_count,
        'connections_count': connections_count,
        'total_views': total_views,
    }

    # Get liked postcards with postcard details
    liked_postcards = PostcardLike.objects.filter(
        user=user
    ).select_related('postcard').order_by('-created_at')[:20]

    # Get sent postcards
    sent_postcards = SentPostcard.objects.filter(
        sender=user
    ).select_related('recipient', 'postcard').order_by('-created_at')[:10]

    # Get received postcards
    received_postcards = SentPostcard.objects.filter(
        recipient=user
    ).select_related('sender', 'postcard').order_by('-created_at')[:10]

    # Get epistolary connections with exchange counts
    epistolary_connections = []
    for conn_id in list(connection_ids)[:20]:
        try:
            conn_user = CustomUser.objects.get(id=conn_id)
            sent_count = SentPostcard.objects.filter(sender=user, recipient=conn_user).count()
            received_count = SentPostcard.objects.filter(sender=conn_user, recipient=user).count()
            last_exchange = SentPostcard.objects.filter(
                Q(sender=user, recipient=conn_user) | Q(sender=conn_user, recipient=user)
            ).order_by('-created_at').first()

            epistolary_connections.append({
                'user': conn_user,
                'sent_count': sent_count,
                'received_count': received_count,
                'last_exchange': last_exchange.created_at if last_exchange else None,
            })
        except CustomUser.DoesNotExist:
            continue

    # Get recent activity
    recent_activities = UserActivity.objects.filter(user=user).order_by('-timestamp')[:15]

    context = {
        'user': user,
        'stats': stats,
        'total_likes': total_likes,
        'sent_postcards_count': postcards_sent,
        'received_postcards_count': postcards_received,
        'connections_count': connections_count,
        'total_views': total_views,
        'suggestions_count': suggestions_count,
        'unread_count': unread_postcards,
        'liked_postcards': liked_postcards,
        'sent_postcards': sent_postcards,
        'received_postcards': received_postcards,
        'epistolary_connections': epistolary_connections,
        'recent_activities': recent_activities,
    }

    return render(request, 'profile.html', context)


@login_required
def profile_settings(request):
    """Profile settings page"""
    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            log_activity(request.user, 'profile_update', 'Profil mis à jour', request)
            return JsonResponse({'success': True})
        return JsonResponse({'errors': form.errors}, status=400)

    return render(request, 'profile_settings.html', {
        'form': ProfileUpdateForm(instance=request.user)
    })


@login_required
def profile_connections(request):
    """View all connections/epistolary relations"""
    connections = UserConnection.objects.filter(user=request.user).select_related('connected_to')

    connection_data = []
    for conn in connections:
        exchange_count = request.user.get_exchange_count_with(conn.connected_to)
        last_exchange = SentPostcard.objects.filter(
            Q(sender=request.user, recipient=conn.connected_to) |
            Q(sender=conn.connected_to, recipient=request.user)
        ).order_by('-created_at').first()

        connection_data.append({
            'connection': conn,
            'exchange_count': exchange_count,
            'last_exchange': last_exchange,
        })

    return render(request, 'profile_connections.html', {
        'connections': connection_data,
    })


@login_required
def profile_favorites(request):
    """View all favorite postcards"""
    favorite_postcards = request.user.get_favorite_postcards()
    favorite_animations = request.user.get_favorite_animations()

    return render(request, 'profile_favorites.html', {
        'postcards': favorite_postcards,
        'animations': favorite_animations,
    })


@login_required
def profile_activity(request):
    """View full activity history"""
    activities = UserActivity.objects.filter(user=request.user).order_by('-timestamp')[:100]

    return render(request, 'profile_activity.html', {
        'activities': activities,
    })


@login_required
@require_http_methods(["POST"])
def update_profile(request):
    """Update user profile via AJAX"""
    try:
        # Handle both JSON and form data
        if request.content_type and 'application/json' in request.content_type:
            data = json.loads(request.body)
        else:
            data = request.POST.dict()

        user = request.user
        updated_fields = []

        # Text fields
        allowed_text_fields = ['bio', 'country', 'city', 'website']
        for field in allowed_text_fields:
            if field in data:
                setattr(user, field, data[field])
                updated_fields.append(field)

        # Boolean fields
        allowed_bool_fields = ['show_activity', 'show_connections', 'allow_messages']
        for field in allowed_bool_fields:
            if field in data:
                value = data[field]
                if isinstance(value, str):
                    value = value.lower() in ('true', '1', 'yes', 'on')
                setattr(user, field, bool(value))
                updated_fields.append(field)

        if updated_fields:
            user.save()
            log_activity(user, 'profile_update', f'Champs mis à jour: {", ".join(updated_fields)}', request)

        return JsonResponse({'success': True, 'updated_fields': updated_fields})

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Format JSON invalide'}, status=400)
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
            return JsonResponse({'error': 'File too large (max 2MB)'}, status=400)

        if not file.content_type.startswith('image/'):
            return JsonResponse({'error': 'Invalid file type'}, status=400)

        request.user.signature_image = file
        request.user.save(update_fields=['signature_image'])

        log_activity(request.user, 'profile_update', 'Signature mise à jour', request)

        return JsonResponse({
            'success': True,
            'url': request.user.signature_image.url
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@require_http_methods(["POST"])
def upload_cover(request):
    """Upload profile cover image - handles both file upload and URL"""
    try:
        # Check for file upload with various possible key names
        file = None
        for key in ['cover', 'cover_image', 'file', 'image']:
            if key in request.FILES:
                file = request.FILES[key]
                break

        if file:
            # Validate file size (max 5MB)
            if file.size > 5 * 1024 * 1024:
                return JsonResponse({'error': 'Fichier trop volumineux (max 5MB)'}, status=400)

            # Validate file type
            if not file.content_type.startswith('image/'):
                return JsonResponse({'error': 'Type de fichier non valide'}, status=400)

            # Save to profile_cover field
            request.user.profile_cover = file
            request.user.save(update_fields=['profile_cover'])

            log_activity(request.user, 'profile_update', 'Image de couverture mise à jour', request)

            return JsonResponse({
                'success': True,
                'url': request.user.profile_cover.url
            })

        # Check for URL in POST data (from postcard selection)
        cover_url = request.POST.get('cover_url') or request.POST.get('url')

        # Also check JSON body
        if not cover_url:
            try:
                data = json.loads(request.body)
                cover_url = data.get('cover_url') or data.get('url')
            except (json.JSONDecodeError, ValueError):
                pass

        if cover_url:
            import requests as http_requests
            from django.core.files.base import ContentFile
            import uuid

            try:
                # Download the image from URL
                response = http_requests.get(cover_url, timeout=10)
                if response.status_code == 200:
                    # Determine file extension
                    content_type = response.headers.get('content-type', 'image/jpeg')
                    if 'jpeg' in content_type or 'jpg' in content_type:
                        ext = 'jpg'
                    elif 'png' in content_type:
                        ext = 'png'
                    elif 'gif' in content_type:
                        ext = 'gif'
                    elif 'webp' in content_type:
                        ext = 'webp'
                    else:
                        ext = 'jpg'

                    # Generate unique filename
                    filename = f"cover_{request.user.id}_{uuid.uuid4().hex[:8]}.{ext}"

                    # Save the image
                    request.user.profile_cover.save(filename, ContentFile(response.content))

                    log_activity(request.user, 'profile_update', 'Image de couverture mise à jour depuis URL', request)

                    return JsonResponse({
                        'success': True,
                        'url': request.user.profile_cover.url
                    })
                else:
                    return JsonResponse({
                        'error': f'Impossible de télécharger l\'image (status: {response.status_code})'
                    }, status=400)
            except http_requests.exceptions.Timeout:
                return JsonResponse({'error': 'Délai d\'attente dépassé pour le téléchargement'}, status=400)
            except http_requests.exceptions.RequestException as e:
                return JsonResponse({'error': f'Erreur de téléchargement: {str(e)}'}, status=400)

        # No file or URL provided
        return JsonResponse({
            'error': 'Aucune image fournie. Envoyez un fichier ou une URL.'
        }, status=400)

    except Exception as e:
        import traceback
        print(f"Upload cover error: {traceback.format_exc()}")
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@require_http_methods(["POST"])
def change_password(request):
    """API endpoint to change user password"""
    try:
        data = json.loads(request.body)
        current_password = data.get('current_password', '')
        new_password = data.get('new_password', '')

        if not current_password or not new_password:
            return JsonResponse({'error': 'Tous les champs sont requis'}, status=400)

        if len(new_password) < 8:
            return JsonResponse({'error': 'Le mot de passe doit contenir au moins 8 caractères'}, status=400)

        if not request.user.check_password(current_password):
            return JsonResponse({'error': 'Mot de passe actuel incorrect'}, status=400)

        request.user.set_password(new_password)
        request.user.save()

        update_session_auth_hash(request, request.user)

        return JsonResponse({'success': True, 'message': 'Mot de passe changé avec succès'})

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@require_http_methods(["POST"])
def toggle_connection_favorite(request, connection_id):
    """Toggle a connection as favorite"""
    try:
        connection = UserConnection.objects.get(id=connection_id, user=request.user)
        connection.is_favorite = not connection.is_favorite
        connection.save()
        return JsonResponse({'success': True, 'is_favorite': connection.is_favorite})
    except UserConnection.DoesNotExist:
        return JsonResponse({'error': 'Connection not found'}, status=404)


@login_required
@require_http_methods(["POST"])
def update_connection_notes(request, connection_id):
    """Update notes for a connection"""
    try:
        data = json.loads(request.body)
        connection = UserConnection.objects.get(id=connection_id, user=request.user)
        connection.notes = data.get('notes', '')[:200]
        connection.save()
        return JsonResponse({'success': True})
    except UserConnection.DoesNotExist:
        return JsonResponse({'error': 'Connection not found'}, status=404)


@login_required
def view_user_profile(request, username):
    """View another user's public profile"""
    viewed_user = get_object_or_404(CustomUser, username=username)

    if viewed_user == request.user:
        return redirect('profile')

    is_connected = UserConnection.objects.filter(
        user=request.user,
        connected_to=viewed_user
    ).exists()

    exchange_count = 0
    if is_connected:
        exchange_count = request.user.get_exchange_count_with(viewed_user)

    context = {
        'viewed_user': viewed_user,
        'is_connected': is_connected,
        'exchange_count': exchange_count,
        'can_message': viewed_user.allow_messages,
    }

    return render(request, 'view_profile.html', context)


@login_required
def get_postcards_for_cover(request):
    """API endpoint to get postcards for cover selection"""
    postcards = Postcard.objects.filter(has_images=True).order_by('?')[:50]

    data = [{
        'id': p.id,
        'number': p.number,
        'title': p.title,
        'vignette_url': p.get_vignette_url(),
        'grande_url': p.get_grande_url(),
    } for p in postcards if p.get_vignette_url()]

    return JsonResponse({'postcards': data})


# ============================================
# INTRO & HOME VIEWS
# ============================================

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

        video_urls = []
        postcards_with_videos = Postcard.objects.filter(
            has_images=True
        ).order_by('?')[:30]

        for postcard in postcards_with_videos:
            urls = postcard.get_animated_urls()
            if urls:
                video_urls.append(urls[0])
                if len(video_urls) >= 15:
                    break

        return render(request, 'home.html', {
            'animated_videos': video_urls[:15]
        })
    except Exception as e:
        return HttpResponse(f"<h1>Home Error</h1><pre>{traceback.format_exc()}</pre>")


# ============================================
# BROWSE & GALLERY VIEWS
# ============================================

def remove_accents(text):
    """Remove accents from text for accent-insensitive search"""
    if not text:
        return ''
    return ''.join(
        c for c in unicodedata.normalize('NFD', text)
        if unicodedata.category(c) != 'Mn'
    )


def browse(request):
    """Browse page with exact phrase search"""
    try:
        query = request.GET.get('keywords_input', '').strip()

        postcards = Postcard.objects.filter(has_images=True)
        themes = Theme.objects.all()[:20]

        # Then in the search:
        if query:
            normalized_query = remove_accents(query.lower())

            # Get all postcards and filter in Python for accent-insensitive search
            all_postcards = postcards.filter(has_images=True)
            matching_ids = []

            for postcard in all_postcards:
                title_normalized = remove_accents(postcard.title.lower()) if postcard.title else ''
                keywords_normalized = remove_accents(postcard.keywords.lower()) if postcard.keywords else ''
                number_str = str(postcard.number).lower()

                if (normalized_query in title_normalized or
                        normalized_query in keywords_normalized or
                        normalized_query in number_str):
                    matching_ids.append(postcard.id)

            postcards = Postcard.objects.filter(id__in=matching_ids, has_images=True)

        # Convert to list for template
        postcards = list(postcards)

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
            'displayed_count': len(postcards),
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
        all_postcards = Postcard.objects.all().order_by('-likes_count', 'number')

        animated_postcards = []
        for postcard in all_postcards:
            video_urls = postcard.get_animated_urls()
            if video_urls:
                postcard.video_count = len(video_urls)
                animated_postcards.append(postcard)
                if len(animated_postcards) >= 100:
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
        return HttpResponse(f"<h1>Animated Gallery Error</h1><pre>{traceback.format_exc()}</pre>")


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
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            message = form.save(commit=False)
            if request.user.is_authenticated:
                message.user = request.user
            message.ip_address = get_client_ip(request)
            message.save()

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


# ============================================
# POSTCARD API VIEWS
# ============================================

def get_postcard_detail(request, postcard_id):
    """API endpoint for postcard details"""
    try:
        postcard = Postcard.objects.get(id=postcard_id)

        postcard.views_count += 1
        postcard.save(update_fields=['views_count'])

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
    """API endpoint to like/unlike a postcard with full tracking"""
    try:
        postcard = get_object_or_404(Postcard, id=postcard_id)
        is_animated = request.POST.get('is_animated', 'false').lower() == 'true'

        if not request.session.session_key:
            request.session.create()

        ip_address = get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')

        # Get location and device info
        location = get_location_from_ip(ip_address)
        ua_info = parse_user_agent_string(user_agent)

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
            # Create like with full tracking info
            PostcardLike.objects.create(
                postcard=postcard,
                user=request.user if request.user.is_authenticated else None,
                session_key=request.session.session_key if not request.user.is_authenticated else '',
                is_animated_like=is_animated,
                ip_address=ip_address,
                country=location.get('country', ''),
                city=location.get('city', ''),
                device_type=ua_info.get('device_type', ''),
                browser=ua_info.get('browser', ''),
                user_agent=user_agent,
            )
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
# LA POSTE - SOCIAL HUB VIEWS
# ============================================

@login_required
def la_poste(request):
    """La Poste - Social hub for sending postcards"""
    user_has_signature = bool(request.user.signature_image)

    # Check if a specific postcard is preselected
    preselected_postcard_id = request.GET.get('postcard')
    preselected_postcard = None
    if preselected_postcard_id:
        try:
            preselected_postcard = Postcard.objects.get(id=int(preselected_postcard_id))
        except (Postcard.DoesNotExist, ValueError):
            pass

    received = SentPostcard.objects.filter(
        recipient=request.user
    ).select_related('sender', 'postcard').order_by('-created_at')[:30]

    sent = SentPostcard.objects.filter(
        sender=request.user
    ).select_related('recipient', 'postcard').order_by('-created_at')[:30]

    public_postcards = SentPostcard.objects.filter(
        visibility='public'
    ).select_related('sender', 'postcard').prefetch_related('comments').order_by('-created_at')[:50]

    unread_count = SentPostcard.objects.filter(
        recipient=request.user,
        is_read=False
    ).count()

    available_postcards = Postcard.objects.filter(has_images=True).order_by('?')[:100]

    all_postcards = list(Postcard.objects.filter(has_images=True).order_by('?')[:200])
    animated_postcards = [p for p in all_postcards if p.has_animation()][:50]

    context = {
        'received_postcards': received,
        'sent_postcards': sent,
        'public_postcards': public_postcards,
        'unread_count': unread_count,
        'available_postcards': available_postcards,
        'animated_postcards': animated_postcards,
        'user_has_signature': user_has_signature,
        'preselected_postcard': preselected_postcard,
    }

    return render(request, 'la_poste.html', context)


@login_required
@require_http_methods(["POST"])
def send_postcard(request):
    """Send a postcard to another user or post publicly"""
    try:
        data = json.loads(request.body)

        if not request.user.signature_image:
            return JsonResponse({
                'error': 'Vous devez d\'abord créer votre signature dans votre profil pour envoyer des cartes postales.'
            }, status=400)

        message = data.get('message', '').strip()
        stamp_type = data.get('stamp_type', '10c')

        max_chars = 44 if stamp_type == '5c' else 55

        if not message:
            return JsonResponse({'error': 'Le message ne peut pas être vide'}, status=400)

        if len(message) > max_chars:
            return JsonResponse({
                'error': f'Message trop long. Maximum {max_chars} caractères pour le timbre choisi.'
            }, status=400)

        visibility = data.get('visibility', 'private')
        recipient_username = data.get('recipient')
        postcard_id = data.get('postcard_id')
        is_animated = data.get('is_animated', False)

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

        if not postcard:
            return JsonResponse({'error': 'Veuillez sélectionner une carte postale'}, status=400)

        sent_postcard = SentPostcard.objects.create(
            sender=request.user,
            recipient=recipient,
            postcard=postcard,
            message=message,
            stamp_type=stamp_type,
            visibility=visibility,
            is_animated=is_animated
        )

        return JsonResponse({
            'success': True,
            'postcard_id': sent_postcard.id,
            'message': 'Carte postale envoyée!' if visibility == 'private' else 'Carte publiée!'
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
def get_postcard_message(request, postcard_id):
    """Get the message details for a sent postcard"""
    try:
        sent_postcard = SentPostcard.objects.select_related('sender', 'postcard').get(id=postcard_id)

        if sent_postcard.visibility == 'private':
            if request.user != sent_postcard.sender and request.user != sent_postcard.recipient:
                return JsonResponse({'error': 'Accès non autorisé'}, status=403)

        if request.user == sent_postcard.recipient and not sent_postcard.is_read:
            sent_postcard.is_read = True
            sent_postcard.save(update_fields=['is_read'])

        data = {
            'id': sent_postcard.id,
            'message': sent_postcard.message,
            'stamp_type': sent_postcard.stamp_type,
            'sender_username': sent_postcard.sender.username,
            'sender_signature_url': sent_postcard.get_sender_signature_url(),
            'created_at': sent_postcard.created_at.strftime('%d/%m/%Y %H:%M'),
            'is_animated': sent_postcard.is_animated,
            'postcard_title': sent_postcard.postcard.title if sent_postcard.postcard else None,
            'postcard_number': sent_postcard.postcard.number if sent_postcard.postcard else None,
            'image_url': sent_postcard.get_image_url(),
            'vignette_url': sent_postcard.get_vignette_url(),
        }

        return JsonResponse(data)

    except SentPostcard.DoesNotExist:
        return JsonResponse({'error': 'Carte non trouvée'}, status=404)


@login_required
def check_user_signature(request):
    """Check if user has a signature"""
    return JsonResponse({
        'has_signature': bool(request.user.signature_image),
        'signature_url': request.user.signature_image.url if request.user.signature_image else None
    })


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


# ============================================
# ADMIN DASHBOARD VIEWS
# ============================================

@user_passes_test(is_admin)
# Replace the admin_dashboard view:
@user_passes_test(is_admin)
def admin_dashboard(request):
    """Comprehensive admin dashboard with full analytics"""
    try:
        today = timezone.now().date()
        now = timezone.now()
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)
        yesterday = today - timedelta(days=1)
        five_minutes_ago = now - timedelta(minutes=5)

        # =============================================
        # REAL-TIME VISITORS
        # =============================================
        # Clean up old real-time records
        RealTimeVisitor.objects.filter(last_activity__lt=five_minutes_ago).delete()

        active_visitors = RealTimeVisitor.objects.all().order_by('-last_activity')
        active_visitor_count = active_visitors.count()
        active_visitors_list = list(active_visitors.values(
            'ip_address', 'country', 'city', 'current_page', 'page_title',
            'device_type', 'browser', 'last_activity', 'user__username'
        )[:20])

        # Add flag emojis
        for visitor in active_visitors_list:
            visitor['flag'] = get_country_flag_emoji(visitor.get('country', '')[:2] if visitor.get('country') else '')
            if visitor['last_activity']:
                visitor['last_activity'] = visitor['last_activity'].strftime('%H:%M:%S')

        # =============================================
        # USER STATISTICS
        # =============================================
        total_users = CustomUser.objects.count()
        new_users_today = CustomUser.objects.filter(date_joined__date=today).count()
        new_users_yesterday = CustomUser.objects.filter(date_joined__date=yesterday).count()
        new_users_week = CustomUser.objects.filter(date_joined__date__gte=week_ago).count()
        new_users_month = CustomUser.objects.filter(date_joined__date__gte=month_ago).count()

        user_growth_percent = 0
        if new_users_yesterday > 0:
            user_growth_percent = round(((new_users_today - new_users_yesterday) / new_users_yesterday) * 100, 1)

        user_categories = {
            'unverified': CustomUser.objects.filter(category='subscribed_unverified').count(),
            'verified': CustomUser.objects.filter(category='subscribed_verified').count(),
            'postman': CustomUser.objects.filter(category='postman').count(),
            'viewer': CustomUser.objects.filter(category='viewer').count(),
            'staff': CustomUser.objects.filter(is_staff=True).count(),
        }

        # =============================================
        # POSTCARD STATISTICS
        # =============================================
        total_postcards = Postcard.objects.count()
        postcards_with_images = Postcard.objects.filter(has_images=True).count()

        # Count animated postcards more accurately
        animated_count = 0
        for p in Postcard.objects.filter(has_images=True)[:500]:
            if p.has_animation():
                animated_count += 1
        animated_postcards = animated_count

        total_views = Postcard.objects.aggregate(total=Sum('views_count'))['total'] or 0
        total_zooms = Postcard.objects.aggregate(total=Sum('zoom_count'))['total'] or 0

        # =============================================
        # PAGE VIEW STATISTICS
        # =============================================
        page_views_today = PageView.objects.filter(timestamp__date=today).count()
        page_views_yesterday = PageView.objects.filter(timestamp__date=yesterday).count()
        page_views_week = PageView.objects.filter(timestamp__date__gte=week_ago).count()
        page_views_month = PageView.objects.filter(timestamp__date__gte=month_ago).count()
        total_page_views = PageView.objects.count()

        views_growth_percent = 0
        if page_views_yesterday > 0:
            views_growth_percent = round(((page_views_today - page_views_yesterday) / page_views_yesterday) * 100, 1)

        # Unique visitors
        unique_visitors_today = PageView.objects.filter(
            timestamp__date=today
        ).values('ip_address').distinct().count()

        unique_visitors_week = PageView.objects.filter(
            timestamp__date__gte=week_ago
        ).values('ip_address').distinct().count()

        # =============================================
        # SESSION STATISTICS
        # =============================================
        sessions_today = VisitorSession.objects.filter(first_visit__date=today).count()
        sessions_week = VisitorSession.objects.filter(first_visit__date__gte=week_ago).count()

        # Average session duration
        avg_session_duration = VisitorSession.objects.filter(
            first_visit__date__gte=week_ago
        ).aggregate(avg=Avg('total_time_spent'))['avg'] or 0
        avg_session_duration = int(avg_session_duration)

        # Pages per session
        avg_pages = VisitorSession.objects.filter(
            first_visit__date__gte=week_ago, page_views__gt=0
        ).aggregate(avg=Avg('page_views'))['avg'] or 0
        pages_per_session = round(avg_pages, 1)

        # Bounce rate (sessions with only 1 page view)
        single_page_sessions = VisitorSession.objects.filter(
            first_visit__date__gte=week_ago, page_views=1
        ).count()
        total_sessions_week = VisitorSession.objects.filter(first_visit__date__gte=week_ago).count()
        bounce_rate = round((single_page_sessions / total_sessions_week * 100), 1) if total_sessions_week > 0 else 0

        # =============================================
        # LIKE STATISTICS WITH FULL DETAILS
        # =============================================
        total_likes = PostcardLike.objects.count()
        likes_today = PostcardLike.objects.filter(created_at__date=today).count()
        likes_yesterday = PostcardLike.objects.filter(created_at__date=yesterday).count()
        likes_week = PostcardLike.objects.filter(created_at__date__gte=week_ago).count()

        likes_growth_percent = 0
        if likes_yesterday > 0:
            likes_growth_percent = round(((likes_today - likes_yesterday) / likes_yesterday) * 100, 1)

        # Recent likes with full details
        recent_likes = PostcardLike.objects.select_related('postcard', 'user').order_by('-created_at')[:50]
        recent_likes_data = []
        for like in recent_likes:
            recent_likes_data.append({
                'id': like.id,
                'postcard_number': like.postcard.number if like.postcard else 'N/A',
                'postcard_id': like.postcard.id if like.postcard else None,
                'postcard_title': like.postcard.title[:30] if like.postcard else 'N/A',
                'user': like.user.username if like.user else 'Anonyme',
                'is_animated': like.is_animated_like,
                'ip_address': like.ip_address or 'N/A',
                'country': like.country or 'Unknown',
                'city': like.city or 'Unknown',
                'device_type': like.device_type or 'Unknown',
                'browser': like.browser or 'Unknown',
                'created_at': like.created_at.strftime('%d/%m/%Y %H:%M'),
                'flag': get_country_flag_emoji(like.country[:2] if like.country else ''),
            })

        # Likes by country
        likes_by_country = list(
            PostcardLike.objects.exclude(country='').values('country')
            .annotate(count=Count('id'))
            .order_by('-count')[:10]
        )

        # =============================================
        # SEARCH STATISTICS
        # =============================================
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
            .annotate(count=Count('id'), avg_results=Avg('results_count'))
            .order_by('-count')[:15]
        )

        # Zero result searches
        zero_result_searches = list(
            SearchLog.objects.filter(results_count=0)
            .values('keyword')
            .annotate(count=Count('id'))
            .order_by('-count')[:15]
        )

        # Recent searches with details
        recent_searches = SearchLog.objects.select_related('user').order_by('-created_at')[:30]

        # =============================================
        # GEOGRAPHIC DATA
        # =============================================
        # Top countries all time
        top_countries = list(
            VisitorSession.objects.exclude(country='')
            .values('country', 'country_code')
            .annotate(count=Count('id'))
            .order_by('-count')[:15]
        )
        for c in top_countries:
            c['flag'] = get_country_flag_emoji(c.get('country_code', ''))

        # Top cities
        top_cities = list(
            VisitorSession.objects.exclude(city='').exclude(city='Unknown')
            .values('city', 'country')
            .annotate(count=Count('id'))
            .order_by('-count')[:15]
        )

        # Countries today
        countries_today = list(
            PageView.objects.filter(timestamp__date=today)
            .exclude(country='')
            .values('country')
            .annotate(count=Count('id'))
            .order_by('-count')[:10]
        )
        for c in countries_today:
            c['flag'] = get_country_flag_emoji(c.get('country', '')[:2])

        # =============================================
        # DEVICE & BROWSER STATISTICS
        # =============================================
        device_stats = VisitorSession.objects.exclude(device_type='').values('device_type').annotate(
            count=Count('id')
        ).order_by('-count')

        device_breakdown = {
            'mobile': 0,
            'tablet': 0,
            'desktop': 0,
            'other': 0,
        }
        for d in device_stats:
            dtype = d['device_type'].lower()
            if 'mobile' in dtype:
                device_breakdown['mobile'] += d['count']
            elif 'tablet' in dtype:
                device_breakdown['tablet'] += d['count']
            elif 'desktop' in dtype:
                device_breakdown['desktop'] += d['count']
            else:
                device_breakdown['other'] += d['count']

        # Top browsers
        top_browsers = list(
            VisitorSession.objects.exclude(browser='').exclude(browser='Unknown')
            .values('browser')
            .annotate(count=Count('id'))
            .order_by('-count')[:10]
        )

        # Top OS
        top_os = list(
            VisitorSession.objects.exclude(os='').exclude(os='Unknown')
            .values('os')
            .annotate(count=Count('id'))
            .order_by('-count')[:10]
        )

        # =============================================
        # REFERRER STATISTICS
        # =============================================
        top_referrers = list(
            VisitorSession.objects.exclude(referrer_domain='').exclude(referrer_domain__icontains='samathey')
            .values('referrer_domain')
            .annotate(count=Count('id'))
            .order_by('-count')[:15]
        )

        direct_traffic = VisitorSession.objects.filter(
            Q(referrer='') | Q(referrer_domain='')
        ).count()

        referral_traffic = VisitorSession.objects.exclude(referrer='').exclude(referrer_domain='').count()

        # =============================================
        # MESSAGES & SUGGESTIONS
        # =============================================
        total_messages = ContactMessage.objects.count()
        unread_messages = ContactMessage.objects.filter(is_read=False).count()
        messages_today = ContactMessage.objects.filter(created_at__date=today).count()
        recent_messages = ContactMessage.objects.select_related('user').order_by('-created_at')[:15]

        total_suggestions = AnimationSuggestion.objects.count()
        pending_suggestions = AnimationSuggestion.objects.filter(status='pending').count()
        recent_suggestions = AnimationSuggestion.objects.select_related(
            'postcard', 'user'
        ).order_by('-created_at')[:20]

        # =============================================
        # TOP POSTCARDS
        # =============================================
        top_viewed_postcards = Postcard.objects.order_by('-views_count')[:15]
        top_liked_postcards = Postcard.objects.order_by('-likes_count')[:15]
        top_zoomed_postcards = Postcard.objects.order_by('-zoom_count')[:10]

        # Rarity statistics
        rarity_stats = {}
        for rarity in ['common', 'rare', 'very_rare']:
            stats = Postcard.objects.filter(rarity=rarity).aggregate(
                count=Count('id'),
                total_views=Sum('views_count'),
                total_likes=Sum('likes_count'),
                total_zooms=Sum('zoom_count'),
            )
            rarity_stats[rarity] = {
                'count': stats['count'] or 0,
                'total_views': stats['total_views'] or 0,
                'total_likes': stats['total_likes'] or 0,
                'total_zooms': stats['total_zooms'] or 0,
            }

        # =============================================
        # RECENT USERS
        # =============================================
        recent_users = CustomUser.objects.order_by('-date_joined')[:20]
        recent_users_data = []
        for user in recent_users:
            recent_users_data.append({
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'category': user.category,
                'is_staff': user.is_staff,
                'is_superuser': user.is_superuser,
                'email_verified': user.email_verified,
                'date_joined': user.date_joined,
                'last_login': user.last_login,
                'registration_ip': user.registration_ip or 'N/A',
                'country': user.country or 'N/A',
                'city': user.city or 'N/A',
            })

        # =============================================
        # IP ANALYSIS
        # =============================================
        # Most active IPs
        most_active_ips = list(
            VisitorSession.objects.values('ip_address', 'country', 'city', 'isp')
            .annotate(
                session_count=Count('id'),
                total_page_views=Sum('page_views')
            )
            .order_by('-session_count')[:20]
        )

        # Suspicious IPs (many sessions from same IP)
        suspicious_ips = list(
            VisitorSession.objects.values('ip_address', 'country')
            .annotate(count=Count('id'))
            .filter(count__gte=10)
            .order_by('-count')[:15]
        )

        # VPN/Proxy count
        vpn_proxy_count = IPLocation.objects.filter(
            Q(is_vpn=True) | Q(is_proxy=True)
        ).count()

        # =============================================
        # HOURLY TRAFFIC (Today)
        # =============================================
        hourly_traffic = []
        for hour in range(24):
            count = PageView.objects.filter(
                timestamp__date=today,
                timestamp__hour=hour
            ).count()
            hourly_traffic.append({
                'hour': f'{hour:02d}:00',
                'count': count
            })

        # Peak hours
        peak_hours = sorted(hourly_traffic, key=lambda x: x['count'], reverse=True)[:3]

        # =============================================
        # DAILY STATS (Last 30 days)
        # =============================================
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
                'messages': ContactMessage.objects.filter(created_at__date=date).count(),
            })

        # =============================================
        # WEEKLY COMPARISON
        # =============================================
        this_week_start = today - timedelta(days=today.weekday())
        last_week_start = this_week_start - timedelta(days=7)
        last_week_end = this_week_start - timedelta(days=1)

        this_week_views = PageView.objects.filter(timestamp__date__gte=this_week_start).count()
        last_week_views = PageView.objects.filter(
            timestamp__date__gte=last_week_start,
            timestamp__date__lte=last_week_end
        ).count()

        week_over_week_change = 0
        if last_week_views > 0:
            week_over_week_change = round(((this_week_views - last_week_views) / last_week_views) * 100, 1)

        # =============================================
        # POSTCARD INTERACTIONS (Recent)
        # =============================================
        recent_interactions = list(
            PostcardInteraction.objects.select_related('postcard', 'user', 'session')
            .order_by('-timestamp')[:30]
            .values(
                'postcard__number', 'postcard__title', 'interaction_type',
                'user__username', 'ip_address', 'country', 'device_type', 'timestamp'
            )
        )

        # =============================================
        # SYSTEM HEALTH
        # =============================================
        from pathlib import Path
        import os

        media_root = Path(settings.MEDIA_ROOT)
        media_stats = {
            'exists': media_root.exists(),
            'vignette_count': 0,
            'grande_count': 0,
            'animated_count': 0,
        }

        if media_root.exists():
            vignette_path = media_root / 'postcards' / 'Vignette'
            grande_path = media_root / 'postcards' / 'Grande'
            animated_path = media_root / 'animated_cp'

            if vignette_path.exists():
                media_stats['vignette_count'] = len(list(vignette_path.glob('*.*')))
            if grande_path.exists():
                media_stats['grande_count'] = len(list(grande_path.glob('*.*')))
            if animated_path.exists():
                media_stats['animated_count'] = len(list(animated_path.glob('*.*')))

        # =============================================
        # CONTEXT
        # =============================================
        context = {
            # Real-time
            'active_visitor_count': active_visitor_count,
            'active_visitors_list': active_visitors_list,

            # Users
            'total_users': total_users,
            'new_users_today': new_users_today,
            'new_users_yesterday': new_users_yesterday,
            'new_users_week': new_users_week,
            'new_users_month': new_users_month,
            'user_growth_percent': user_growth_percent,
            'user_categories': user_categories,
            'user_categories_choices': CustomUser.USER_CATEGORIES,
            'recent_users': recent_users_data,

            # Postcards
            'total_postcards': total_postcards,
            'postcards_with_images': postcards_with_images,
            'animated_postcards': animated_postcards,
            'total_postcard_views': total_views,
            'total_postcard_zooms': total_zooms,
            'top_viewed_postcards': top_viewed_postcards,
            'top_liked_postcards': top_liked_postcards,
            'top_zoomed_postcards': top_zoomed_postcards,
            'rarity_stats': rarity_stats,

            # Page views
            'page_views_today': page_views_today,
            'page_views_yesterday': page_views_yesterday,
            'page_views_week': page_views_week,
            'page_views_month': page_views_month,
            'total_page_views': total_page_views,
            'views_growth_percent': views_growth_percent,

            # Sessions
            'sessions_today': sessions_today,
            'sessions_week': sessions_week,
            'unique_visitors_today': unique_visitors_today,
            'unique_visitors_week': unique_visitors_week,
            'avg_session_duration': avg_session_duration,
            'avg_session_duration_formatted': format_duration(avg_session_duration),
            'pages_per_session': pages_per_session,
            'bounce_rate': bounce_rate,
            'week_over_week_change': week_over_week_change,

            # Likes
            'total_likes': total_likes,
            'likes_today': likes_today,
            'likes_yesterday': likes_yesterday,
            'likes_week': likes_week,
            'likes_growth_percent': likes_growth_percent,
            'recent_likes': recent_likes_data,
            'likes_by_country': likes_by_country,

            # Searches
            'total_searches': total_searches,
            'searches_today': searches_today,
            'searches_week': searches_week,
            'top_searches_all': top_searches_all,
            'top_searches_today': top_searches_today,
            'zero_result_searches': zero_result_searches,
            'recent_searches': recent_searches,

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

            # Messages & Suggestions
            'total_messages': total_messages,
            'unread_messages': unread_messages,
            'messages_today': messages_today,
            'recent_messages': recent_messages,
            'total_suggestions': total_suggestions,
            'pending_suggestions': pending_suggestions,
            'recent_suggestions': recent_suggestions,

            # IP Analysis
            'most_active_ips': most_active_ips,
            'suspicious_ips': suspicious_ips,
            'vpn_proxy_count': vpn_proxy_count,

            # Time-based
            'hourly_traffic': json.dumps(hourly_traffic),
            'daily_stats': json.dumps(daily_stats),
            'peak_hours': peak_hours,

            # Recent interactions
            'recent_interactions': recent_interactions,

            # System
            'media_stats': media_stats,
            'total_themes': Theme.objects.count(),
        }

        return render(request, 'admin_dashboard.html', context)

    except Exception as e:
        import traceback
        return HttpResponse(f"<h1>Admin Error</h1><pre>{traceback.format_exc()}</pre>")


# Add new API endpoints for admin dashboard
@user_passes_test(is_admin)
def admin_realtime_api(request):
    """API endpoint for real-time visitor data"""
    from .utils import get_country_flag_emoji

    five_minutes_ago = timezone.now() - timedelta(minutes=5)
    RealTimeVisitor.objects.filter(last_activity__lt=five_minutes_ago).delete()

    visitors = RealTimeVisitor.objects.all().order_by('-last_activity')

    data = {
        'count': visitors.count(),
        'visitors': []
    }

    for v in visitors[:30]:
        data['visitors'].append({
            'ip_address': v.ip_address,
            'country': v.country,
            'city': v.city,
            'current_page': v.current_page,
            'page_title': v.page_title,
            'device_type': v.device_type,
            'browser': v.browser,
            'last_activity': v.last_activity.strftime('%H:%M:%S') if v.last_activity else '',
            'username': v.user.username if v.user else None,
            'flag': get_country_flag_emoji(v.country[:2] if v.country else ''),
        })

    return JsonResponse(data)


@user_passes_test(is_admin)
def admin_likes_api(request):
    """API endpoint for likes with full details"""
    from .utils import get_country_flag_emoji

    page = int(request.GET.get('page', 1))
    per_page = int(request.GET.get('per_page', 50))

    likes = PostcardLike.objects.select_related('postcard', 'user').order_by('-created_at')

    start = (page - 1) * per_page
    end = start + per_page

    likes_data = []
    for like in likes[start:end]:
        likes_data.append({
            'id': like.id,
            'postcard_number': like.postcard.number if like.postcard else 'N/A',
            'postcard_id': like.postcard.id if like.postcard else None,
            'postcard_title': like.postcard.title[:40] if like.postcard else 'N/A',
            'user': like.user.username if like.user else 'Anonyme',
            'is_animated': like.is_animated_like,
            'ip_address': like.ip_address or 'N/A',
            'country': like.country or 'Unknown',
            'city': like.city or 'Unknown',
            'device_type': like.device_type or 'Unknown',
            'browser': like.browser or 'Unknown',
            'created_at': like.created_at.strftime('%d/%m/%Y %H:%M:%S'),
            'flag': get_country_flag_emoji(like.country[:2] if like.country else ''),
        })

    return JsonResponse({
        'likes': likes_data,
        'total': likes.count(),
        'page': page,
        'per_page': per_page,
        'total_pages': (likes.count() + per_page - 1) // per_page,
    })


@user_passes_test(is_admin)
def admin_geographic_api(request):
    """API endpoint for geographic analytics"""
    from .utils import get_country_flag_emoji

    period = request.GET.get('period', 'all')

    if period == 'today':
        date_filter = {'first_visit__date': timezone.now().date()}
    elif period == 'week':
        date_filter = {'first_visit__date__gte': timezone.now().date() - timedelta(days=7)}
    elif period == 'month':
        date_filter = {'first_visit__date__gte': timezone.now().date() - timedelta(days=30)}
    else:
        date_filter = {}

    countries = list(
        VisitorSession.objects.filter(**date_filter)
        .exclude(country='')
        .values('country', 'country_code')
        .annotate(
            count=Count('id'),
            total_pages=Sum('page_views')
        )
        .order_by('-count')[:30]
    )

    for c in countries:
        c['flag'] = get_country_flag_emoji(c.get('country_code', ''))

    cities = list(
        VisitorSession.objects.filter(**date_filter)
        .exclude(city='').exclude(city='Unknown')
        .values('city', 'country', 'country_code')
        .annotate(count=Count('id'))
        .order_by('-count')[:30]
    )

    for c in cities:
        c['flag'] = get_country_flag_emoji(c.get('country_code', ''))

    return JsonResponse({
        'countries': countries,
        'cities': cities,
    })


@user_passes_test(is_admin)
def admin_ip_lookup(request, ip_address):
    """API endpoint to lookup IP address details"""
    from .utils import get_location_from_ip, get_country_flag_emoji

    # Get fresh location data
    location = get_location_from_ip(ip_address)

    # Get sessions from this IP
    sessions = VisitorSession.objects.filter(ip_address=ip_address).order_by('-first_visit')

    # Get page views from this IP
    page_views = PageView.objects.filter(ip_address=ip_address).order_by('-timestamp')

    # Get likes from this IP
    likes = PostcardLike.objects.filter(ip_address=ip_address).select_related('postcard')

    # Get searches from this IP
    searches = SearchLog.objects.filter(ip_address=ip_address).order_by('-created_at')

    sessions_data = []
    for s in sessions[:20]:
        sessions_data.append({
            'first_visit': s.first_visit.strftime('%d/%m/%Y %H:%M'),
            'last_activity': s.last_activity.strftime('%d/%m/%Y %H:%M') if s.last_activity else '',
            'device_type': s.device_type,
            'browser': s.browser,
            'os': s.os,
            'page_views': s.page_views,
            'landing_page': s.landing_page,
            'username': s.user.username if s.user else None,
        })

    likes_data = []
    for like in likes[:20]:
        likes_data.append({
            'postcard_number': like.postcard.number if like.postcard else 'N/A',
            'is_animated': like.is_animated_like,
            'created_at': like.created_at.strftime('%d/%m/%Y %H:%M'),
        })

    searches_data = []
    for search in searches[:20]:
        searches_data.append({
            'keyword': search.keyword,
            'results_count': search.results_count,
            'created_at': search.created_at.strftime('%d/%m/%Y %H:%M'),
        })

    return JsonResponse({
        'ip_address': ip_address,
        'location': {
            'country': location.get('country', 'Unknown'),
            'country_code': location.get('country_code', ''),
            'city': location.get('city', 'Unknown'),
            'region': location.get('region', ''),
            'latitude': location.get('latitude'),
            'longitude': location.get('longitude'),
            'timezone': location.get('timezone', ''),
            'isp': location.get('isp', ''),
            'is_vpn': location.get('is_vpn', False),
            'is_proxy': location.get('is_proxy', False),
            'flag': get_country_flag_emoji(location.get('country_code', '')),
        },
        'total_sessions': sessions.count(),
        'total_page_views': page_views.count(),
        'total_likes': likes.count(),
        'total_searches': searches.count(),
        'sessions': sessions_data,
        'likes': likes_data,
        'searches': searches_data,
    })


@user_passes_test(is_admin)
def admin_postcard_analytics(request, postcard_id):
    """API endpoint for detailed postcard analytics"""
    from .utils import get_country_flag_emoji

    try:
        postcard = Postcard.objects.get(id=postcard_id)
    except Postcard.DoesNotExist:
        return JsonResponse({'error': 'Postcard not found'}, status=404)

    # Get likes with details
    likes = PostcardLike.objects.filter(postcard=postcard).order_by('-created_at')

    likes_by_country = list(
        likes.exclude(country='').values('country')
        .annotate(count=Count('id'))
        .order_by('-count')[:10]
    )
    for c in likes_by_country:
        c['flag'] = get_country_flag_emoji(c.get('country', '')[:2])

    likes_by_device = list(
        likes.exclude(device_type='').values('device_type')
        .annotate(count=Count('id'))
        .order_by('-count')
    )

    # Recent likes
    recent_likes = []
    for like in likes[:20]:
        recent_likes.append({
            'user': like.user.username if like.user else 'Anonyme',
            'ip_address': like.ip_address or 'N/A',
            'country': like.country or 'Unknown',
            'city': like.city or 'Unknown',
            'device_type': like.device_type or 'Unknown',
            'browser': like.browser or 'Unknown',
            'is_animated': like.is_animated_like,
            'created_at': like.created_at.strftime('%d/%m/%Y %H:%M'),
            'flag': get_country_flag_emoji(like.country[:2] if like.country else ''),
        })

    # Daily likes trend (last 30 days)
    today = timezone.now().date()
    daily_likes = []
    for i in range(30):
        date = today - timedelta(days=29 - i)
        count = likes.filter(created_at__date=date).count()
        daily_likes.append({
            'date': date.strftime('%d/%m'),
            'count': count
        })

    # Get interactions
    interactions = PostcardInteraction.objects.filter(postcard=postcard)
    interaction_types = list(
        interactions.values('interaction_type')
        .annotate(count=Count('id'))
        .order_by('-count')
    )

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
        'likes_total': likes.count(),
        'likes_by_country': likes_by_country,
        'likes_by_device': likes_by_device,
        'recent_likes': recent_likes,
        'daily_likes': daily_likes,
        'interaction_types': interaction_types,
    })


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


@user_passes_test(is_admin)
def admin_realtime_api(request):
    """API endpoint for real-time visitor data"""
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

    for v in data['visitors']:
        if v['last_activity']:
            v['last_activity'] = v['last_activity'].strftime('%H:%M:%S')

    return JsonResponse(data)


@user_passes_test(is_admin)
def admin_geographic_api(request):
    """API endpoint for geographic analytics"""
    return JsonResponse({'countries': [], 'cities': []})


@user_passes_test(is_admin)
def admin_ip_lookup(request, ip_address):
    """API endpoint to lookup IP address details"""
    return JsonResponse({
        'ip_address': ip_address,
        'location': {},
        'total_sessions': 0,
        'total_page_views': 0,
        'sessions': [],
    })


@user_passes_test(is_admin)
def admin_postcard_analytics(request, postcard_id):
    """API endpoint for detailed postcard analytics"""
    try:
        postcard = Postcard.objects.get(id=postcard_id)
    except Postcard.DoesNotExist:
        return JsonResponse({'error': 'Postcard not found'}, status=404)

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
        'interaction_types': {},
        'country_breakdown': [],
        'device_breakdown': {},
        'daily_views': [],
        'recent_likes': [],
    })


@user_passes_test(is_admin)
def admin_export_data(request):
    """Export analytics data as CSV"""
    import csv

    export_type = request.GET.get('type', 'sessions')

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="export_{export_type}.csv"'

    writer = csv.writer(response)
    writer.writerow(['No data available'])

    return response


@user_passes_test(is_admin)
@require_http_methods(["POST"])
def admin_upload_media(request):
    """Admin endpoint to upload media files."""
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


# ============================================
# DEBUG VIEWS
# ============================================

def debug_postcard_images(request, postcard_id):
    """Debug endpoint to check image paths for a postcard"""
    try:
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
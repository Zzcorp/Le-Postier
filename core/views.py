from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import login, authenticate
from django.contrib import messages
from django.db.models import Q, Count, Sum
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from datetime import datetime, timedelta
import json

from .models import (
    CustomUser, Postcard, Theme, ContactMessage,
    SearchLog, PageView, UserActivity, SystemLog, IntroSeen
)
from .forms import ContactForm, SimpleRegistrationForm
from django.http import JsonResponse

def health_check(request):
    """Health check endpoint for Render"""
    return JsonResponse({
        'status': 'healthy',
        'service': 'le-postier',
        'timestamp': timezone.now().isoformat()
    })

def check_intro_needed(request):
    """Check if intro animation should be shown"""
    session_key = request.session.session_key
    if not session_key:
        request.session.create()
        session_key = request.session.session_key

    today = timezone.now().date()

    # Check if user has seen intro today
    if request.user.is_authenticated:
        if request.user.last_visit_date != today:
            request.user.last_visit_date = today
            request.user.save(update_fields=['last_visit_date'])
            return True
    else:
        # Check session-based intro tracking
        intro_seen = IntroSeen.objects.filter(
            session_key=session_key,
            date_seen=today
        ).exists()

        if not intro_seen:
            IntroSeen.objects.update_or_create(
                session_key=session_key,
                defaults={'date_seen': today}
            )
            return True

    return False


def intro_view(request):
    """Show intro animation"""
    # Determine where to redirect after intro
    next_url = request.GET.get('next', '/')

    context = {
        'redirect_url': next_url
    }
    return render(request, 'intro.html', context)


def home(request):
    """Home page view"""
    # Check if intro is needed
    if check_intro_needed(request):
        return redirect('intro')

    log_page_view(request, 'Accueil')
    return render(request, 'home.html')


def log_page_view(request, page_name):
    """Helper function to log page views"""
    ip_address = request.META.get('HTTP_X_FORWARDED_FOR')
    if ip_address:
        ip_address = ip_address.split(',')[0]
    else:
        ip_address = request.META.get('REMOTE_ADDR')

    PageView.objects.create(
        page_name=page_name,
        user=request.user if request.user.is_authenticated else None,
        ip_address=ip_address,
        user_agent=request.META.get('HTTP_USER_AGENT', ''),
        session_key=request.session.session_key or ''
    )


def browse(request):
    """Browse page with search functionality"""
    log_page_view(request, 'Parcourir')

    query = request.GET.get('keywords_input', '').strip()
    postcards = Postcard.objects.all()
    themes = Theme.objects.all().prefetch_related('postcards')

    # Filter based on user permissions
    if not request.user.is_authenticated:
        postcards = postcards.exclude(rarity='very_rare')
    elif request.user.is_authenticated and not request.user.can_view_very_rare():
        postcards = postcards.exclude(rarity='very_rare')

    if query:
        # Search in title, description, and keywords
        postcards = postcards.filter(
            Q(title__icontains=query) |
            Q(description__icontains=query) |
            Q(keywords__icontains=query)
        )

        # Log the search
        ip_address = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR'))
        SearchLog.objects.create(
            keyword=query,
            results_count=postcards.count(),
            user=request.user if request.user.is_authenticated else None,
            ip_address=ip_address
        )

    # Exclude very rare postcards for non-members in slideshow
    if request.user.is_authenticated and request.user.can_view_very_rare():
        slideshow_postcards = postcards
    else:
        slideshow_postcards = postcards.exclude(rarity='very_rare')

    context = {
        'postcards': postcards[:50],  # Limit to 50 for performance
        'slideshow_postcards': slideshow_postcards[:20],  # Limit slideshow
        'themes': themes,
        'query': query,
        'total_count': postcards.count(),
    }

    return render(request, 'browse.html', context)


def get_postcard_detail(request, postcard_id):
    """AJAX endpoint to get postcard details"""
    postcard = get_object_or_404(Postcard, id=postcard_id)

    # Log view
    postcard.views_count += 1
    postcard.save(update_fields=['views_count'])

    if request.user.is_authenticated:
        UserActivity.objects.create(
            user=request.user,
            action='postcard_view',
            details=f"Viewed postcard {postcard.number}",
            ip_address=request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR'))
        )

    # Clean title by replacing backslashes with quotes
    clean_title = postcard.title.replace('\\', '"')

    data = {
        'number': postcard.number,
        'title': clean_title,
        'description': postcard.description,
        'grande_image': postcard.grande_image.url if postcard.grande_image else '',
        'dos_image': postcard.dos_image.url if postcard.dos_image else '',
        'zoom_image': postcard.zoom_image.url if postcard.zoom_image else postcard.grande_image.url if postcard.grande_image else '',
        'rarity': postcard.rarity,
    }

    return JsonResponse(data)


def zoom_postcard(request, postcard_id):
    """Zoom view for authenticated users"""
    postcard = get_object_or_404(Postcard, id=postcard_id)

    # Check if user can view very rare postcards
    can_view = True
    if postcard.rarity == 'very_rare':
        if not request.user.is_authenticated or not request.user.can_view_very_rare():
            can_view = False

    if can_view and request.user.is_authenticated:
        postcard.zoom_count += 1
        postcard.save(update_fields=['zoom_count'])

        UserActivity.objects.create(
            user=request.user,
            action='postcard_zoom',
            details=f"Zoomed postcard {postcard.number}",
            ip_address=request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR'))
        )

    zoom_url = ''
    if can_view:
        if postcard.zoom_image:
            zoom_url = postcard.zoom_image.url
        elif postcard.grande_image:
            zoom_url = postcard.grande_image.url

    data = {
        'can_view': can_view,
        'zoom_image': zoom_url,
        'grande_image': postcard.grande_image.url if postcard.grande_image else '',
        'dos_image': postcard.dos_image.url if postcard.dos_image else '',
    }

    return JsonResponse(data)


def gallery(request):
    """Gallery page - découvrir"""
    log_page_view(request, 'Galerie')

    # Get postcards based on user permissions
    postcards = Postcard.objects.all()

    if not request.user.is_authenticated:
        postcards = postcards.exclude(rarity='very_rare')
    elif not request.user.can_view_very_rare():
        postcards = postcards.exclude(rarity='very_rare')

    # Get featured or random selection
    featured_postcards = postcards.order_by('?')[:20]

    context = {
        'postcards': featured_postcards,
    }

    return render(request, 'gallery.html', context)


def presentation(request):
    """Presentation page"""
    log_page_view(request, 'Présentation')
    return render(request, 'presentation.html')


def contact(request):
    """Contact page"""
    log_page_view(request, 'Contact')

    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            contact_message = form.save(commit=False)

            # Get IP address
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                contact_message.ip_address = x_forwarded_for.split(',')[0]
            else:
                contact_message.ip_address = request.META.get('REMOTE_ADDR')

            if request.user.is_authenticated:
                contact_message.user = request.user
                UserActivity.objects.create(
                    user=request.user,
                    action='contact',
                    details='Sent contact message',
                    ip_address=contact_message.ip_address
                )

            contact_message.save()

            messages.success(request, 'Carte envoyée avec succès!')
            return redirect('contact')
    else:
        form = ContactForm()

    return render(request, 'contact.html', {'form': form})


def register(request):
    """Simple registration - only username and email"""
    if request.user.is_authenticated:
        return redirect('browse')

    if request.method == 'POST':
        form = SimpleRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()

            UserActivity.objects.create(
                user=user,
                action='register',
                details='New registration',
                ip_address=request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR'))
            )

            messages.success(
                request,
                'Inscription réussie! Un email vous a été envoyé pour vous connecter.'
            )
            return redirect('home')
    else:
        form = SimpleRegistrationForm()

    return render(request, 'register.html', {'form': form})


def login_view(request):
    """Custom login view"""
    if request.user.is_authenticated:
        return redirect('browse')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)

            # Log activity
            UserActivity.objects.create(
                user=user,
                action='login',
                details='User logged in',
                ip_address=request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR'))
            )

            messages.success(request, f'Bienvenue {user.username}!')
            return redirect('browse')
        else:
            messages.error(request, 'Nom d\'utilisateur ou mot de passe incorrect.')

    return render(request, 'login.html')


@user_passes_test(lambda u: u.is_staff)
def admin_dashboard(request):
    """Admin dashboard view"""
    log_page_view(request, 'Admin Dashboard')

    # Get statistics
    total_users = CustomUser.objects.count()
    verified_users = CustomUser.objects.filter(email_verified=True).count()
    unverified_users = total_users - verified_users

    total_postcards = Postcard.objects.count()
    common_postcards = Postcard.objects.filter(rarity='common').count()
    rare_postcards = Postcard.objects.filter(rarity='rare').count()
    very_rare_postcards = Postcard.objects.filter(rarity='very_rare').count()

    # Today's views
    today = timezone.now().date()
    today_views = PageView.objects.filter(timestamp__date=today).count()
    unique_visitors = PageView.objects.filter(
        timestamp__date=today
    ).values('ip_address').distinct().count()

    # Searches
    total_searches = SearchLog.objects.count()
    top_searches = SearchLog.objects.values('keyword').annotate(
        count=Count('id')
    ).order_by('-count')[:1]
    top_search = top_searches[0]['keyword'] if top_searches else 'N/A'

    # Recent data
    recent_users = CustomUser.objects.order_by('-last_activity')[:10]
    recent_searches = SearchLog.objects.order_by('-created_at')[:20]
    system_logs = SystemLog.objects.order_by('-timestamp')[:50]

    # Chart data for last 7 days
    chart_labels = []
    chart_data = []
    for i in range(6, -1, -1):
        date = today - timedelta(days=i)
        chart_labels.append(date.strftime('%d/%m'))
        chart_data.append(
            PageView.objects.filter(timestamp__date=date).count()
        )

    context = {
        'total_users': total_users,
        'verified_users': verified_users,
        'unverified_users': unverified_users,
        'total_postcards': total_postcards,
        'common_postcards': common_postcards,
        'rare_postcards': rare_postcards,
        'very_rare_postcards': very_rare_postcards,
        'today_views': today_views,
        'unique_visitors': unique_visitors,
        'total_searches': total_searches,
        'top_search': top_search,
        'recent_users': recent_users,
        'recent_searches': recent_searches,
        'system_logs': system_logs,
        'chart_labels': json.dumps(chart_labels),
        'chart_data': json.dumps(chart_data),
        'user_categories': CustomUser.USER_CATEGORIES,
    }

    return render(request, 'admin_dashboard.html', context)


@user_passes_test(lambda u: u.is_staff)
@require_http_methods(["POST"])
def update_user_category(request, user_id):
    """Update user category - AJAX endpoint"""
    try:
        user = get_object_or_404(CustomUser, id=user_id)
        data = json.loads(request.body)
        category = data.get('category')

        if category in dict(CustomUser.USER_CATEGORIES):
            user.category = category
            if category != 'subscribed_unverified':
                user.email_verified = True
            user.save()

            SystemLog.objects.create(
                level='INFO',
                message=f"User {user.username} category updated to {category}",
                user=request.user
            )

            return JsonResponse({'success': True})
        else:
            return JsonResponse({'success': False, 'error': 'Invalid category'}, status=400)
    except Exception as e:
        SystemLog.objects.create(
            level='ERROR',
            message=f"Error updating user category: {str(e)}",
            user=request.user
        )
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@user_passes_test(lambda u: u.is_staff)
@require_http_methods(["DELETE"])
def delete_user(request, user_id):
    """Delete user - AJAX endpoint"""
    try:
        user = get_object_or_404(CustomUser, id=user_id)
        if not user.is_staff:
            username = user.username
            user.delete()

            SystemLog.objects.create(
                level='WARNING',
                message=f"User {username} deleted by {request.user.username}",
                user=request.user
            )

            return JsonResponse({'success': True})
        return JsonResponse({'success': False, 'message': 'Cannot delete staff user'}, status=400)
    except Exception as e:
        SystemLog.objects.create(
            level='ERROR',
            message=f"Error deleting user: {str(e)}",
            user=request.user
        )
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


# Additional utility functions for admin
@user_passes_test(lambda u: u.is_staff)
def export_data(request):
    """Export data to CSV - for admin use"""
    import csv
    from django.http import HttpResponse

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="postcards_export.csv"'

    writer = csv.writer(response)
    writer.writerow(['Number', 'Title', 'Description', 'Keywords', 'Rarity', 'Views', 'Zooms'])

    postcards = Postcard.objects.all()
    for postcard in postcards:
        writer.writerow([
            postcard.number,
            postcard.title,
            postcard.description,
            postcard.keywords,
            postcard.rarity,
            postcard.views_count,
            postcard.zoom_count
        ])

    return response


@user_passes_test(lambda u: u.is_staff)
def clear_cache(request):
    """Clear cache - for admin use"""
    from django.core.cache import cache
    cache.clear()

    SystemLog.objects.create(
        level='INFO',
        message='Cache cleared',
        user=request.user
    )

    messages.success(request, 'Cache vidé avec succès')
    return redirect('admin_dashboard')
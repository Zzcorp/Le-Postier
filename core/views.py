from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Q
from django.utils import timezone
import traceback

from .models import (
    CustomUser, Postcard, Theme, ContactMessage,
    SearchLog, PageView, UserActivity, SystemLog, IntroSeen
)
from .forms import ContactForm, SimpleRegistrationForm


def home(request):
    """Home page view"""
    try:
        return render(request, 'home.html')
    except Exception as e:
        return HttpResponse(f"<h1>Home Error</h1><pre>{traceback.format_exc()}</pre>")


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

        # Get postcards with images for slideshow
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
        return HttpResponse(f"""
            <h1>Browse Page Error</h1>
            <pre style="background:#ffeeee;padding:20px;white-space:pre-wrap;">{traceback.format_exc()}</pre>
            <p><a href="/">Back to Home</a></p>
        """)


def gallery(request):
    """Gallery page"""
    try:
        # Get postcards that have images
        postcards = Postcard.objects.exclude(
            vignette_url=''
        ).exclude(
            vignette_url__isnull=True
        ).order_by('?')[:50]  # Random 50 postcards

        context = {
            'postcards': postcards,
            'user': request.user,
        }

        return render(request, 'gallery.html', context)

    except Exception as e:
        return HttpResponse(f"""
            <h1>Gallery Page Error</h1>
            <pre style="background:#ffeeee;padding:20px;white-space:pre-wrap;">{traceback.format_exc()}</pre>
            <p><a href="/">Back to Home</a></p>
        """)


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
                return render(request, 'register.html', {'success': True})
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
                from django.shortcuts import redirect
                return redirect(next_url)
            else:
                error = "Nom d'utilisateur ou mot de passe incorrect."

        return render(request, 'login.html', {'error': error})

    except Exception as e:
        return HttpResponse(f"<h1>Login Error</h1><pre>{traceback.format_exc()}</pre>")


def logout_view(request):
    """Logout"""
    logout(request)
    from django.shortcuts import redirect
    return redirect('home')


def get_postcard_detail(request, postcard_id):
    """API endpoint for postcard details"""
    try:
        postcard = Postcard.objects.get(id=postcard_id)

        # Increment view count
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
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


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


@user_passes_test(lambda u: u.is_staff if u.is_authenticated else False)
def admin_dashboard(request):
    """Admin dashboard"""
    try:
        context = {
            'total_users': CustomUser.objects.count(),
            'total_postcards': Postcard.objects.count(),
            'total_themes': Theme.objects.count(),
            'recent_users': CustomUser.objects.order_by('-date_joined')[:10],
            'recent_searches': SearchLog.objects.order_by('-created_at')[:10],
        }
        return render(request, 'admin_dashboard.html', context)
    except Exception as e:
        return HttpResponse(f"<h1>Admin Error</h1><pre>{traceback.format_exc()}</pre>")


def update_user_category(request, user_id):
    """Update user category (admin only)"""
    if not request.user.is_staff:
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    try:
        import json
        data = json.loads(request.body)
        user = CustomUser.objects.get(id=user_id)
        user.category = data.get('category', user.category)
        user.save()
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def delete_user(request, user_id):
    """Delete user (admin only)"""
    if not request.user.is_staff:
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    try:
        user = CustomUser.objects.get(id=user_id)
        if not user.is_staff:
            user.delete()
            return JsonResponse({'success': True})
        return JsonResponse({'error': 'Cannot delete staff'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
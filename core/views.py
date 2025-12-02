from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Q, Count
from django.utils import timezone
from datetime import datetime, timedelta
import json

from .models import (
    CustomUser, Postcard, Theme, ContactMessage,
    SearchLog, PageView, UserActivity, SystemLog, IntroSeen
)
from .forms import ContactForm, SimpleRegistrationForm


def home(request):
    """Home page view - NO REDIRECTS"""
    # Try to render template
    try:
        return render(request, 'home.html')
    except:
        # If template fails, return simple HTML
        return HttpResponse("""
            <!DOCTYPE html>
            <html>
            <head><title>Le Postier</title></head>
            <body>
                <h1>Le Postier - Home</h1>
                <p>Site is loading...</p>
                <a href="/admin/">Admin</a>
            </body>
            </html>
        """)


def browse(request):
    """Browse page - NO LOGIN REQUIRED"""
    query = request.GET.get('keywords_input', '').strip()

    # Get all postcards - no filtering by user
    postcards = Postcard.objects.all()
    themes = Theme.objects.all()

    if query:
        postcards = postcards.filter(
            Q(title__icontains=query) |
            Q(keywords__icontains=query)
        )

    context = {
        'postcards': postcards[:50],
        'themes': themes,
        'query': query,
        'total_count': postcards.count(),
        'slideshow_postcards': postcards[:20],
    }

    try:
        return render(request, 'browse.html', context)
    except:
        return HttpResponse("Browse page - template error")


def gallery(request):
    """Gallery page"""
    postcards = Postcard.objects.all()[:20]

    context = {
        'postcards': postcards,
    }

    try:
        return render(request, 'gallery.html', context)
    except:
        return HttpResponse("Gallery page - template error")


def presentation(request):
    """Presentation page"""
    try:
        return render(request, 'presentation.html')
    except:
        return HttpResponse("Presentation page - template error")


def contact(request):
    """Contact page"""
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            form.save()
            return HttpResponse("Message sent!")
    else:
        form = ContactForm()

    try:
        return render(request, 'contact.html', {'form': form})
    except:
        return HttpResponse("Contact page - template error")


def register(request):
    """Registration page - NO REDIRECT if already logged in"""
    if request.method == 'POST':
        form = SimpleRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            return HttpResponse("Registration successful! <a href='/'>Home</a>")
    else:
        form = SimpleRegistrationForm()

    try:
        return render(request, 'register.html', {'form': form})
    except:
        return HttpResponse("Register page - template error")


def login_view(request):
    """Login page - NO REDIRECT if already logged in"""
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return HttpResponse(f"Logged in as {user.username}! <a href='/'>Home</a>")

    try:
        return render(request, 'login.html')
    except:
        return HttpResponse("""
            <form method="post">
                <input type="text" name="username" placeholder="Username">
                <input type="password" name="password" placeholder="Password">
                <button type="submit">Login</button>
            </form>
        """)


def logout_view(request):
    """Logout and return to home"""
    logout(request)
    return HttpResponse("Logged out! <a href='/'>Home</a>")


def get_postcard_detail(request, postcard_id):
    """API endpoint"""
    try:
        postcard = Postcard.objects.get(id=postcard_id)
        data = {
            'number': postcard.number,
            'title': postcard.title,
            'rarity': postcard.rarity,
        }
        return JsonResponse(data)
    except:
        return JsonResponse({'error': 'Not found'}, status=404)


def zoom_postcard(request, postcard_id):
    """API endpoint"""
    return JsonResponse({'can_view': True})


# REMOVE or comment out these functions that cause redirects:
def intro_view(request):
    """Intro disabled"""
    return HttpResponse("Intro disabled")


def check_intro_needed(request):
    """Always return False to avoid redirects"""
    return False


# Admin dashboard - only if staff
@user_passes_test(lambda u: u.is_staff if u.is_authenticated else False)
def admin_dashboard(request):
    """Admin dashboard"""
    return HttpResponse("Admin Dashboard - You are staff!")


# Dummy functions for missing views
def update_user_category(request, user_id):
    return JsonResponse({'success': True})


def delete_user(request, user_id):
    return JsonResponse({'success': True})


def log_page_view(request, page_name):
    """Simple page view logger"""
    pass
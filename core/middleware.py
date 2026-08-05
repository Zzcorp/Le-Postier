# core/middleware.py
"""
Middleware for Le Postier - analytics tracking.

Media is served by nginx in production and by django.conf.urls.static in
development (see le_postier/urls.py) — the old MediaServeMiddleware is gone.
"""

import logging

from django.utils import timezone
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger(__name__)


class AnalyticsTrackingMiddleware(MiddlewareMixin):
    """
    Track page views and visitor sessions.

    Cost discipline:
    - bots / static / media / API paths bail out before any session or DB work;
    - ONE IP-geolocation lookup per request, shared by the three trackers;
    - the lookup is cache-only (IPLocation table); on a miss an empty location
      is recorded and a daemon thread resolves the IP for next time.
    """

    # Paths to exclude from tracking
    EXCLUDED_PATHS = [
        '/api/',
        '/admin/',
        '/static/',
        '/media/',
        '/favicon.ico',
        '/robots.txt',
        '/sitemap.xml',
        '/__debug__/',
    ]

    # Paths to track with custom names
    PAGE_NAMES = {
        '/': 'Accueil',
        '/parcourir/': 'Parcourir',
        '/cp-animes/': 'CP Animées',
        '/presentation/': 'Présentation',
        '/decouvrir/': 'Découvrir',
        '/contact/': 'Contact',
        '/la-poste/': 'La Poste',
        '/profil/': 'Profil',
        '/connexion/': 'Connexion',
        '/inscription/': 'Inscription',
        '/tableau-de-bord/': 'Tableau de bord',
    }

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        try:
            self.track(request, response)
        except Exception as e:
            logger.error(f"[AnalyticsTracking] Error tracking request: {e}")

        return response

    def should_track(self, request, response):
        """Cheap request/response checks — no DB, no session, no parsing."""
        if request.method != 'GET':
            return False

        if response.status_code != 200:
            return False

        for excluded in self.EXCLUDED_PATHS:
            if request.path.startswith(excluded):
                return False

        # Don't track AJAX requests
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return False

        # Don't track if response is not HTML
        content_type = response.get('Content-Type', '')
        if 'text/html' not in content_type:
            return False

        return True

    def track(self, request, response):
        from .utils import get_client_ip, get_location_from_ip, parse_user_agent_string

        if not self.should_track(request, response):
            return

        user_agent = request.META.get('HTTP_USER_AGENT', '')
        ua_info = parse_user_agent_string(user_agent)

        # Bot bailout before any session or DB work
        if ua_info.get('is_bot'):
            return

        if not request.session.session_key:
            request.session.create()
        session_key = request.session.session_key

        ip_address = get_client_ip(request)
        # Single, cache-only lookup shared by the three trackers
        location = get_location_from_ip(ip_address)

        self.track_page_view(request, ip_address, location, ua_info, user_agent, session_key)
        self.update_visitor_session(request, ip_address, location, ua_info, user_agent, session_key)
        self.update_realtime_visitor(request, ip_address, location, ua_info, session_key)

    def track_page_view(self, request, ip_address, location, ua_info, user_agent, session_key):
        """Record a page view"""
        try:
            from .models import PageView

            page_name = self.PAGE_NAMES.get(request.path, request.path)

            PageView.objects.create(
                page_name=page_name,
                page_url=request.path,
                user=request.user if request.user.is_authenticated else None,
                ip_address=ip_address,
                user_agent=user_agent[:500] if user_agent else '',
                session_key=session_key,
                referrer=request.META.get('HTTP_REFERER', '')[:500],
                country=location.get('country', ''),
                city=location.get('city', ''),
                device_type=ua_info.get('device_type', ''),
                browser=ua_info.get('browser', ''),
                os=ua_info.get('os', ''),
            )
        except Exception as e:
            logger.error(f"[AnalyticsTracking] Error tracking page view: {e}")

    def update_visitor_session(self, request, ip_address, location, ua_info, user_agent, session_key):
        """Update or create visitor session"""
        try:
            from .models import VisitorSession

            session, created = VisitorSession.objects.get_or_create(
                session_key=session_key,
                defaults={
                    'user': request.user if request.user.is_authenticated else None,
                    'ip_address': ip_address,
                    'country': location.get('country', ''),
                    'country_code': location.get('country_code', ''),
                    'city': location.get('city', ''),
                    'region': location.get('region', ''),
                    'latitude': location.get('latitude'),
                    'longitude': location.get('longitude'),
                    'timezone': location.get('timezone', ''),
                    'isp': location.get('isp', ''),
                    'user_agent': user_agent[:500] if user_agent else '',
                    'device_type': ua_info.get('device_type', ''),
                    'browser': ua_info.get('browser', ''),
                    'browser_version': ua_info.get('browser_version', ''),
                    'os': ua_info.get('os', ''),
                    'os_version': ua_info.get('os_version', ''),
                    'referrer': request.META.get('HTTP_REFERER', '')[:500],
                    'referrer_domain': self.extract_domain(request.META.get('HTTP_REFERER', '')),
                    'landing_page': request.path,
                    'is_bot': ua_info.get('is_bot', False),
                    'session_start': timezone.now(),
                }
            )

            # Update existing session
            if not created:
                session.page_views += 1
                session.exit_page = request.path
                session.session_end = timezone.now()

                # Update user if they logged in
                if request.user.is_authenticated and not session.user:
                    session.user = request.user

                session.save(update_fields=[
                    'page_views', 'exit_page', 'session_end', 'last_activity', 'user'
                ])

            # Check if returning visitor
            if created:
                previous_sessions = VisitorSession.objects.filter(
                    ip_address=ip_address
                ).exclude(session_key=session_key).exists()

                if previous_sessions:
                    session.is_returning = True
                    session.save(update_fields=['is_returning'])

        except Exception as e:
            logger.error(f"[AnalyticsTracking] Error updating session: {e}")

    def update_realtime_visitor(self, request, ip_address, location, ua_info, session_key):
        """Update real-time visitor tracking"""
        try:
            from .models import RealTimeVisitor

            page_name = self.PAGE_NAMES.get(request.path, request.path)

            RealTimeVisitor.objects.update_or_create(
                session_key=session_key,
                defaults={
                    'user': request.user if request.user.is_authenticated else None,
                    'ip_address': ip_address,
                    'country': location.get('country', ''),
                    'city': location.get('city', ''),
                    'current_page': request.path,
                    'page_title': page_name,
                    'device_type': ua_info.get('device_type', ''),
                    'browser': ua_info.get('browser', ''),
                }
            )
        except Exception as e:
            logger.error(f"[AnalyticsTracking] Error updating realtime visitor: {e}")

    def extract_domain(self, url):
        """Extract domain from URL"""
        if not url:
            return ''
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            return parsed.netloc[:200]
        except Exception:
            return ''

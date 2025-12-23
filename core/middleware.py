# core/middleware.py
from django.utils import timezone
from django.conf import settings
import re


class MediaServeMiddleware:
    """Middleware to serve media files from persistent disk on Render"""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        return response


class AnalyticsTrackingMiddleware:
    """Enhanced middleware to track visitor sessions and page views"""

    EXCLUDED_PATHS = [
        '/static/',
        '/media/',
        '/admin/jsi18n/',
        '/favicon.ico',
        '/robots.txt',
        '/sitemap.xml',
        '/__debug__/',
        '/api/admin/realtime/',
    ]

    BOT_PATTERNS = [
        'bot', 'crawler', 'spider', 'scraper', 'curl', 'wget',
        'python-requests', 'java', 'apache-http', 'okhttp',
        'googlebot', 'bingbot', 'slurp', 'duckduckbot', 'baiduspider',
        'yandexbot', 'facebookexternalhit', 'twitterbot', 'linkedinbot',
        'whatsapp', 'telegram', 'discord', 'slack',
    ]

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Skip excluded paths
        path = request.path.lower()
        if any(path.startswith(excluded) for excluded in self.EXCLUDED_PATHS):
            return self.get_response(request)

        # Skip if it looks like a static file
        if re.search(r'\.(css|js|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot|map)$', path, re.I):
            return self.get_response(request)

        # Track the visit
        self.track_visit(request)

        response = self.get_response(request)

        # Update session end time after response
        self.update_session_end(request)

        return response

    def is_bot(self, user_agent):
        """Check if user agent is a bot"""
        if not user_agent:
            return False
        ua_lower = user_agent.lower()
        return any(bot in ua_lower for bot in self.BOT_PATTERNS)

    def track_visit(self, request):
        """Track page view and session"""
        try:
            from .models import PageView, VisitorSession, RealTimeVisitor
            from .utils import get_client_ip, get_location_from_ip, parse_user_agent_string

            # Ensure session exists
            if not request.session.session_key:
                request.session.create()

            session_key = request.session.session_key
            ip_address = get_client_ip(request)
            user_agent = request.META.get('HTTP_USER_AGENT', '')

            # Skip bots
            if self.is_bot(user_agent):
                return

            # Get location and device info
            location = get_location_from_ip(ip_address)
            ua_info = parse_user_agent_string(user_agent)

            # Get or create visitor session
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
                    'user_agent': user_agent,
                    'device_type': ua_info.get('device_type', ''),
                    'browser': ua_info.get('browser', ''),
                    'browser_version': ua_info.get('browser_version', ''),
                    'os': ua_info.get('os', ''),
                    'os_version': ua_info.get('os_version', ''),
                    'is_bot': ua_info.get('is_bot', False),
                    'referrer': request.META.get('HTTP_REFERER', '')[:500] if request.META.get('HTTP_REFERER') else '',
                    'landing_page': request.path[:500],
                    'session_start': timezone.now(),
                }
            )

            if not created:
                # Update existing session
                session.page_views += 1
                session.last_activity = timezone.now()
                session.actions_count += 1

                # Calculate time spent
                if session.session_start:
                    delta = timezone.now() - session.session_start
                    session.total_time_spent = int(delta.total_seconds())

                # Update user if logged in
                if request.user.is_authenticated and not session.user:
                    session.user = request.user

                # Check if returning visitor
                previous_sessions = VisitorSession.objects.filter(
                    ip_address=ip_address
                ).exclude(id=session.id).exists()
                session.is_returning = previous_sessions

                session.save()
            else:
                session.page_views = 1
                session.save()

            # Get page title from path
            page_title = self.get_page_title(request.path)

            # Create page view record
            PageView.objects.create(
                page_name=page_title,
                page_url=request.path,
                user=request.user if request.user.is_authenticated else None,
                ip_address=ip_address,
                user_agent=user_agent,
                session_key=session_key,
                referrer=request.META.get('HTTP_REFERER', '')[:500] if request.META.get('HTTP_REFERER') else '',
                country=location.get('country', ''),
                city=location.get('city', ''),
                device_type=ua_info.get('device_type', ''),
                browser=ua_info.get('browser', ''),
                os=ua_info.get('os', ''),
            )

            # Update real-time visitor
            RealTimeVisitor.objects.update_or_create(
                session_key=session_key,
                defaults={
                    'user': request.user if request.user.is_authenticated else None,
                    'ip_address': ip_address,
                    'country': location.get('country', ''),
                    'city': location.get('city', ''),
                    'current_page': request.path,
                    'page_title': page_title,
                    'device_type': ua_info.get('device_type', ''),
                    'browser': ua_info.get('browser', ''),
                    'last_activity': timezone.now(),
                }
            )

        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Analytics tracking error: {e}")

    def update_session_end(self, request):
        """Update session end time"""
        try:
            from .models import VisitorSession

            if not request.session.session_key:
                return

            session_key = request.session.session_key

            VisitorSession.objects.filter(session_key=session_key).update(
                session_end=timezone.now(),
                last_activity=timezone.now()
            )
        except Exception:
            pass

    def get_page_title(self, path):
        """Get page title from path"""
        titles = {
            '/': 'Accueil',
            '/parcourir/': 'Parcourir',
            '/browse/': 'Parcourir',
            '/cp-animes/': 'CP Animées',
            '/presentation/': 'Présentation',
            '/decouvrir/': 'Découvrir',
            '/contact/': 'Contact',
            '/la-poste/': 'La Poste',
            '/profil/': 'Profil',
            '/connexion/': 'Connexion',
            '/inscription/': 'Inscription',
            '/tableau-de-bord/': 'Admin Dashboard',
        }
        return titles.get(path, path.strip('/').replace('-', ' ').title() or 'Page')
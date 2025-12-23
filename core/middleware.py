# core/middleware.py
"""
Middleware for Le Postier - Media serving and analytics tracking
"""

import os
import mimetypes
from pathlib import Path
from django.http import HttpResponse, FileResponse, Http404
from django.conf import settings
from django.utils import timezone
from django.utils.deprecation import MiddlewareMixin
import logging

logger = logging.getLogger(__name__)


def get_media_root():
    """Get the correct media root path - always use persistent disk on Render"""
    if os.environ.get('RENDER', 'false').lower() == 'true' or Path('/var/data').exists():
        return Path('/var/data/media')
    return Path(settings.MEDIA_ROOT)


class MediaServeMiddleware(MiddlewareMixin):
    """
    Middleware to serve media files from the Render persistent disk.
    This is needed because Render's persistent disk is mounted at /var/data,
    not at the default Django media location.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.media_url = settings.MEDIA_URL.rstrip('/')
        self.media_root = get_media_root()
        logger.info(f"[MediaServeMiddleware] Initialized with MEDIA_ROOT={self.media_root}")

    def __call__(self, request):
        # Check if this is a media request
        if request.path.startswith(self.media_url + '/'):
            response = self.serve_media(request)
            if response:
                return response

        return self.get_response(request)

    def serve_media(self, request):
        """Serve a media file from the persistent disk"""
        # Get the relative path after /media/
        relative_path = request.path[len(self.media_url) + 1:]

        # Security: prevent directory traversal
        if '..' in relative_path or relative_path.startswith('/'):
            logger.warning(f"[MediaServeMiddleware] Blocked suspicious path: {relative_path}")
            return None

        # Construct the full file path
        file_path = self.media_root / relative_path

        # Log the lookup for debugging
        logger.debug(f"[MediaServeMiddleware] Looking for: {file_path}")

        # Check if file exists
        if not file_path.exists():
            # Try case-insensitive search for the file
            file_path = self.find_file_case_insensitive(relative_path)
            if not file_path:
                logger.warning(f"[MediaServeMiddleware] File not found: {self.media_root / relative_path}")
                # Return None to let Django's normal 404 handling take over
                return None

        if not file_path.is_file():
            logger.warning(f"[MediaServeMiddleware] Not a file: {file_path}")
            return None

        # Determine content type
        content_type, _ = mimetypes.guess_type(str(file_path))
        if not content_type:
            content_type = 'application/octet-stream'

        # Serve the file
        try:
            response = FileResponse(
                open(file_path, 'rb'),
                content_type=content_type
            )

            # Add cache headers for static assets
            if content_type.startswith('image/') or content_type.startswith('video/'):
                response['Cache-Control'] = 'public, max-age=86400'  # 24 hours

            # Add filename header
            response['Content-Disposition'] = f'inline; filename="{file_path.name}"'

            logger.debug(f"[MediaServeMiddleware] Served: {file_path}")
            return response

        except IOError as e:
            logger.error(f"[MediaServeMiddleware] Error reading file {file_path}: {e}")
            return None

    def find_file_case_insensitive(self, relative_path):
        """
        Try to find a file with case-insensitive matching.
        This helps with files that might have different case extensions (.JPG vs .jpg)
        """
        parts = relative_path.split('/')
        current_path = self.media_root

        for i, part in enumerate(parts):
            if not current_path.exists():
                return None

            # Check if this part exists exactly
            exact_path = current_path / part
            if exact_path.exists():
                current_path = exact_path
                continue

            # Try case-insensitive match
            found = False
            try:
                for item in current_path.iterdir():
                    if item.name.lower() == part.lower():
                        current_path = item
                        found = True
                        break
            except PermissionError:
                return None

            if not found:
                # For the last part (filename), try different extensions
                if i == len(parts) - 1:
                    base_name = Path(part).stem.lower()
                    extensions = ['.jpg', '.jpeg', '.png', '.gif', '.JPG', '.JPEG', '.PNG', '.GIF',
                                  '.mp4', '.webm', '.MP4', '.WEBM']
                    for ext in extensions:
                        test_path = current_path / (base_name + ext)
                        if test_path.exists():
                            return test_path
                        # Also try with original case stem
                        test_path = current_path / (Path(part).stem + ext)
                        if test_path.exists():
                            return test_path
                return None

        return current_path if current_path.is_file() else None


class AnalyticsTrackingMiddleware(MiddlewareMixin):
    """
    Middleware to track page views and visitor sessions.
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
        # Process the request
        response = self.get_response(request)

        # Track the page view after response is generated
        if self.should_track(request, response):
            self.track_page_view(request)
            self.update_visitor_session(request)
            self.update_realtime_visitor(request)

        return response

    def should_track(self, request, response):
        """Determine if this request should be tracked"""
        # Only track successful GET requests
        if request.method != 'GET':
            return False

        if response.status_code != 200:
            return False

        # Exclude certain paths
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

    def track_page_view(self, request):
        """Record a page view"""
        try:
            from .models import PageView
            from .utils import get_client_ip, get_location_from_ip, parse_user_agent_string

            # Ensure session exists
            if not request.session.session_key:
                request.session.create()

            ip_address = get_client_ip(request)
            user_agent = request.META.get('HTTP_USER_AGENT', '')

            # Get location and device info
            location = get_location_from_ip(ip_address)
            ua_info = parse_user_agent_string(user_agent)

            # Skip bots
            if ua_info.get('is_bot'):
                return

            # Determine page name
            page_name = self.PAGE_NAMES.get(request.path, request.path)

            PageView.objects.create(
                page_name=page_name,
                page_url=request.path,
                user=request.user if request.user.is_authenticated else None,
                ip_address=ip_address,
                user_agent=user_agent[:500] if user_agent else '',
                session_key=request.session.session_key,
                referrer=request.META.get('HTTP_REFERER', '')[:500],
                country=location.get('country', ''),
                city=location.get('city', ''),
                device_type=ua_info.get('device_type', ''),
                browser=ua_info.get('browser', ''),
                os=ua_info.get('os', ''),
            )
        except Exception as e:
            logger.error(f"[AnalyticsTracking] Error tracking page view: {e}")

    def update_visitor_session(self, request):
        """Update or create visitor session"""
        try:
            from .models import VisitorSession
            from .utils import get_client_ip, get_location_from_ip, parse_user_agent_string

            if not request.session.session_key:
                request.session.create()

            session_key = request.session.session_key
            ip_address = get_client_ip(request)
            user_agent = request.META.get('HTTP_USER_AGENT', '')

            location = get_location_from_ip(ip_address)
            ua_info = parse_user_agent_string(user_agent)

            # Skip bots
            if ua_info.get('is_bot'):
                return

            # Get or create session
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

    def update_realtime_visitor(self, request):
        """Update real-time visitor tracking"""
        try:
            from .models import RealTimeVisitor
            from .utils import get_client_ip, get_location_from_ip, parse_user_agent_string

            if not request.session.session_key:
                request.session.create()

            session_key = request.session.session_key
            ip_address = get_client_ip(request)
            user_agent = request.META.get('HTTP_USER_AGENT', '')

            location = get_location_from_ip(ip_address)
            ua_info = parse_user_agent_string(user_agent)

            # Skip bots
            if ua_info.get('is_bot'):
                return

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
        except:
            return ''
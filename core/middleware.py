# core/middleware.py - Enhanced tracking middleware

from django.http import FileResponse
from django.conf import settings
from django.utils import timezone
from pathlib import Path
import mimetypes
import os
import logging

logger = logging.getLogger(__name__)


class MediaServeMiddleware:
    """Middleware to serve media files from persistent disk on Render"""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith(settings.MEDIA_URL):
            relative_path = request.path[len(settings.MEDIA_URL):]

            is_render = os.environ.get('RENDER', 'false').lower() == 'true'
            persistent_exists = Path('/var/data').exists()

            if is_render or persistent_exists:
                media_root = Path('/var/data/media')
            else:
                media_root = Path(settings.MEDIA_ROOT)

            file_path = media_root / relative_path

            if file_path.exists() and file_path.is_file():
                content_type, _ = mimetypes.guess_type(str(file_path))
                if content_type is None:
                    content_type = 'application/octet-stream'

                response = FileResponse(
                    open(file_path, 'rb'),
                    content_type=content_type
                )
                response['Cache-Control'] = 'public, max-age=31536000'
                return response

        return self.get_response(request)


class AnalyticsTrackingMiddleware:
    """Enhanced middleware to track page views and visitor sessions"""

    EXCLUDED_PATHS = [
        '/admin/',
        '/api/',
        '/static/',
        '/media/',
        '/favicon.ico',
        '/robots.txt',
        '/sitemap.xml',
        '/__debug__/',
    ]

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Process request
        response = self.get_response(request)

        # Skip tracking for excluded paths
        if any(request.path.startswith(path) for path in self.EXCLUDED_PATHS):
            return response

        # Skip non-HTML responses
        content_type = response.get('Content-Type', '')
        if 'text/html' not in content_type:
            return response

        # Skip if response is not successful
        if response.status_code != 200:
            return response

        # Track the page view asynchronously (or in background)
        try:
            self._track_page_view(request)
            self._update_visitor_session(request)
            self._update_realtime_visitor(request)
        except Exception as e:
            logger.warning(f"Analytics tracking error: {e}")

        return response

    def _get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')

    def _track_page_view(self, request):
        from .models import PageView
        from .utils import get_location_from_ip, parse_user_agent_string

        ip_address = self._get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')

        # Parse user agent
        ua_info = parse_user_agent_string(user_agent)

        # Skip bots
        if ua_info.get('is_bot'):
            return

        # Get location
        location = get_location_from_ip(ip_address)

        # Determine page name from path
        path = request.path
        page_name = path.strip('/').replace('/', '_') or 'home'

        # Get referrer
        referrer = request.META.get('HTTP_REFERER', '')

        # Create page view record
        PageView.objects.create(
            page_name=page_name,
            page_url=request.build_absolute_uri(),
            user=request.user if request.user.is_authenticated else None,
            ip_address=ip_address,
            user_agent=user_agent,
            session_key=request.session.session_key or '',
            referrer=referrer,
            country=location.get('country', ''),
            city=location.get('city', ''),
            device_type=ua_info.get('device_type', ''),
            browser=ua_info.get('browser', ''),
            os=ua_info.get('os', ''),
        )

    def _update_visitor_session(self, request):
        from .models import VisitorSession
        from .utils import get_location_from_ip, parse_user_agent_string
        from urllib.parse import urlparse

        if not request.session.session_key:
            request.session.create()

        session_key = request.session.session_key
        ip_address = self._get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        referrer = request.META.get('HTTP_REFERER', '')

        # Parse user agent
        ua_info = parse_user_agent_string(user_agent)

        # Skip bots
        if ua_info.get('is_bot'):
            return

        # Get location
        location = get_location_from_ip(ip_address)

        # Parse referrer domain
        referrer_domain = ''
        if referrer:
            try:
                parsed = urlparse(referrer)
                referrer_domain = parsed.netloc
            except:
                pass

        # Parse UTM parameters
        utm_source = request.GET.get('utm_source', '')
        utm_medium = request.GET.get('utm_medium', '')
        utm_campaign = request.GET.get('utm_campaign', '')

        # Update or create session
        session, created = VisitorSession.objects.update_or_create(
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
                'referrer': referrer,
                'referrer_domain': referrer_domain,
                'is_bot': ua_info.get('is_bot', False),
            }
        )

        # Update page views count
        if not created:
            session.page_views += 1
            session.save(update_fields=['page_views', 'last_activity'])
        else:
            session.landing_page = request.path
            session.utm_source = utm_source
            session.utm_medium = utm_medium
            session.utm_campaign = utm_campaign
            session.save()

    def _update_realtime_visitor(self, request):
        from .models import RealTimeVisitor
        from .utils import get_location_from_ip, parse_user_agent_string

        if not request.session.session_key:
            return

        session_key = request.session.session_key
        ip_address = self._get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')

        ua_info = parse_user_agent_string(user_agent)
        location = get_location_from_ip(ip_address)

        # Skip bots
        if ua_info.get('is_bot'):
            return

        # Determine page title from path
        path = request.path
        page_title = path.strip('/').replace('/', ' > ').title() or 'Accueil'

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
            }
        )
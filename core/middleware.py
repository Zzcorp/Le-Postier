# core/middleware.py
from django.conf import settings
from django.http import FileResponse
from pathlib import Path
import mimetypes
from .utils import track_visitor_session, cleanup_old_realtime_visitors
from django.utils import timezone
import random


class MediaServeMiddleware:
    """
    Middleware to serve media files from MEDIA_ROOT.
    This handles media files when they're stored on a persistent disk.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Check if this is a media file request
        if request.path.startswith(settings.MEDIA_URL):
            # Get the file path relative to MEDIA_URL
            relative_path = request.path[len(settings.MEDIA_URL):]
            file_path = Path(settings.MEDIA_ROOT) / relative_path

            if file_path.exists() and file_path.is_file():
                # Determine content type
                content_type, _ = mimetypes.guess_type(str(file_path))
                if content_type is None:
                    content_type = 'application/octet-stream'

                # Serve the file
                response = FileResponse(
                    open(file_path, 'rb'),
                    content_type=content_type
                )

                # Set cache headers for better performance
                response['Cache-Control'] = 'public, max-age=86400'  # 24 hours

                return response

        return self.get_response(request)


class AnalyticsTrackingMiddleware:
    """
    Middleware to track visitor sessions and page views.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.excluded_paths = [
            '/static/',
            '/media/',
            '/admin/jsi18n/',
            '/favicon.ico',
            '/robots.txt',
            '/api/',  # Don't track API calls for page views
        ]
        self.excluded_extensions = ['.css', '.js', '.png', '.jpg', '.jpeg', '.gif', '.ico', '.svg', '.woff', '.woff2',
                                    '.ttf']

    def __call__(self, request):
        # Check if we should track this request
        should_track = True
        path = request.path.lower()

        for excluded in self.excluded_paths:
            if path.startswith(excluded.lower()):
                should_track = False
                break

        for ext in self.excluded_extensions:
            if path.endswith(ext):
                should_track = False
                break

        if should_track and request.method == 'GET':
            try:
                # Track visitor session
                track_visitor_session(request)

                # Occasionally cleanup old real-time visitors (1% of requests)
                if random.random() < 0.01:
                    cleanup_old_realtime_visitors()
            except Exception as e:
                # Don't let tracking errors break the site
                import logging
                logging.error(f"Analytics tracking error: {e}")

        response = self.get_response(request)
        return response
# core/middleware.py
"""
Middleware to serve media files from persistent disk in production.
"""

from django.http import FileResponse, Http404
from django.conf import settings
from pathlib import Path
import mimetypes
import logging

logger = logging.getLogger(__name__)


class MediaServeMiddleware:
    """
    Middleware to serve media files from the persistent disk.
    This is needed because WhiteNoise only serves static files, not media.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.media_url = settings.MEDIA_URL.rstrip('/')
        self.media_root = Path(settings.MEDIA_ROOT)

    def __call__(self, request):
        # Check if this is a media file request
        if request.path.startswith(self.media_url + '/'):
            return self.serve_media(request)

        return self.get_response(request)

    def serve_media(self, request):
        # Get the relative path from the URL
        relative_path = request.path[len(self.media_url) + 1:]

        # Security: prevent directory traversal
        if '..' in relative_path or relative_path.startswith('/'):
            raise Http404("Invalid path")

        # Build the full file path
        file_path = self.media_root / relative_path

        # Check if file exists
        if not file_path.exists() or not file_path.is_file():
            logger.debug(f"Media file not found: {file_path}")
            raise Http404(f"Media file not found: {relative_path}")

        # Security: ensure the file is within MEDIA_ROOT
        try:
            file_path.resolve().relative_to(self.media_root.resolve())
        except ValueError:
            raise Http404("Invalid path")

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

            # Set cache headers for better performance
            response['Cache-Control'] = 'public, max-age=86400'  # 1 day

            # For videos, support range requests
            if content_type.startswith('video/'):
                response['Accept-Ranges'] = 'bytes'

            return response

        except IOError as e:
            logger.error(f"Error serving media file {file_path}: {e}")
            raise Http404("Error serving file")
# core/middleware.py
"""
Middleware to serve media files in production.
WhiteNoise only handles static files, this handles media.
"""

import os
import mimetypes
from django.conf import settings
from django.http import FileResponse, Http404
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class MediaServeMiddleware:
    """
    Middleware to serve media files from MEDIA_ROOT.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.media_url = settings.MEDIA_URL
        self.media_root = Path(settings.MEDIA_ROOT)

        # Initialize mimetypes
        mimetypes.init()
        # Add video types if not present
        mimetypes.add_type('video/mp4', '.mp4')
        mimetypes.add_type('video/webm', '.webm')

    def __call__(self, request):
        # Check if this is a media file request
        if request.path.startswith(self.media_url):
            return self.serve_media(request)
        return self.get_response(request)

    def serve_media(self, request):
        """Serve a media file."""
        # Get the relative path after /media/
        relative_path = request.path[len(self.media_url):]

        # Security: prevent directory traversal
        if '..' in relative_path or relative_path.startswith('/'):
            logger.warning(f"Blocked suspicious media path: {relative_path}")
            raise Http404("Invalid path")

        # Build full path
        file_path = self.media_root / relative_path

        # Normalize the path to prevent traversal
        try:
            file_path = file_path.resolve()
            # Ensure the resolved path is still under MEDIA_ROOT
            if not str(file_path).startswith(str(self.media_root.resolve())):
                raise Http404("Invalid path")
        except (ValueError, RuntimeError):
            raise Http404("Invalid path")

        # Check if file exists
        if not file_path.exists():
            logger.debug(f"Media file not found: {file_path}")
            raise Http404(f"Media file not found: {relative_path}")

        if not file_path.is_file():
            raise Http404("Not a file")

        # Get content type
        content_type, _ = mimetypes.guess_type(str(file_path))
        if content_type is None:
            content_type = 'application/octet-stream'

        # Serve the file
        try:
            response = FileResponse(
                open(file_path, 'rb'),
                content_type=content_type
            )
        except IOError as e:
            logger.error(f"Error opening file {file_path}: {e}")
            raise Http404("Error reading file")

        # Set cache headers based on content type
        if content_type.startswith('image/'):
            response['Cache-Control'] = 'public, max-age=86400'  # 1 day
        elif content_type.startswith('video/'):
            response['Cache-Control'] = 'public, max-age=604800'  # 1 week
            # Support range requests for video streaming
            response['Accept-Ranges'] = 'bytes'
        else:
            response['Cache-Control'] = 'public, max-age=3600'  # 1 hour

        # Add content length
        response['Content-Length'] = file_path.stat().st_size

        return response
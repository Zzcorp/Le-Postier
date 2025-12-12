# core/middleware.py
"""
Middleware to serve media files in production.
WhiteNoise only handles static files, this handles media.
"""

import os
import mimetypes
from django.conf import settings
from django.http import FileResponse, Http404, HttpResponseNotModified
from pathlib import Path
import logging
import hashlib

logger = logging.getLogger(__name__)


class MediaServeMiddleware:
    """
    Middleware to serve media files from MEDIA_ROOT.
    Handles images, videos with proper caching and range requests for video streaming.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.media_url = getattr(settings, 'MEDIA_URL', '/media/')
        self.media_root = Path(getattr(settings, 'MEDIA_ROOT', 'media'))

        # Initialize mimetypes
        mimetypes.init()
        # Add video types if not present
        mimetypes.add_type('video/mp4', '.mp4')
        mimetypes.add_type('video/webm', '.webm')
        mimetypes.add_type('image/jpeg', '.jpg')
        mimetypes.add_type('image/jpeg', '.jpeg')
        mimetypes.add_type('image/png', '.png')
        mimetypes.add_type('image/gif', '.gif')

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
            media_root_resolved = self.media_root.resolve()
            # Ensure the resolved path is still under MEDIA_ROOT
            if not str(file_path).startswith(str(media_root_resolved)):
                raise Http404("Invalid path")
        except (ValueError, RuntimeError, OSError):
            raise Http404("Invalid path")

        # Check if file exists
        if not file_path.exists():
            # Try case-insensitive match
            file_path = self.find_case_insensitive(file_path)
            if not file_path:
                logger.debug(f"Media file not found: {relative_path}")
                raise Http404(f"Media file not found")

        if not file_path.is_file():
            raise Http404("Not a file")

        # Get file stats
        stat = file_path.stat()

        # Generate ETag
        etag = self.generate_etag(file_path, stat)

        # Check If-None-Match header for caching
        if_none_match = request.META.get('HTTP_IF_NONE_MATCH')
        if if_none_match and if_none_match == etag:
            return HttpResponseNotModified()

        # Get content type
        content_type, _ = mimetypes.guess_type(str(file_path))
        if content_type is None:
            content_type = 'application/octet-stream'

        # Handle range requests for video streaming
        range_header = request.META.get('HTTP_RANGE')
        if range_header and content_type.startswith('video/'):
            return self.serve_range_request(file_path, stat, content_type, range_header, etag)

        # Serve the file
        try:
            response = FileResponse(
                open(file_path, 'rb'),
                content_type=content_type
            )
        except IOError as e:
            logger.error(f"Error opening file {file_path}: {e}")
            raise Http404("Error reading file")

        # Set headers
        response['Content-Length'] = stat.st_size
        response['ETag'] = etag
        response['Accept-Ranges'] = 'bytes'

        # Set cache headers based on content type
        if content_type.startswith('image/'):
            response['Cache-Control'] = 'public, max-age=604800'  # 1 week
        elif content_type.startswith('video/'):
            response['Cache-Control'] = 'public, max-age=2592000'  # 30 days
        else:
            response['Cache-Control'] = 'public, max-age=86400'  # 1 day

        return response

    def find_case_insensitive(self, file_path):
        """Try to find file with case-insensitive matching."""
        parent = file_path.parent
        if not parent.exists():
            return None

        target_name = file_path.name.lower()
        for f in parent.iterdir():
            if f.name.lower() == target_name:
                return f
        return None

    def generate_etag(self, file_path, stat):
        """Generate ETag based on file path and modification time."""
        data = f"{file_path}-{stat.st_mtime}-{stat.st_size}"
        return f'"{hashlib.md5(data.encode()).hexdigest()}"'

    def serve_range_request(self, file_path, stat, content_type, range_header, etag):
        """Handle HTTP range requests for video streaming."""
        file_size = stat.st_size

        # Parse range header
        # Format: bytes=start-end or bytes=start-
        try:
            range_match = range_header.replace('bytes=', '')
            if '-' in range_match:
                parts = range_match.split('-')
                start = int(parts[0]) if parts[0] else 0
                end = int(parts[1]) if parts[1] else file_size - 1
            else:
                start = int(range_match)
                end = file_size - 1
        except (ValueError, IndexError):
            start = 0
            end = file_size - 1

        # Ensure valid range
        start = max(0, min(start, file_size - 1))
        end = max(start, min(end, file_size - 1))
        length = end - start + 1

        # Open file and seek to start position
        try:
            f = open(file_path, 'rb')
            f.seek(start)
        except IOError as e:
            logger.error(f"Error opening file for range request: {e}")
            raise Http404("Error reading file")

        # Create response with partial content
        from django.http import StreamingHttpResponse

        def file_iterator(file_obj, chunk_size=8192, length=length):
            bytes_read = 0
            while bytes_read < length:
                chunk = file_obj.read(min(chunk_size, length - bytes_read))
                if not chunk:
                    break
                bytes_read += len(chunk)
                yield chunk
            file_obj.close()

        response = StreamingHttpResponse(
            file_iterator(f),
            status=206,
            content_type=content_type
        )

        response['Content-Length'] = length
        response['Content-Range'] = f'bytes {start}-{end}/{file_size}'
        response['Accept-Ranges'] = 'bytes'
        response['ETag'] = etag
        response['Cache-Control'] = 'public, max-age=2592000'

        return response
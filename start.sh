#!/usr/bin/env bash
# start.sh - Startup script for Render

echo "=========================================="
echo "Le Postier - Starting Web Service"
echo "=========================================="

# Show environment
echo "RENDER: $RENDER"
echo "MEDIA_ROOT: ${MEDIA_ROOT:-/var/data/media}"

# Create media directories on persistent disk
echo ""
echo "Setting up media directories..."
python -c "
import os
from pathlib import Path

# Always use persistent disk on Render
if os.environ.get('RENDER'):
    media_root = Path('/var/data/media')
else:
    media_root = Path(os.environ.get('MEDIA_ROOT', 'media'))

print(f'Media root: {media_root}')

directories = [
    media_root / 'postcards' / 'Vignette',
    media_root / 'postcards' / 'Grande',
    media_root / 'postcards' / 'Dos',
    media_root / 'postcards' / 'Zoom',
    media_root / 'animated_cp',
    media_root / 'signatures',
]

for directory in directories:
    try:
        directory.mkdir(parents=True, exist_ok=True)
        print(f'  ✓ {directory}')
    except Exception as e:
        print(f'  ✗ {directory}: {e}')

# Check disk space
try:
    import shutil
    total, used, free = shutil.disk_usage(media_root)
    print(f'')
    print(f'Disk space: {free / (1024**3):.2f} GB free of {total / (1024**3):.2f} GB')
except:
    pass
"

echo ""
echo "Starting Gunicorn..."
exec gunicorn le_postier.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --timeout 120
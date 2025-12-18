#!/usr/bin/env bash
# start.sh - Startup script for Render

echo "=========================================="
echo "Le Postier - Starting Web Service"
echo "=========================================="

# Show environment
echo "RENDER: $RENDER"
echo "Checking /var/data..."

# Check if persistent disk is mounted
if [ -d "/var/data" ]; then
    echo "✓ Persistent disk mounted at /var/data"
    MEDIA_ROOT="/var/data/media"
else
    echo "✗ WARNING: /var/data not found - using fallback"
    MEDIA_ROOT="./media"
fi

echo "MEDIA_ROOT will be: $MEDIA_ROOT"

# Create media directories on persistent disk
echo ""
echo "Setting up media directories..."
python -c "
import os
from pathlib import Path

# Always use persistent disk if it exists
if Path('/var/data').exists():
    media_root = Path('/var/data/media')
    print(f'Using persistent disk: {media_root}')
else:
    media_root = Path('media')
    print(f'Using local folder: {media_root}')

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
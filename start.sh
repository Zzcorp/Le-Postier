#!/usr/bin/env bash
# Startup script for Render - runs when the service starts

echo "Setting up media directories on persistent disk..."

# Create media directories (persistent disk is now mounted)
python -c "
import os
from pathlib import Path

media_root = Path(os.environ.get('MEDIA_ROOT', '/var/data/media'))

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
        print(f'  ✓ Created: {directory}')
    except Exception as e:
        print(f'  ✗ Error creating {directory}: {e}')

print(f'Media root: {media_root}')
print(f'Media root exists: {media_root.exists()}')
"

echo "Starting Gunicorn..."
exec gunicorn le_postier.wsgi:application --bind 0.0.0.0:$PORT
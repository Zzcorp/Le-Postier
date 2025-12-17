#!/usr/bin/env bash
# Build script for Render

set -o errexit

echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo "Collecting static files..."
python manage.py collectstatic --no-input

echo "Running migrations..."
python manage.py migrate

echo "Setting up media directories..."
python -c "
from django.conf import settings
from pathlib import Path
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'le_postier.settings')
import django
django.setup()

media_root = Path(settings.MEDIA_ROOT)
for folder in ['Vignette', 'Grande', 'Dos', 'Zoom']:
    (media_root / 'postcards' / folder).mkdir(parents=True, exist_ok=True)
(media_root / 'animated_cp').mkdir(parents=True, exist_ok=True)
(media_root / 'signatures').mkdir(parents=True, exist_ok=True)
print(f'Media directories created at {media_root}')
"

echo "Creating admin user if needed..."
python manage.py create_admin || true

echo "Build complete!"
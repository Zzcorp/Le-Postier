#!/usr/bin/env bash
# build.sh - Build script for Render deployment

set -o errexit

echo "=== Starting build process ==="

# Install Python dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --no-input

# Run database migrations
echo "Running migrations..."
python manage.py migrate

# Create admin user
echo "Creating admin user..."
python manage.py create_admin || true

# Scan media folder and show stats
echo "Scanning media folder..."
python manage.py scan_media || true

# Create postcard entries from images if database is empty
POSTCARD_COUNT=$(python -c "
import django
django.setup()
from core.models import Postcard
print(Postcard.objects.count())
" 2>/dev/null || echo "0")

if [ "$POSTCARD_COUNT" = "0" ]; then
    echo "Database is empty, creating postcards from images..."
    python manage.py import_postcards_from_csv --create-from-images || true
fi

echo "=== Build completed successfully! ==="
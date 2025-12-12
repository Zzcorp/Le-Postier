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

# Update postcard image flags
echo "Updating postcard image flags..."
python manage.py import_postcards_csv --update-flags || true

echo "=== Build completed successfully! ==="
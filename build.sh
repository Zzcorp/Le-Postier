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

echo "Creating admin user if needed..."
python manage.py create_admin || true

echo "Build complete!"
echo "Note: Media directories will be created at runtime when the persistent disk is mounted."
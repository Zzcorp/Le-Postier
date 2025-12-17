#!/usr/bin/env bash
# build.sh - Build script for Render

set -o errexit

echo "=========================================="
echo "Installing dependencies..."
echo "=========================================="
pip install --upgrade pip
pip install -r requirements.txt

echo "=========================================="
echo "Collecting static files..."
echo "=========================================="
python manage.py collectstatic --no-input

echo "=========================================="
echo "Running migrations..."
echo "=========================================="
python manage.py migrate

echo "=========================================="
echo "Creating admin user..."
echo "=========================================="
python manage.py create_admin || true

echo "=========================================="
echo "Build complete!"
echo "=========================================="
echo "Media directories will be created at runtime."
echo "Run 'python manage.py full_setup' after deployment."
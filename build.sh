#!/usr/bin/env bash
# build.sh - Build script for Render

set -o errexit

echo "=========================================="
echo "Le Postier - Build Script"
echo "=========================================="

echo ""
echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo ""
echo "Collecting static files..."
python manage.py collectstatic --no-input

echo ""
echo "Running migrations..."
python manage.py migrate

echo ""
echo "Creating admin user..."
python manage.py create_admin || true

echo ""
echo "=========================================="
echo "Build complete!"
echo "=========================================="
echo ""
echo "IMPORTANT: After deployment, run these commands in Render Shell:"
echo ""
echo "1. Sync images from OVH (set env vars first):"
echo "   python manage.py sync_from_ovh"
echo ""
echo "2. Import CSV data:"
echo "   python manage.py import_csv /path/to/your/data.csv --update"
echo ""
echo "3. Update image flags:"
echo "   python manage.py update_flags"
echo ""
echo "Or run all at once:"
echo "   python manage.py full_setup --csv /path/to/data.csv"
echo ""
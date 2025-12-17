#!/usr/bin/env bash
# build.sh

set -o errexit

echo "=== Starting build process ==="

pip install -r requirements.txt

echo "Collecting static files..."
python manage.py collectstatic --no-input

echo "Running migrations..."
python manage.py migrate

echo "Creating admin user..."
python manage.py create_admin || true

# Sync images from OVH if credentials are provided
if [ -n "$OVH_FTP_HOST" ] && [ -n "$OVH_FTP_USER" ] && [ -n "$OVH_FTP_PASS" ]; then
    echo "Syncing images from OVH FTP..."
    python manage.py sync_from_ovh \
        --ftp-host="$OVH_FTP_HOST" \
        --ftp-user="$OVH_FTP_USER" \
        --ftp-pass="$OVH_FTP_PASS" \
        --ftp-path="/collection_cp/cartes" \
        --animated-path="/collection_cp/animated_cp" \
        --folders="Vignette,Grande,Dos,Zoom" \
        --include-animated \
        --skip-existing
    echo "Image sync completed!"
else
    echo "OVH FTP credentials not set, skipping image sync"
fi

echo "=== Build completed ==="
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

# Check if migration should run
if [ "$RUN_OVH_MIGRATION" = "false" ]; then
    echo "Running OVH migration..."
    python manage.py migrate_from_ovh \
      --ftp-host=${OVH_FTP_HOST} \
      --ftp-user=${OVH_FTP_USER} \
      --ftp-pass=${OVH_FTP_PASS} \
      --generate-csv
    
    echo "Migration completed!"
fi

echo "=== Build completed ==="
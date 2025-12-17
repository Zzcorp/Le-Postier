#!/bin/bash
# sync_images.sh - Run this on Render to sync images from OVH

echo "Starting image sync from OVH FTP..."

# Set these environment variables in Render dashboard or here
# OVH_FTP_HOST=ftp.cluster0XX.hosting.ovh.net
# OVH_FTP_USER=your_username
# OVH_FTP_PASS=your_password

python manage.py sync_from_ovh \
    --ftp-host="${OVH_FTP_HOST}" \
    --ftp-user="${OVH_FTP_USER}" \
    --ftp-pass="${OVH_FTP_PASS}" \
    --ftp-path="/collection_cp/cartes" \
    --animated-path="/collection_cp/animated_cp" \
    --folders="Vignette,Grande,Dos,Zoom" \
    --include-animated \
    --skip-existing

echo "Sync complete!"
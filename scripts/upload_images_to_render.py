#!/usr/bin/env python
"""
Script to upload postcard images to Render.
Run this locally to batch upload images.

Usage:
    python upload_images_to_render.py --source /path/to/images --url https://your-app.onrender.com
"""

import os
import sys
import argparse
import requests
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed


def upload_file(file_path, upload_url, folder_type):
    """Upload a single file to the server."""
    try:
        with open(file_path, 'rb') as f:
            files = {'file': (file_path.name, f)}
            data = {'folder': folder_type}
            response = requests.post(upload_url, files=files, data=data, timeout=60)

            if response.status_code == 200:
                return True, file_path.name
            else:
                return False, f"{file_path.name}: {response.status_code}"
    except Exception as e:
        return False, f"{file_path.name}: {str(e)}"


def main():
    parser = argparse.ArgumentParser(description='Upload images to Render')
    parser.add_argument('--source', required=True, help='Source directory containing images')
    parser.add_argument('--url', required=True, help='Base URL of your Render app')
    parser.add_argument('--folder', choices=['Vignette', 'Grande', 'Dos', 'Zoom', 'animated_cp', 'all'],
                        default='all', help='Folder to upload')
    parser.add_argument('--workers', type=int, default=4, help='Number of parallel uploads')

    args = parser.parse_args()

    source_path = Path(args.source)
    upload_url = f"{args.url.rstrip('/')}/api/admin/upload-media/"

    if not source_path.exists():
        print(f"Error: Source directory not found: {source_path}")
        sys.exit(1)

    # Determine folders to upload
    if args.folder == 'all':
        folders = ['Vignette', 'Grande', 'Dos', 'Zoom', 'animated_cp']
    else:
        folders = [args.folder]

    total_uploaded = 0
    total_failed = 0

    for folder in folders:
        if folder == 'animated_cp':
            folder_path = source_path / 'animated_cp'
            extensions = {'.mp4', '.webm'}
        else:
            folder_path = source_path / folder
            extensions = {'.jpg', '.jpeg', '.png', '.gif'}

        if not folder_path.exists():
            print(f"Skipping {folder} - directory not found")
            continue

        # Get all files
        files = [f for f in folder_path.iterdir()
                 if f.is_file() and f.suffix.lower() in extensions]

        print(f"\nUploading {len(files)} files from {folder}...")

        # Upload with thread pool
        with ThreadPoolExecutor(max_workers=args.workers) as executor:
            futures = {
                executor.submit(upload_file, f, upload_url, folder): f
                for f in files
            }

            for i, future in enumerate(as_completed(futures)):
                success, message = future.result()
                if success:
                    total_uploaded += 1
                else:
                    total_failed += 1
                    print(f"  Failed: {message}")

                # Progress indicator
                if (i + 1) % 50 == 0:
                    print(f"  Progress: {i + 1}/{len(files)}")

    print(f"\n{'=' * 50}")
    print(f"Upload complete!")
    print(f"  Uploaded: {total_uploaded}")
    print(f"  Failed: {total_failed}")


if __name__ == '__main__':
    main()
#!/usr/bin/env bash
# exit on error
set -o errexit

echo "Starting build process..."
echo "Python version: $(python --version)"

# Install system dependencies for Pillow
apt-get update -y
apt-get install -y \
    libjpeg-dev \
    zlib1g-dev \
    libpng-dev \
    libfreetype6-dev \
    liblcms2-dev \
    libtiff5-dev \
    libwebp-dev \
    libharfbuzz-dev \
    libfribidi-dev \
    libxcb1-dev \
    build-essential

# Upgrade pip and install wheel
python -m pip install --upgrade pip wheel setuptools

# Install Pillow with no binary to compile from source if needed
python -m pip install --no-cache-dir Pillow==10.4.0

# Install other dependencies
python -m pip install -r requirements.txt

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --no-input

# Run migrations
echo "Running migrations..."
python manage.py migrate

# Create superuser if it doesn't exist
echo "Checking for superuser..."
python manage.py shell << END
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='samathey').exists():
    try:
        User.objects.create_superuser(
            username='samathey',
            email='sam@samathey.com',
            password='Elpatron78!'
        )
        print('Superuser created successfully.')
    except Exception as e:
        print(f'Error creating superuser: {e}')
else:
    print('Superuser already exists.')
END

echo "Build completed successfully!"
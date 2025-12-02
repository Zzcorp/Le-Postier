#!/usr/bin/env bash
set -o errexit

echo "Starting build process..."
echo "Python version: $(python --version)"

# Upgrade pip
python -m pip install --upgrade pip wheel setuptools

# Install dependencies
echo "Installing Python dependencies..."
python -m pip install -r requirements.txt

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --no-input

# Run migrations
echo "Running migrations..."
python manage.py migrate

# Create superuser
echo "Checking for superuser..."
python manage.py shell << END
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='samathey').exists():
    try:
        User.objects.create_superuser(
            username='samathey',
            email='sam@samathey.com',
            password='Elpatron78!',
            category='viewer',
            email_verified=True
        )
        print('Superuser created successfully.')
    except Exception as e:
        print(f'Error creating superuser: {e}')
else:
    print('Superuser already exists.')
END

echo "Build completed successfully!"
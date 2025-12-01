#!/usr/bin/env bash
# exit on error
set -o errexit

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Collect static files
python manage.py collectstatic --no-input

# Run migrations
python manage.py migrate

# Create superuser if it doesn't exist
python manage.py shell << END
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='samathey').exists():
    User.objects.create_superuser(
        username='samathey',
        email='sam@samathey.com',
        password='Elpatron78!',
        category='viewer',
        email_verified=True
    )
    print('Superuser created.')
else:
    print('Superuser already exists.')
END

echo "Build completed successfully!"
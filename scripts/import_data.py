import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'le_postier.settings_production')
django.setup()

from core.models import Postcard, Theme

# Your import logic here
print("Importing postcards...")
# Add your postcard import code
print("Import completed!")
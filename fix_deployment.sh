#!/bin/bash

# Remove corsheaders from settings
echo "Fixing settings..."
sed -i "/corsheaders/d" le_postier/settings.py
sed -i "/corsheaders/d" le_postier/settings_production.py 2>/dev/null || true

# Update requirements.txt
echo "Updating requirements.txt..."
cat > requirements.txt << 'EOF'
Django==4.2.7
Pillow==10.2.0
gunicorn==21.2.0
whitenoise==6.6.0
dj-database-url==2.1.0
psycopg2-binary==2.9.9
python-decouple==3.8
django-crispy-forms==2.1
crispy-bootstrap5==2024.2
EOF

# Fix wsgi.py
echo "Fixing wsgi.py..."
cat > le_postier/wsgi.py << 'EOF'
import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'le_postier.settings')
application = get_wsgi_application()
EOF

echo "Done! Now commit and push:"
echo "git add ."
echo "git commit -m 'Fix deployment - remove corsheaders'"
echo "git push origin main"
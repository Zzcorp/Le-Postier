#!/usr/bin/env python
import os
import sys
from django.conf import settings
from django.urls import path
from django.http import HttpResponse
from django.core.wsgi import get_wsgi_application

# Configure Django
settings.configure(
    DEBUG=True,
    SECRET_KEY='django-insecure-8d0)r5bhf(r85cg*u_vbk-@k&i1bv%lvjah^34!siis!o1dekn',
    ALLOWED_HOSTS=['*'],
    ROOT_URLCONF=__name__,
    MIDDLEWARE=[],  # NO MIDDLEWARE AT ALL
    INSTALLED_APPS=['django.contrib.contenttypes'],
)

# Single view
def home(request):
    return HttpResponse('Le Postier - No Redirect Test')

# URL patterns
urlpatterns = [
    path('', home),
]

# WSGI application
application = get_wsgi_application()

if __name__ == '__main__':
    from django.core.management import execute_from_command_line
    execute_from_command_line(sys.argv)
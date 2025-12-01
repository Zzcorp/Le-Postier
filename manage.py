#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys


def main():
    """Run administrative tasks."""
    # Use production settings by default on Render
    settings_module = 'le_postier.settings'
    if os.environ.get('RENDER'):
        settings_module = 'le_postier.settings_production'

    os.environ.setdefault('DJANGO_SETTINGS_MODULE', settings_module)

    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
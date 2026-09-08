"""
ASGI config for jdih_sidoarjo project.
"""

import os
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'jdih_sidoarjo.settings')

application = get_asgi_application()

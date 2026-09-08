"""
WSGI config for jdih_sidoarjo project.

It exposes the WSGI callable as a module-level variable named ``application``.
Also defines ``app`` for Vercel Serverless Functions.
"""

import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'jdih_sidoarjo.settings')

application = get_wsgi_application()
app = application

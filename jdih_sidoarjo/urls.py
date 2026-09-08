"""
URL configuration for jdih_sidoarjo project.
"""

from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # Public documents portal
    path('', include('documents.urls')),

    # Custom Admin panel (Firebase Auth backed)
    path('admin-panel/', include('admin_panel.urls')),
]

# In development, serve static files directly if needed
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])

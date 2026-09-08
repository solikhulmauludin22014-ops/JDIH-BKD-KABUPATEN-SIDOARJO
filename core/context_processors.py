import os
from django.conf import settings

def institution_context(request):
    """
    Context processor to provide institutional branding and Firebase client info.
    """
    admin_user = request.session.get('admin_user', None)
    
    return {
        'INSTITUTION_NAME': 'Badan Kepegawaian Daerah Kabupaten Sidoarjo',
        'INSTITUTION_SHORT': 'BKD Kab. Sidoarjo',
        'APP_TITLE': 'JDIH BKD Sidoarjo',
        'APP_SUBTITLE': 'Jaringan Dokumentasi dan Informasi Hukum Kepegawaian',
        'GOVERNMENT_NAME': 'Pemerintah Kabupaten Sidoarjo',
        'CURRENT_YEAR': 2026,
        'ADMIN_USER': admin_user,
        'IS_AUTHENTICATED_ADMIN': bool(admin_user),
        'FIREBASE_WEB_CONFIG': {
            'apiKey': getattr(settings, 'FIREBASE_WEB_API_KEY', ''),
            'authDomain': getattr(settings, 'FIREBASE_AUTH_DOMAIN', ''),
            'projectId': getattr(settings, 'FIREBASE_PROJECT_ID', ''),
            'storageBucket': getattr(settings, 'FIREBASE_STORAGE_BUCKET', ''),
            'messagingSenderId': getattr(settings, 'FIREBASE_MESSAGING_SENDER_ID', '319941227618'),
            'appId': getattr(settings, 'FIREBASE_APP_ID', ''),
        }
    }

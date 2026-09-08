"""
Firebase Admin SDK Configuration & Initialization.
Supports:
1. Environment Variable JSON string (Vercel deployment: FIREBASE_SERVICE_ACCOUNT_JSON)
2. Local service account JSON file (Local dev: FIREBASE_CREDENTIALS_PATH)
3. Safe Mock Provider fallback if credentials are not yet configured.
"""

import os
import json
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

_firebase_app = None
_firestore_db = None
_storage_bucket = None
_is_mock = False


def initialize_firebase():
    """
    Initialize Firebase Admin SDK or enable mock provider fallback.
    """
    global _firebase_app, _firestore_db, _storage_bucket, _is_mock
    
    if _firebase_app is not None or _is_mock:
        return _firestore_db, _storage_bucket, _is_mock

    try:
        import firebase_admin
        from firebase_admin import credentials, firestore, storage

        # Check if already initialized
        if firebase_admin._apps:
            _firebase_app = firebase_admin.get_app()
            _firestore_db = firestore.client()
            bucket_name = getattr(settings, 'FIREBASE_STORAGE_BUCKET', None)
            _storage_bucket = storage.bucket(bucket_name) if bucket_name else None
            _is_mock = False
            return _firestore_db, _storage_bucket, _is_mock

        cred = None

        # 1. Try JSON string from environment variable (Best for Vercel)
        service_account_json = getattr(settings, 'FIREBASE_SERVICE_ACCOUNT_JSON', None)
        if service_account_json:
            try:
                cert_dict = json.loads(service_account_json)
                cred = credentials.Certificate(cert_dict)
                logger.info("Loaded Firebase credentials from FIREBASE_SERVICE_ACCOUNT_JSON.")
            except Exception as e:
                logger.warning(f"Error parsing FIREBASE_SERVICE_ACCOUNT_JSON: {e}")

        # 2. Try file path from environment variable or default path
        if not cred:
            cred_path = getattr(settings, 'FIREBASE_CREDENTIALS_PATH', None)
            candidate_paths = [
                cred_path,
                f"{cred_path}.json" if cred_path else None,
                str(settings.BASE_DIR / 'serviceAccountKey.json'),
                str(settings.BASE_DIR / 'serviceAccountKey.json.json'),
            ]
            valid_path = next((p for p in candidate_paths if p and os.path.exists(p)), None)

            if valid_path:
                try:
                    cred = credentials.Certificate(valid_path)
                    logger.info(f"Loaded Firebase credentials from file: {valid_path}")
                except Exception as e:
                    logger.warning(f"Error loading credentials from {valid_path}: {e}")

        # Initialize if credentials found
        if cred:
            options = {}
            bucket_name = getattr(settings, 'FIREBASE_STORAGE_BUCKET', None)
            if bucket_name:
                options['storageBucket'] = bucket_name

            _firebase_app = firebase_admin.initialize_app(cred, options)
            try:
                _firestore_db = firestore.client()
                # Test connectivity to Firestore
                _ = list(_firestore_db.collection('documents').limit(1).stream())
            except Exception as fe:
                msg_str = str(fe)
                if "SERVICE_DISABLED" in msg_str or "403" in msg_str:
                    logger.info("Info Firebase: Cloud Firestore belum diaktifkan di Firebase Console. Mengaktifkan mode data lokal siap-pakai.")
                else:
                    logger.info(f"Info Firebase: {msg_str[:120]}. Mengaktifkan mode data lokal siap-pakai.")
                _firestore_db = None

            if bucket_name:
                try:
                    _storage_bucket = storage.bucket(bucket_name)
                except Exception as se:
                    logger.warning(f"Storage bucket note: {se}")

            if _firestore_db is not None:
                _is_mock = False
                logger.info("Firebase Admin SDK & Firestore successfully initialized.")
                return _firestore_db, _storage_bucket, _is_mock
            else:
                _is_mock = True
                return None, _storage_bucket, _is_mock

    except Exception as e:
        logger.error(f"Failed to initialize Firebase Admin SDK: {e}")

    # Fallback to Mock mode for preview and development
    logger.warning("Firebase credentials not active. Running in Mock/Preview mode with sample BKD data.")
    _is_mock = True
    return None, None, _is_mock


def get_firestore_db():
    """Get Firestore client or None if mock mode."""
    db, _, is_mock = initialize_firebase()
    return db if not is_mock else None


def get_storage_bucket():
    """Get Storage bucket or None if mock mode."""
    _, bucket, is_mock = initialize_firebase()
    return bucket if not is_mock else None


def is_mock_mode():
    """Return True if running in fallback mock mode."""
    initialize_firebase()
    return _is_mock


def verify_firebase_id_token(id_token):
    """
    Verify Firebase ID token using firebase_admin.auth.
    Returns decoded token dict with 'uid', 'email', etc. or None on failure.
    """
    if is_mock_mode():
        # In mock mode, allow test token verification
        if id_token and id_token.startswith("mock-token-"):
            email = id_token.replace("mock-token-", "")
            return {
                "uid": f"mock_uid_{email}",
                "email": email,
                "name": "Admin BKD Sidoarjo",
            }
        return None

    try:
        from firebase_admin import auth
        decoded_token = auth.verify_id_token(id_token)
        return decoded_token
    except Exception as e:
        logger.error(f"Error verifying Firebase ID token: {e}")
        return None

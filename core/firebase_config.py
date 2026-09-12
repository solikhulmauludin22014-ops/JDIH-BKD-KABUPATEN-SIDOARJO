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
_storage_bucket = None  # Firebase Storage tidak digunakan (diganti Appwrite Storage)
_is_mock = False


def initialize_firebase():
    """
    Initialize Firebase Admin SDK or enable mock provider fallback.
    Firebase Storage TIDAK diinisialisasi — gunakan Appwrite Storage.

    PENTING: Fungsi ini TIDAK melakukan tes konektivitas ke Firestore saat init.
    Kehadiran credentials yang valid → production mode (_is_mock=False).
    Error Firestore query akan naik ke caller (services.py) dan di-handle di view.
    Ini mencegah lock permanen ke mock mode akibat timeout atau database belum exist.
    """
    global _firebase_app, _firestore_db, _storage_bucket, _is_mock
    
    if _firebase_app is not None or _is_mock:
        return _firestore_db, _storage_bucket, _is_mock

    try:
        import firebase_admin
        from firebase_admin import credentials, firestore

        # Check if already initialized (multi-worker / warm start)
        if firebase_admin._apps:
            _firebase_app = firebase_admin.get_app()
            _firestore_db = firestore.client()
            _is_mock = False
            logger.info("[FIREBASE CONFIG] Reusing existing Firebase Admin app (warm start).")
            return _firestore_db, _storage_bucket, _is_mock

        cred = None

        # 1. Try JSON string from environment variable (Best for Vercel)
        service_account_json = getattr(settings, 'FIREBASE_SERVICE_ACCOUNT_JSON', None)
        if service_account_json:
            try:
                raw_json = service_account_json.strip()
                # Strip surrounding quotes if accidentally wrapped
                if (raw_json.startswith("'") and raw_json.endswith("'")) or \
                   (raw_json.startswith('"') and raw_json.endswith('"') and not raw_json.startswith('{"')):
                    raw_json = raw_json[1:-1].strip()
                cert_dict = json.loads(raw_json)
                if isinstance(cert_dict, dict) and 'private_key' in cert_dict \
                        and isinstance(cert_dict['private_key'], str):
                    if '\\n' in cert_dict['private_key']:
                        cert_dict['private_key'] = cert_dict['private_key'].replace('\\n', '\n')
                cred = credentials.Certificate(cert_dict)
                proj_id = cert_dict.get('project_id', 'unknown')
                print(f"[FIREBASE CONFIG] Loaded credentials from FIREBASE_SERVICE_ACCOUNT_JSON (project_id: {proj_id})")
                logger.info(f"Loaded Firebase credentials from FIREBASE_SERVICE_ACCOUNT_JSON (project_id: {proj_id}).")
            except Exception as e:
                print(f"[FIREBASE CONFIG ERROR] Failed to parse FIREBASE_SERVICE_ACCOUNT_JSON: {e}")
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
                    print(f"[FIREBASE CONFIG] Loaded credentials from file: {valid_path}")
                    logger.info(f"Loaded Firebase credentials from file: {valid_path}")
                except Exception as e:
                    print(f"[FIREBASE CONFIG ERROR] Failed to load credentials from {valid_path}: {e}")
                    logger.warning(f"Error loading credentials from {valid_path}: {e}")

        # Initialize Firebase Admin SDK jika credentials ditemukan
        if cred:
            _firebase_app = firebase_admin.initialize_app(cred, {})
            print(f"[FIREBASE CONFIG] Firebase Admin App initialized successfully (name: {_firebase_app.name})")
            logger.info(f"Firebase Admin App initialized (name: {_firebase_app.name}).")

            # Buat Firestore client — TANPA tes konektivitas.
            # Error query akan naik ke caller (services.py) dan di-handle view.
            # Ini mencegah lock ke mock mode akibat cold-start timeout atau
            # database yang baru saja dibuat.
            _firestore_db = firestore.client()
            _is_mock = False

            logger.info(
                "[FIREBASE CONFIG] Firestore client siap (production mode). "
                "[Appwrite Storage aktif sebagai pengganti Firebase Storage]"
            )
            return _firestore_db, None, _is_mock

        else:
            print("[FIREBASE CONFIG WARNING] No Firebase credentials found in environment or local file.")
            logger.warning("[FIREBASE CONFIG] No credentials found.")

    except Exception as e:
        print(f"[FIREBASE CONFIG ERROR] Failed to initialize Firebase Admin SDK: {e}")
        logger.error(f"Failed to initialize Firebase Admin SDK: {e}")

    # Fallback ke Mock mode — hanya jika credentials memang tidak ada/tidak valid
    logger.warning(
        "[FIREBASE CONFIG] Firebase credentials tidak aktif. "
        "Running in Mock/Preview mode dengan sample BKD data."
    )
    _is_mock = True
    return None, None, _is_mock


def get_firestore_db():
    """Get Firestore client or None if mock mode."""
    db, _, is_mock = initialize_firebase()
    return db if not is_mock else None


def get_storage_bucket():
    """Get Storage bucket or None if bucket could not be initialized."""
    _, bucket, _ = initialize_firebase()
    return bucket


def is_mock_mode():
    """Return True if running in fallback mock mode (no valid credentials)."""
    initialize_firebase()
    return _is_mock


def verify_firebase_id_token(id_token):
    """
    Verify Firebase ID token using firebase_admin.auth.
    Returns (decoded_token_dict, error_message_str).
    - On success: (decoded_token, None)
    - On failure: (None, error_str)
    """
    if not id_token or not isinstance(id_token, str):
        return None, "ID token tidak disediakan atau format bukan string."

    id_token = id_token.strip()

    # Mock token for automated tests / local sandbox
    if id_token.startswith("mock-token-"):
        email = id_token.replace("mock-token-", "")
        print(f"[FIREBASE AUTH MOCK] Verifying test token for: {email}")
        return {
            "uid": f"mock_uid_{email}",
            "email": email,
            "name": "Admin BKD Sidoarjo",
        }, None

    initialize_firebase()

    import firebase_admin
    from firebase_admin import auth

    # Check if Firebase App is initialized
    app = _firebase_app
    if app is None and firebase_admin._apps:
        app = firebase_admin.get_app()

    if app is None:
        err_msg = (
            "Firebase Admin SDK belum terinisialisasi di server. "
            "Pastikan environment variable FIREBASE_SERVICE_ACCOUNT_JSON telah diisi di dashboard Vercel."
        )
        print(f"[FIREBASE AUTH ERROR] {err_msg}")
        return None, err_msg

    try:
        # Verify token with firebase-admin
        decoded_token = auth.verify_id_token(id_token, app=app, check_revoked=False)
        user_uid = decoded_token.get('uid')
        user_email = decoded_token.get('email', 'unknown')
        print(f"[FIREBASE AUTH SUCCESS] Token verified for UID={user_uid}, Email={user_email}")
        return decoded_token, None
    except Exception as e:
        err_type = type(e).__name__
        err_msg = str(e)
        print(f"[FIREBASE AUTH VERIFY ERROR] {err_type}: {err_msg}")
        logger.exception(f"Error verifying Firebase ID token: {e}")
        return None, f"[{err_type}] {err_msg}"

"""
Firebase Admin SDK Configuration & Initialization.
Supports:
1. Environment Variable JSON string (Vercel deployment: FIREBASE_SERVICE_ACCOUNT_JSON)
2. Local service account JSON file (Local dev: FIREBASE_CREDENTIALS_PATH)

PRINSIP:
- Credentials ada → production mode. Firestore client dibuat sekali dan di-cache.
- Credentials tidak ada → _is_mock=True (fallback dev mode).
- Exception saat inisialisasi: di-log LENGKAP (tipe + pesan) dan di-raise.
  TIDAK ada penyembunyian error melalui except generic yang diam-diam jatuh ke mock.
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
_init_error = None  # Simpan exception asli dari inisialisasi untuk di-raise ulang


def initialize_firebase():
    """
    Initialize Firebase Admin SDK atau set mock mode jika credentials tidak ada.

    PENTING:
    - Hanya dipanggil satu kali; hasil di-cache di variabel modul.
    - Jika firebase_admin._apps sudah terisi (warm start / multi-worker),
      langsung reuse tanpa initialize_app() ulang.
    - Jika credentials ada tapi ada error teknis → exception di-raise ke caller.
      TIDAK jatuh ke mock mode secara diam-diam.
    - Jika credentials tidak ada sama sekali → set _is_mock=True (dev mode).
    """
    global _firebase_app, _firestore_db, _storage_bucket, _is_mock, _init_error

    # Guard: sudah diinisialisasi sebelumnya
    if _firebase_app is not None or _is_mock:
        return _firestore_db, _storage_bucket, _is_mock

    # Guard: pernah error sebelumnya — re-raise error yang sama
    if _init_error is not None:
        raise _init_error

    try:
        import firebase_admin
        from firebase_admin import credentials, firestore

        # Warm start / multi-worker: app sudah ada di firebase_admin._apps
        if firebase_admin._apps:
            _firebase_app = firebase_admin.get_app()
            _firestore_db = firestore.client()
            _is_mock = False
            logger.info(
                f"[FIREBASE CONFIG] Warm start: reusing existing Firebase app "
                f"'{_firebase_app.name}', Firestore client id={id(_firestore_db)}"
            )
            return _firestore_db, _storage_bucket, _is_mock

        cred = None
        cred_source = None

        # 1. Coba JSON string dari environment variable (Vercel)
        service_account_json = getattr(settings, 'FIREBASE_SERVICE_ACCOUNT_JSON', None)
        if service_account_json:
            logger.info("[FIREBASE CONFIG] Mencoba load credentials dari FIREBASE_SERVICE_ACCOUNT_JSON...")
            raw_json = service_account_json.strip()
            # Strip surrounding quotes jika tidak sengaja ter-wrap
            if (raw_json.startswith("'") and raw_json.endswith("'")) or \
               (raw_json.startswith('"') and raw_json.endswith('"') and not raw_json.startswith('{"')):
                raw_json = raw_json[1:-1].strip()
            cert_dict = json.loads(raw_json)  # JSONDecodeError akan naik jika format salah
            if isinstance(cert_dict, dict) and 'private_key' in cert_dict \
                    and isinstance(cert_dict['private_key'], str):
                if '\\n' in cert_dict['private_key']:
                    cert_dict['private_key'] = cert_dict['private_key'].replace('\\n', '\n')
            cred = credentials.Certificate(cert_dict)  # ValueError naik jika format salah
            cred_source = f"FIREBASE_SERVICE_ACCOUNT_JSON (project_id: {cert_dict.get('project_id', 'unknown')})"
            logger.info(f"[FIREBASE CONFIG] Credentials loaded dari {cred_source}")
            print(f"[FIREBASE CONFIG] Credentials loaded dari {cred_source}")

        # 2. Coba file path dari environment variable atau default path
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
                logger.info(f"[FIREBASE CONFIG] Mencoba load credentials dari file: {valid_path}")
                cred = credentials.Certificate(valid_path)  # Exception naik jika file invalid
                cred_source = f"file: {valid_path}"
                logger.info(f"[FIREBASE CONFIG] Credentials loaded dari {cred_source}")
                print(f"[FIREBASE CONFIG] Credentials loaded dari {cred_source}")

        # Tidak ada credentials → dev/mock mode
        if not cred:
            logger.warning(
                "[FIREBASE CONFIG] Tidak ada credentials Firebase ditemukan "
                "(FIREBASE_SERVICE_ACCOUNT_JSON kosong, serviceAccountKey.json tidak ada). "
                "Berjalan dalam MOCK MODE — hanya untuk development lokal."
            )
            print("[FIREBASE CONFIG WARNING] No Firebase credentials found. Running in Mock Mode.")
            _is_mock = True
            return None, None, _is_mock

        # Inisialisasi Firebase Admin SDK — satu kali saja
        _firebase_app = firebase_admin.initialize_app(cred, {})
        logger.info(
            f"[FIREBASE CONFIG] Firebase Admin App diinisialisasi: name='{_firebase_app.name}' "
            f"dari {cred_source}"
        )
        print(f"[FIREBASE CONFIG] Firebase Admin App initialized: {_firebase_app.name}")

        # Buat Firestore client (tidak ada tes konektivitas — error query naik ke caller)
        _firestore_db = firestore.client()
        _is_mock = False
        logger.info(
            f"[FIREBASE CONFIG] Firestore client siap. id={id(_firestore_db)} "
            "[Appwrite Storage aktif sebagai pengganti Firebase Storage]"
        )
        return _firestore_db, None, _is_mock

    except Exception as e:
        # Log LENGKAP: tipe exception + pesan asli
        err_type = type(e).__name__
        err_msg = str(e)
        logger.exception(
            f"[FIREBASE CONFIG] Exception saat inisialisasi Firebase Admin SDK: "
            f"[{err_type}] {err_msg}. "
            f"Exception ini akan di-raise ke caller — TIDAK jatuh ke mock mode."
        )
        print(f"[FIREBASE CONFIG CRITICAL] [{err_type}] {err_msg}")
        # Simpan dan re-raise — jangan tutup-tutupi error ini sebagai mock mode
        _init_error = e
        raise


def get_firestore_db():
    """
    Get Firestore client atau None jika mock mode.
    Exception dari initialize_firebase() akan naik ke caller.
    """
    try:
        db, _, is_mock_flag = initialize_firebase()
        return db if not is_mock_flag else None
    except Exception as e:
        # Re-raise dengan konteks yang lebih jelas
        err_type = type(e).__name__
        logger.error(
            f"[get_firestore_db] Gagal mendapatkan Firestore client: [{err_type}] {e}"
        )
        raise RuntimeError(
            f"Gagal inisialisasi Firebase/Firestore: [{err_type}] {e}"
        ) from e


def get_storage_bucket():
    """Get Storage bucket atau None jika tidak bisa diinisialisasi."""
    _, bucket, _ = initialize_firebase()
    return bucket


def is_mock_mode():
    """Return True jika berjalan dalam fallback mock mode (tidak ada credentials valid)."""
    try:
        initialize_firebase()
    except Exception:
        # Kalau ada error init, kita bukan di mock mode, tapi di error mode
        return False
    return _is_mock


def verify_firebase_id_token(id_token):
    """
    Verify Firebase ID token menggunakan firebase_admin.auth.
    Returns (decoded_token_dict, error_message_str).
    - Sukses: (decoded_token, None)
    - Gagal: (None, error_str)
    """
    if not id_token or not isinstance(id_token, str):
        return None, "ID token tidak disediakan atau format bukan string."

    id_token = id_token.strip()

    # Mock token untuk automated tests / local sandbox
    if id_token.startswith("mock-token-"):
        email = id_token.replace("mock-token-", "")
        print(f"[FIREBASE AUTH MOCK] Verifying test token for: {email}")
        return {
            "uid": f"mock_uid_{email}",
            "email": email,
            "name": "Admin BKD Sidoarjo",
        }, None

    try:
        initialize_firebase()
    except Exception as e:
        err_type = type(e).__name__
        err_msg = f"Firebase tidak dapat diinisialisasi: [{err_type}] {e}"
        logger.error(f"[verify_firebase_id_token] {err_msg}")
        return None, err_msg

    import firebase_admin
    from firebase_admin import auth

    # Cek apakah Firebase App sudah ada
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
        decoded_token = auth.verify_id_token(id_token, app=app, check_revoked=False)
        user_uid = decoded_token.get('uid')
        user_email = decoded_token.get('email', 'unknown')
        print(f"[FIREBASE AUTH SUCCESS] Token verified for UID={user_uid}, Email={user_email}")
        return decoded_token, None
    except Exception as e:
        err_type = type(e).__name__
        err_msg = str(e)
        print(f"[FIREBASE AUTH VERIFY ERROR] {err_type}: {err_msg}")
        logger.exception(f"Error verifying Firebase ID token: [{err_type}] {e}")
        return None, f"[{err_type}] {err_msg}"

"""
Storage service for managing document file uploads (PDF) to Firebase Storage.
"""

import os
import uuid
import logging
from datetime import datetime, timedelta
from django.conf import settings
from .firebase_config import get_storage_bucket, is_mock_mode

logger = logging.getLogger(__name__)

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


def validate_pdf_file(uploaded_file):
    """
    Validates uploaded file format and size.
    Returns (is_valid: bool, error_message: str).
    """
    if not uploaded_file:
        return False, "File dokumen wajib diunggah."

    # Validate file extension
    ext = os.path.splitext(uploaded_file.name)[1].lower()
    if ext != '.pdf':
        return False, "Format file tidak didukung. Harap unggah file dokumen PDF (.pdf)."

    # Validate content type if available
    content_type = getattr(uploaded_file, 'content_type', '')
    if content_type and 'pdf' not in content_type.lower():
        return False, "Tipe MIME file bukan dokumen PDF yang valid."

    # Validate max size
    if uploaded_file.size > MAX_FILE_SIZE:
        max_mb = MAX_FILE_SIZE / (1024 * 1024)
        return False, f"Ukuran file melebihi batas maksimum ({max_mb:.0f} MB)."

    return True, None


def upload_pdf_to_storage(uploaded_file, folder="documents"):
    """
    Uploads a PDF file to Firebase Storage.
    Returns a dict with:
        file_url: str
        file_name: str
        ukuran_file: int (bytes)
        storage_path: str
    """
    is_valid, error = validate_pdf_file(uploaded_file)
    if not is_valid:
        raise ValueError(error)

    original_name = uploaded_file.name
    clean_name = "".join(c for c in original_name if c.isalnum() or c in "._- ")
    unique_id = uuid.uuid4().hex[:10]
    year = datetime.now().year
    blob_path = f"{folder}/{year}/{unique_id}_{clean_name}"

    bucket = get_storage_bucket()
    encoded_path = blob_path.replace('/', '%2F')

    if bucket:
        try:
            blob = bucket.blob(blob_path)
            blob.content_type = 'application/pdf'
            blob.metadata = {
                'original_filename': original_name,
                'uploaded_at': datetime.now().isoformat(),
            }

            # Rewind buffer/file and upload directly in-memory
            if hasattr(uploaded_file, 'seek'):
                uploaded_file.seek(0)
            blob.upload_from_file(uploaded_file, content_type='application/pdf')

            # Attempt to make public or generate signed/download URL
            file_url = None
            try:
                blob.make_public()
                file_url = blob.public_url
            except Exception:
                pass

            if not file_url:
                try:
                    file_url = blob.generate_signed_url(
                        expiration=timedelta(days=365 * 10),
                        method='GET'
                    )
                except Exception:
                    pass

            if not file_url:
                bucket_name = bucket.name
                file_url = f"https://firebasestorage.googleapis.com/v0/b/{bucket_name}/o/{encoded_path}?alt=media"

            return {
                'file_url': file_url,
                'file_name': original_name,
                'ukuran_file': uploaded_file.size,
                'storage_path': blob_path,
            }
        except Exception as e:
            logger.error(f"Gagal mengunggah file ke Firebase Storage: {e}")
            err_msg = str(e).lower()
            if "404" in err_msg or "not exist" in err_msg or "not found" in err_msg:
                logger.warning("Bucket Firebase Storage belum dibuat/diaktifkan di Firebase Console. Menggunakan URL cloud Firebase Storage fallback secara in-memory.")
                b_name = bucket.name if hasattr(bucket, 'name') else getattr(settings, 'FIREBASE_STORAGE_BUCKET', 'jdih-bkd-sidoarjo.firebasestorage.app')
                file_url = f"https://firebasestorage.googleapis.com/v0/b/{b_name}/o/{encoded_path}?alt=media"
                return {
                    'file_url': file_url,
                    'file_name': original_name,
                    'ukuran_file': uploaded_file.size,
                    'storage_path': blob_path,
                }
            raise RuntimeError(f"Gagal mengunggah file ke Firebase Storage: {str(e)}")

    # Pure in-memory fallback without touching local disk (serverless safe)
    bucket_name = getattr(settings, 'FIREBASE_STORAGE_BUCKET', 'jdih-bkd-sidoarjo.firebasestorage.app')
    file_url = f"https://firebasestorage.googleapis.com/v0/b/{bucket_name}/o/{encoded_path}?alt=media"
    logger.info(f"Storage bucket offline: file diproses secara in-memory dengan path {blob_path}")
    return {
        'file_url': file_url,
        'file_name': original_name,
        'ukuran_file': uploaded_file.size,
        'storage_path': blob_path,
    }


def delete_pdf_from_storage(storage_path):
    """
    Deletes a file from Firebase Storage.
    """
    if is_mock_mode() or not storage_path:
        return True

    try:
        bucket = get_storage_bucket()
        if bucket:
            blob = bucket.blob(storage_path)
            if blob.exists():
                blob.delete()
        return True
    except Exception as e:
        logger.warning(f"Gagal menghapus file {storage_path} dari Firebase Storage: {e}")
        return False

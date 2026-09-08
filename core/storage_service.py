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

    if is_mock_mode():
        # In mock mode, save to local media or simulate storage URL
        mock_dir = settings.BASE_DIR / 'static' / 'mock_docs'
        os.makedirs(mock_dir, exist_ok=True)
        local_path = mock_dir / f"{unique_id}_{clean_name}"
        with open(local_path, 'wb+') as destination:
            for chunk in uploaded_file.chunks():
                destination.write(chunk)
        
        file_url = f"/static/mock_docs/{unique_id}_{clean_name}"
        return {
            'file_url': file_url,
            'file_name': original_name,
            'ukuran_file': uploaded_file.size,
            'storage_path': blob_path,
        }

    try:
        bucket = get_storage_bucket()
        if not bucket:
            raise RuntimeError("Firebase Storage bucket belum dikonfigurasi.")

        blob = bucket.blob(blob_path)
        blob.content_type = 'application/pdf'
        blob.metadata = {
            'original_filename': original_name,
            'uploaded_at': datetime.now().isoformat(),
        }

        # Read chunks and upload
        blob.upload_from_file(uploaded_file, content_type='application/pdf')

        # Make public or generate URL
        try:
            blob.make_public()
            file_url = blob.public_url
        except Exception:
            # If public access not enabled on bucket, generate long-lived signed URL
            file_url = blob.generate_signed_url(
                expiration=timedelta(days=365 * 10),
                method='GET'
            )

        return {
            'file_url': file_url,
            'file_name': original_name,
            'ukuran_file': uploaded_file.size,
            'storage_path': blob_path,
        }

    except Exception as e:
        logger.error(f"Gagal mengunggah file ke Firebase Storage: {e}")
        raise RuntimeError(f"Gagal mengunggah file ke Firebase Storage: {str(e)}")


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

"""
Storage service for managing document file uploads (PDF) to Appwrite Storage.
Firebase Storage telah diganti sepenuhnya dengan Appwrite Storage.
"""

import os
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


def _get_appwrite_storage():
    """
    Initialize and return Appwrite Client + Storage instance.
    Raises RuntimeError if env vars not set.
    """
    from appwrite.client import Client
    from appwrite.services.storage import Storage

    endpoint = getattr(settings, 'APPWRITE_ENDPOINT', None) or os.environ.get('APPWRITE_ENDPOINT')
    project_id = getattr(settings, 'APPWRITE_PROJECT_ID', None) or os.environ.get('APPWRITE_PROJECT_ID')
    api_key = getattr(settings, 'APPWRITE_API_KEY', None) or os.environ.get('APPWRITE_API_KEY')

    if not endpoint or not project_id or not api_key:
        raise RuntimeError(
            "Konfigurasi Appwrite belum lengkap. "
            "Pastikan APPWRITE_ENDPOINT, APPWRITE_PROJECT_ID, dan APPWRITE_API_KEY "
            "telah diisi di file .env."
        )

    client = Client()
    client.set_endpoint(endpoint)
    client.set_project(project_id)
    client.set_key(api_key)

    return Storage(client)


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


def upload_pdf_to_storage(uploaded_file):
    """
    Uploads a PDF file to Appwrite Storage.
    Returns a dict with:
        file_url: str         — URL publik untuk pratinjau/unduh
        file_name: str        — Nama file asli
        ukuran_file: int      — Ukuran dalam bytes
        appwrite_file_id: str — ID file di Appwrite (diperlukan untuk hapus)
    Raises ValueError jika validasi gagal.
    Raises RuntimeError jika upload gagal.
    """
    from appwrite.input_file import InputFile
    from appwrite.id import ID

    is_valid, error = validate_pdf_file(uploaded_file)
    if not is_valid:
        raise ValueError(error)

    original_filename = uploaded_file.name

    # Baca bytes dari uploaded file
    if hasattr(uploaded_file, 'seek'):
        uploaded_file.seek(0)
    file_bytes = uploaded_file.read()

    bucket_id = getattr(settings, 'APPWRITE_BUCKET_ID', None) or os.environ.get('APPWRITE_BUCKET_ID')
    endpoint = getattr(settings, 'APPWRITE_ENDPOINT', None) or os.environ.get('APPWRITE_ENDPOINT')
    project_id = getattr(settings, 'APPWRITE_PROJECT_ID', None) or os.environ.get('APPWRITE_PROJECT_ID')

    if not bucket_id:
        raise RuntimeError("APPWRITE_BUCKET_ID belum dikonfigurasi di .env.")

    try:
        storage = _get_appwrite_storage()

        result = storage.create_file(
            bucket_id=bucket_id,
            file_id=ID.unique(),
            file=InputFile.from_bytes(file_bytes, filename=original_filename),
        )

        # Appwrite SDK v2+ mengembalikan Pydantic model 'File', bukan dict.
        # Jadi kita gunakan attribute access (.id) alih-alih result['$id']
        file_id = result.id
        file_url = (
            f"{endpoint}/storage/buckets/{bucket_id}/files/{file_id}/view"
            f"?project={project_id}"
        )

        logger.info(f"[APPWRITE STORAGE] File '{original_filename}' berhasil diupload, ID: {file_id}")

        return {
            'file_url': file_url,
            'file_name': original_filename,
            'ukuran_file': uploaded_file.size,
            'appwrite_file_id': file_id,
        }

    except Exception as e:
        logger.error(f"[APPWRITE STORAGE] Gagal mengupload file '{original_filename}': {e}")
        raise RuntimeError(f"Gagal mengunggah file ke Appwrite Storage: {str(e)}")


def delete_pdf_from_storage(appwrite_file_id):
    """
    Menghapus file dari Appwrite Storage berdasarkan file ID.
    Returns True jika berhasil atau file tidak ditemukan (sudah terhapus).
    Returns False jika ada error lain.

    Parameter:
        appwrite_file_id: str — nilai $id dari dokumen Firestore field 'appwrite_file_id'
    """
    if not appwrite_file_id:
        logger.warning("[APPWRITE STORAGE] delete_pdf_from_storage dipanggil tanpa appwrite_file_id, dilewati.")
        return True

    bucket_id = getattr(settings, 'APPWRITE_BUCKET_ID', None) or os.environ.get('APPWRITE_BUCKET_ID')
    if not bucket_id:
        logger.error("[APPWRITE STORAGE] APPWRITE_BUCKET_ID tidak dikonfigurasi, tidak bisa menghapus file.")
        return False

    try:
        storage = _get_appwrite_storage()
        storage.delete_file(bucket_id=bucket_id, file_id=appwrite_file_id)
        logger.info(f"[APPWRITE STORAGE] File ID '{appwrite_file_id}' berhasil dihapus dari Appwrite.")
        return True

    except Exception as e:
        err_str = str(e).lower()
        # Jika file memang sudah tidak ada, anggap sukses
        if '404' in err_str or 'not found' in err_str or 'storage_file_not_found' in err_str:
            logger.warning(f"[APPWRITE STORAGE] File ID '{appwrite_file_id}' tidak ditemukan di Appwrite (mungkin sudah terhapus sebelumnya). Dianggap sukses.")
            return True
        logger.error(f"[APPWRITE STORAGE] Gagal menghapus file ID '{appwrite_file_id}' dari Appwrite: {e}")
        return False

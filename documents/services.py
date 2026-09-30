"""
Document Service Layer for JDIH BKD Sidoarjo.
Handles interactions with Firestore collection 'documents'.

MODE OPERASI (PRODUCTION-ONLY):
- SELALU query Firestore. Tidak ada fallback ke data palsu dalam kondisi apapun.
- Kegagalan Firestore ditangkap di view dan menampilkan pesan error yang jujur ke user.
- _MOCK_DOCUMENTS telah DIHAPUS TOTAL dari codebase secara sengaja.
  Referensi ke _MOCK_DOCUMENTS akan langsung menghasilkan NameError yang terlihat.

Untuk development lokal:
- Pastikan FIREBASE_CREDENTIALS_PATH menunjuk ke serviceAccountKey.json yang valid, ATAU
- Isi FIREBASE_SERVICE_ACCOUNT_JSON di environment.
- Untuk seed data awal ke Firestore: python manage.py seed_bkd_documents
"""

import uuid
import logging
from datetime import datetime
from google.cloud import firestore
from core.firebase_config import get_firestore_db

logger = logging.getLogger(__name__)

COLLECTION_NAME = 'documents'

# Standard Document Types
DOCUMENT_TYPES = [
    ('perbup', 'Peraturan Bupati (Perbup)'),
    ('sk', 'Keputusan Bupati / Kepala BKD (SK)'),
    ('perda', 'Peraturan Daerah (Perda)'),
    ('se', 'Surat Edaran (SE)'),
    ('instruksi', 'Instruksi Bupati'),
    ('permen', 'Peraturan Menteri / BKN'),
    ('lainnya', 'Lainnya'),
]

# Standard Categories for BKD / Kepegawaian
CATEGORIES = [
    'Manajemen Kinerja & SKP',
    'Pemberhentian & Pensiun',
    'Kepegawaian',
    'Kenaikan Pangkat & Gaji Berkala',
    'Mutasi, Promosi & Jabatan Fungsional',
    'Kesejahteraan & Cuti',
    'Disiplin Pegawai & Kode Etik',
    'Pengembangan Kompetensi & Diklat',
    'Tata Kelola Kepegawaian Daerah',
]

# Standard Statuses
STATUS_CHOICES = [
    ('berlaku', 'Berlaku'),
    ('diubah', 'Diubah'),
    ('dicabut', 'Dicabut'),
]

# NOTE: _MOCK_DOCUMENTS telah DIHAPUS TOTAL dari codebase.
# Tidak ada data palsu di sini. Referensi ke _MOCK_DOCUMENTS = NameError.


def _require_firestore_db():
    """
    Mendapatkan Firestore DB client. Raise RuntimeError eksplisit jika tidak tersedia.
    Memastikan tidak ada jalur kode yang bisa diam-diam melewati error koneksi Firestore.
    """
    db = get_firestore_db()
    if db is None:
        raise RuntimeError(
            "Firestore tidak dapat diinisialisasi. "
            "Pastikan FIREBASE_SERVICE_ACCOUNT_JSON (Vercel) atau "
            "FIREBASE_CREDENTIALS_PATH (lokal) sudah dikonfigurasi dengan benar. "
            "TIDAK ADA fallback ke data palsu — konfigurasi credentials harus diselesaikan."
        )
    return db


def _safe_count(val: object) -> int:
    """
    Konversi aman nilai field Firestore ke int untuk sorting/counting.
    Menangani tipe dinamis dari dict Firestore: None, int, float, str, datetime, dll.
    """
    if isinstance(val, bool):
        return 0
    if isinstance(val, (int, float)):
        return int(val)
    if isinstance(val, str):
        try:
            return int(val)
        except ValueError:
            return 0
    return 0


def _format_firestore_doc(doc_snapshot):
    """Formats Firestore document snapshot into standardized dictionary."""
    data = doc_snapshot.to_dict()
    data['id'] = doc_snapshot.id
    for field in ['tanggal_terbit', 'created_at', 'updated_at']:
        val = data.get(field)
        if hasattr(val, 'to_datetime'):
            data[field] = val.to_datetime()
    return data


def _get_raw_dataset():
    """
    Helper internal: ambil SEMUA dokumen dari Firestore.
    - SELALU query Firestore - tidak ada fallback mock.
    - Exception naik ke caller jika Firestore gagal.
    - Return list (bisa [] jika Firestore kosong, bukan error).
    """
    db = _require_firestore_db()
    logger.info(
        f"[_get_raw_dataset] Firestore client id={id(db)} "
        f"- query collection '{COLLECTION_NAME}'"
    )
    items = [_format_firestore_doc(doc) for doc in db.collection(COLLECTION_NAME).stream()]
    logger.info(f"[_get_raw_dataset] Fetched {len(items)} docs from Firestore.")
    return items


def get_documents(
    search_query=None,
    jenis=None,
    tahun=None,
    kategori=None,
    status=None,
    include_deleted=False,
    sort_by='terbaru',
    page=1,
    page_size=9
):
    """
    Search, filter, dan paginate dokumen dari Firestore.

    SELALU query Firestore - tidak ada fallback ke data palsu.
    Dashboard admin dan beranda publik keduanya memanggil fungsi ini (satu sumber data).
    Kegagalan Firestore -> exception naik ke caller (view).

    Returns a dict with:
        items, total_items, total_pages, current_page,
        has_previous, has_next, previous_page_number, next_page_number, page_range
    """
    db = _require_firestore_db()
    coll_ref = db.collection(COLLECTION_NAME)
    docs = coll_ref.stream()
    results = [_format_firestore_doc(doc) for doc in docs]
    logger.info(f"[get_documents] Firestore: fetched {len(results)} raw docs.")

    # Filter: deleted
    if not include_deleted:
        results = [d for d in results if d.get('status') != 'dihapus']
    elif include_deleted == 'only':
        results = [d for d in results if d.get('status') == 'dihapus']

    # Filter: jenis
    if jenis:
        results = [d for d in results if str(d.get('jenis_dokumen', '')).lower() == jenis.lower()]

    # Filter: tahun
    if tahun:
        try:
            results = [d for d in results if int(str(d.get('tahun', 0))) == int(tahun)]
        except ValueError:
            pass

    # Filter: kategori
    if kategori:
        results = [d for d in results if d.get('kategori') == kategori]

    # Filter: status
    if status and status != 'semua':
        results = [d for d in results if str(d.get('status', '')).lower() == status.lower()]

    # Search query across multi-fields
    if search_query:
        sq = search_query.strip().lower()
        results = [
            d for d in results
            if sq in str(d.get('judul', '')).lower()
            or sq in str(d.get('nomor_dokumen', '')).lower()
            or sq in str(d.get('deskripsi', '')).lower()
            or any(sq in t.lower() for t in (d.get('tags') if isinstance(d.get('tags'), list) else []) if isinstance(t, str))
        ]

    # Sorting
    if sort_by == 'populer':
        results.sort(key=lambda x: _safe_count(x.get('view_count')) + _safe_count(x.get('download_count')) * 2, reverse=True)
    elif sort_by == 'tahun_asc':
        results.sort(key=lambda x: (x.get('tahun', 0), x.get('tanggal_terbit') or datetime.min))
    elif sort_by == 'tahun_desc':
        results.sort(key=lambda x: (x.get('tahun', 0), x.get('tanggal_terbit') or datetime.min), reverse=True)
    else:  # terbaru
        results.sort(
            key=lambda x: x.get('tanggal_terbit') or x.get('created_at') or datetime.min,
            reverse=True
        )

    # Pagination
    total_items = len(results)
    page_size = max(1, page_size)
    total_pages = max(1, (total_items + page_size - 1) // page_size)
    page = max(1, min(page, total_pages))
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size

    return {
        'items': results[start_idx:end_idx],
        'total_items': total_items,
        'total_pages': total_pages,
        'current_page': page,
        'has_previous': page > 1,
        'has_next': page < total_pages,
        'previous_page_number': page - 1,
        'next_page_number': page + 1,
        'page_range': list(range(1, total_pages + 1)),
    }


def get_document_by_id(doc_id):
    """
    Retrieve single document by ID from Firestore.
    SELALU query Firestore - exception naik ke caller jika gagal.
    Return None jika dokumen tidak ditemukan (bukan error).
    """
    db = _require_firestore_db()
    doc_ref = db.collection(COLLECTION_NAME).document(doc_id)
    doc = doc_ref.get()
    if doc.exists:
        return _format_firestore_doc(doc)
    return None


def create_document(data, user_uid="admin_bkd"):
    """
    Create a new document in Firestore.
    SELALU tulis ke Firestore - exception naik ke caller jika gagal.
    """
    db = _require_firestore_db()
    now = datetime.now()
    doc_id = str(uuid.uuid4())
    doc_data = {
        'id': doc_id,
        'judul': data.get('judul', '').strip(),
        'nomor_dokumen': data.get('nomor_dokumen', '').strip(),
        'jenis_dokumen': data.get('jenis_dokumen', 'perbup'),
        'kategori': data.get('kategori', 'Tata Kelola Kepegawaian Daerah'),
        'tags': [t.strip() for t in data.get('tags', []) if t.strip()],
        'tahun': int(data.get('tahun', now.year)),
        'tanggal_terbit': data.get('tanggal_terbit', now),
        'status': data.get('status', 'berlaku'),
        'deskripsi': data.get('deskripsi', '').strip(),
        'file_url': data.get('file_url', ''),
        'file_name': data.get('file_name', ''),
        'ukuran_file': int(data.get('ukuran_file', 0)),
        'appwrite_file_id': data.get('appwrite_file_id', ''),
        'view_count': 0,
        'download_count': 0,
        'created_at': now,
        'updated_at': now,
        'created_by': user_uid,
    }

    doc_ref = db.collection(COLLECTION_NAME).document(doc_id)
    doc_ref.set(doc_data)
    logger.info(f"[create_document] Firestore: created doc_id={doc_id}")
    return doc_data


def update_document(doc_id, data):
    """
    Update document metadata in Firestore.
    SELALU update Firestore - exception naik ke caller jika gagal.
    """
    db = _require_firestore_db()
    now = datetime.now()
    clean_data = {k: v for k, v in data.items() if k not in ['id', 'created_at', 'created_by']}
    clean_data['updated_at'] = now
    doc_ref = db.collection(COLLECTION_NAME).document(doc_id)
    doc_ref.update(clean_data)
    logger.info(f"[update_document] Firestore: updated doc_id={doc_id}")
    return get_document_by_id(doc_id)


def delete_document(doc_id, soft=True):
    """
    Delete document. If soft=True, sets status='dihapus'. If soft=False, permanent delete.
    SELALU operasi ke Firestore - exception naik ke caller jika gagal.
    """
    db = _require_firestore_db()
    doc_ref = db.collection(COLLECTION_NAME).document(doc_id)
    if soft:
        doc_ref.update({'status': 'dihapus', 'updated_at': datetime.now()})
    else:
        doc_ref.delete()
    logger.info(f"[delete_document] Firestore: doc_id={doc_id} soft={soft}")
    return True


def restore_document(doc_id):
    """
    Restore a soft-deleted document to 'berlaku'.
    SELALU operasi ke Firestore - exception naik ke caller jika gagal.
    """
    db = _require_firestore_db()
    doc_ref = db.collection(COLLECTION_NAME).document(doc_id)
    doc_ref.update({'status': 'berlaku', 'updated_at': datetime.now()})
    logger.info(f"[restore_document] Firestore: restored doc_id={doc_id}")
    return True


def bulk_delete_documents(doc_ids, soft=True):
    """
    Bulk delete multiple documents via WriteBatch (atomic, max 500 ops).
    SELALU operasi ke Firestore - exception naik ke caller jika gagal.
    """
    if not doc_ids:
        return 0
    db = _require_firestore_db()
    batch = db.batch()
    now = datetime.now()
    for doc_id in doc_ids:
        doc_ref = db.collection(COLLECTION_NAME).document(doc_id)
        if soft:
            batch.update(doc_ref, {'status': 'dihapus', 'updated_at': now})
        else:
            batch.delete(doc_ref)
    batch.commit()
    logger.info(f"[bulk_delete_documents] Firestore: {len(doc_ids)} docs, soft={soft}")
    return len(doc_ids)


def bulk_restore_documents(doc_ids):
    """
    Bulk restore multiple documents via WriteBatch.
    SELALU operasi ke Firestore - exception naik ke caller jika gagal.
    """
    if not doc_ids:
        return 0
    db = _require_firestore_db()
    batch = db.batch()
    now = datetime.now()
    for doc_id in doc_ids:
        doc_ref = db.collection(COLLECTION_NAME).document(doc_id)
        batch.update(doc_ref, {'status': 'berlaku', 'updated_at': now})
    batch.commit()
    logger.info(f"[bulk_restore_documents] Firestore: restored {len(doc_ids)} docs")
    return len(doc_ids)


def increment_view_count(doc_id):
    """Increment document view count. Non-critical -- silent skip on failure."""
    try:
        db = get_firestore_db()
        if db is None:
            logger.warning(f"[increment_view_count] Firestore tidak tersedia untuk doc_id={doc_id}, skip.")
            return
        doc_ref = db.collection(COLLECTION_NAME).document(doc_id)
        doc_ref.update({'view_count': firestore.Increment(1)})
    except Exception as e:
        logger.warning(f"[increment_view_count] Skipped for {doc_id}: {e}")


def increment_download_count(doc_id):
    """Increment document download count. Non-critical -- silent skip on failure."""
    try:
        db = get_firestore_db()
        if db is None:
            logger.warning(f"[increment_download_count] Firestore tidak tersedia untuk doc_id={doc_id}, skip.")
            return
        doc_ref = db.collection(COLLECTION_NAME).document(doc_id)
        doc_ref.update({'download_count': firestore.Increment(1)})
    except Exception as e:
        logger.warning(f"[increment_download_count] Skipped for {doc_id}: {e}")


def get_statistics():
    """
    Returns general metrics for public hero and admin dashboard.

    SELALU mengambil dari Firestore - tidak ada mock fallback.
    Dokumen dengan status 'dihapus' (soft-deleted) TIDAK ikut terhitung.
    Field jenis_dokumen di-compare lowercase agar tidak case-sensitive.

    Dashboard admin dan beranda publik KEDUANYA memanggil fungsi ini (satu sumber data).
    """
    all_docs = _get_raw_dataset()

    sample_jenis = [d.get('jenis_dokumen') for d in all_docs[:5]]
    sample_status = [d.get('status') for d in all_docs[:5]]
    logger.info(
        f"[get_statistics] source=Firestore "
        f"total_raw={len(all_docs)} "
        f"sample_jenis={sample_jenis} "
        f"sample_status={sample_status}"
    )

    docs = [d for d in all_docs if str(d.get('status', '')).lower() != 'dihapus']
    logger.info(
        f"[get_statistics] setelah filter dihapus: total_aktif={len(docs)} "
        f"(dikecualikan={len(all_docs) - len(docs)} dokumen dengan status='dihapus')"
    )

    total_docs = len(docs)
    total_views = sum(d.get('view_count', 0) for d in docs)
    total_downloads = sum(d.get('download_count', 0) for d in docs)

    perbup_count = sum(1 for d in docs if str(d.get('jenis_dokumen', '')).lower() == 'perbup')
    sk_count = sum(1 for d in docs if str(d.get('jenis_dokumen', '')).lower() == 'sk')
    perda_count = sum(1 for d in docs if str(d.get('jenis_dokumen', '')).lower() == 'perda')
    se_count = sum(1 for d in docs if str(d.get('jenis_dokumen', '')).lower() == 'se')
    instruksi_count = sum(1 for d in docs if str(d.get('jenis_dokumen', '')).lower() == 'instruksi')
    permen_count = sum(1 for d in docs if str(d.get('jenis_dokumen', '')).lower() == 'permen')

    berlaku_count = sum(1 for d in docs if str(d.get('status', '')).lower() == 'berlaku')
    diubah_count = sum(1 for d in docs if str(d.get('status', '')).lower() == 'diubah')
    dicabut_count = sum(1 for d in docs if str(d.get('status', '')).lower() == 'dicabut')

    logger.info(
        f"[get_statistics] HASIL: total_docs={total_docs} "
        f"perbup={perbup_count} sk={sk_count} se={se_count} "
        f"perda={perda_count} instruksi={instruksi_count} permen={permen_count} | "
        f"berlaku={berlaku_count} diubah={diubah_count} dicabut={dicabut_count}"
    )

    return {
        'total_documents': total_docs,
        'total_views': total_views,
        'total_downloads': total_downloads,
        'perbup_count': perbup_count,
        'sk_count': sk_count,
        'perda_count': perda_count,
        'se_count': se_count,
        'instruksi_count': instruksi_count,
        'permen_count': permen_count,
        'berlaku_count': berlaku_count,
        'diubah_count': diubah_count,
        'dicabut_count': dicabut_count,
    }


def get_available_years():
    """Returns sorted list of unique years in descending order."""
    years = {int(d.get('tahun')) for d in _get_raw_dataset() if d.get('tahun')}
    current_year = datetime.now().year
    years.add(current_year)
    return sorted(list(years), reverse=True)
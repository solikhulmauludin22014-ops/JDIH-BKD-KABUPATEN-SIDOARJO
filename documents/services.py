"""
Document Service Layer for JDIH BKD Sidoarjo.
Handles interactions with Firestore collection 'documents'.

MODE OPERASI:
- Production (Vercel, kredensial Firebase ada): SELALU query Firestore.
  Tidak ada fallback ke mock dalam kondisi apapun.
  Kegagalan Firestore akan menghasilkan exception yang naik ke view.
- Development lokal (tanpa serviceAccountKey.json): Gunakan _MOCK_DOCUMENTS
  sebagai dataset in-memory untuk pengembangan dan preview UI.

NOTE: _MOCK_DOCUMENTS TIDAK PERNAH digunakan di production.
Untuk mengisi data awal Firestore (dev only), jalankan:
    python manage.py seed_bkd_documents
"""

import uuid
import logging
from datetime import datetime
from google.cloud import firestore
from core.firebase_config import get_firestore_db, is_mock_mode

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
]

# Standard Categories for BKD / Kepegawaian
CATEGORIES = [
    'Manajemen Kinerja & SKP',
    'Pengadaan ASN (CPNS & PPPK)',
    'Mutasi, Promosi & Jabatan Fungsional',
    'Kenaikan Pangkat & Gaji Berkala',
    'Disiplin Pegawai & Kode Etik',
    'Pengembangan Kompetensi & Diklat',
    'Kesejahteraan, Cuti & Pensiun',
    'Tata Kelola Kepegawaian Daerah',
]

# Standard Statuses
STATUS_CHOICES = [
    ('berlaku', 'Berlaku'),
    ('diubah', 'Diubah'),
    ('dicabut', 'Dicabut'),
]

# In-Memory Seed/Mock Documents for local testing & instant preview
_MOCK_DOCUMENTS = [
    {
        'id': 'doc-bkd-001',
        'judul': 'Pedoman Pelaksanaan Evaluasi Kinerja Pegawai Negeri Sipil di Lingkungan Pemerintah Kabupaten Sidoarjo',
        'nomor_dokumen': 'Perbup No. 42 Tahun 2023',
        'jenis_dokumen': 'perbup',
        'kategori': 'Manajemen Kinerja & SKP',
        'tags': ['kinerja', 'skp', 'pns', 'evaluasi', 'bkd'],
        'tahun': 2023,
        'tanggal_terbit': datetime(2023, 8, 15, 9, 0),
        'status': 'berlaku',
        'deskripsi': 'Peraturan ini mengatur tata cara dan standar operasional pelaksanaan penilaian kinerja pegawai negeri sipil tahunan dan periodik guna menjamin akuntabilitas serta meritokrasi birokrasi Sidoarjo.',
        'file_url': 'https://raw.githubusercontent.com/mozilla/pdf.js/ba2edeae/examples/learning/helloworld.pdf',
        'file_name': 'Perbup_42_2023_Manajemen_Kinerja_PNS.pdf',
        'ukuran_file': 1245184,
        'view_count': 1420,
        'download_count': 685,
        'created_at': datetime(2023, 8, 15, 10, 0),
        'updated_at': datetime(2023, 8, 15, 10, 0),
        'created_by': 'admin_bkd_sidoarjo',
    },
    {
        'id': 'doc-bkd-002',
        'judul': 'Penetapan Kebutuhan Pegawai Pemerintah dengan Perjanjian Kerja (PPPK) di Lingkungan Pemerintah Kabupaten Sidoarjo Formasi Tahun Anggaran 2024',
        'nomor_dokumen': 'Keputusan Bupati No. 188/245/438.1.1/2024',
        'jenis_dokumen': 'sk',
        'kategori': 'Pengadaan ASN (CPNS & PPPK)',
        'tags': ['pppk', 'formasi', 'casn', 'guru', 'nakes', 'teknis'],
        'tahun': 2024,
        'tanggal_terbit': datetime(2024, 3, 20, 8, 30),
        'status': 'berlaku',
        'deskripsi': 'Penetapan rincian kebutuhan dan alokasi formasi PPPK untuk tenaga guru, tenaga kesehatan, dan tenaga teknis di lingkungan Pemkab Sidoarjo.',
        'file_url': 'https://raw.githubusercontent.com/mozilla/pdf.js/ba2edeae/examples/learning/helloworld.pdf',
        'file_name': 'SK_Bupati_188_245_2024_Formasi_PPPK.pdf',
        'ukuran_file': 892416,
        'view_count': 3240,
        'download_count': 1950,
        'created_at': datetime(2024, 3, 20, 9, 15),
        'updated_at': datetime(2024, 3, 20, 9, 15),
        'created_by': 'admin_bkd_sidoarjo',
    },
    {
        'id': 'doc-bkd-003',
        'judul': 'Petunjuk Teknis Pelaksanaan Penyesuaian Ijazah dan Ujian Dinas bagi PNS Kabupaten Sidoarjo',
        'nomor_dokumen': 'SE Kepala BKD No. 800/142/438.5.2/2024',
        'jenis_dokumen': 'se',
        'kategori': 'Pengembangan Kompetensi & Diklat',
        'tags': ['ujian dinas', 'penyesuaian ijazah', 'kenaikan pangkat'],
        'tahun': 2024,
        'tanggal_terbit': datetime(2024, 5, 12, 10, 0),
        'status': 'berlaku',
        'deskripsi': 'Surat Edaran mengenai jadwal, persyaratan berkas, dan mekanisme Computer Assisted Test (CAT) untuk penyesuaian ijazah dan ujian dinas tingkat I & II.',
        'file_url': 'https://raw.githubusercontent.com/mozilla/pdf.js/ba2edeae/examples/learning/helloworld.pdf',
        'file_name': 'SE_BKD_Penyesuaian_Ijazah_2024.pdf',
        'ukuran_file': 655360,
        'view_count': 980,
        'download_count': 420,
        'created_at': datetime(2024, 5, 12, 11, 0),
        'updated_at': datetime(2024, 5, 12, 11, 0),
        'created_by': 'admin_bkd_sidoarjo',
    },
    {
        'id': 'doc-bkd-004',
        'judul': 'Tata Cara Mutasi, Rotasi, dan Promosi Pegawai Negeri Sipil di Lingkungan Pemkab Sidoarjo',
        'nomor_dokumen': 'Perbup No. 15 Tahun 2022',
        'jenis_dokumen': 'perbup',
        'kategori': 'Mutasi, Promosi & Jabatan Fungsional',
        'tags': ['mutasi', 'rotasi', 'promosi', 'talent pool'],
        'tahun': 2022,
        'tanggal_terbit': datetime(2022, 4, 10, 9, 0),
        'status': 'diubah',
        'deskripsi': 'Pedoman manajemen mutasi dan rotasi internal antar perangkat daerah. Telah diubah sebagian ketentuannya oleh Perbup No. 33 Tahun 2024.',
        'file_url': 'https://raw.githubusercontent.com/mozilla/pdf.js/ba2edeae/examples/learning/helloworld.pdf',
        'file_name': 'Perbup_15_2022_Mutasi_PNS.pdf',
        'ukuran_file': 1450000,
        'view_count': 1850,
        'download_count': 810,
        'created_at': datetime(2022, 4, 10, 10, 0),
        'updated_at': datetime(2024, 6, 1, 14, 0),
        'created_by': 'admin_bkd_sidoarjo',
    },
    {
        'id': 'doc-bkd-005',
        'judul': 'Perubahan atas Peraturan Bupati No. 15 Tahun 2022 tentang Tata Cara Mutasi, Rotasi, dan Promosi PNS',
        'nomor_dokumen': 'Perbup No. 33 Tahun 2024',
        'jenis_dokumen': 'perbup',
        'kategori': 'Mutasi, Promosi & Jabatan Fungsional',
        'tags': ['mutasi', 'perubahan perbup', 'manajemen talenta'],
        'tahun': 2024,
        'tanggal_terbit': datetime(2024, 6, 1, 11, 0),
        'status': 'berlaku',
        'deskripsi': 'Penyempurnaan mekanisme uji kompetensi dan integrasi sistem informasi manajemen talenta aparatur sipil negara.',
        'file_url': 'https://raw.githubusercontent.com/mozilla/pdf.js/ba2edeae/examples/learning/helloworld.pdf',
        'file_name': 'Perbup_33_2024_Perubahan_Mutasi.pdf',
        'ukuran_file': 980000,
        'view_count': 2100,
        'download_count': 1150,
        'created_at': datetime(2024, 6, 1, 11, 30),
        'updated_at': datetime(2024, 6, 1, 11, 30),
        'created_by': 'admin_bkd_sidoarjo',
    },
    {
        'id': 'doc-bkd-006',
        'judul': 'Penegakan Disiplin dan Kode Etik Aparatur Sipil Negara di Lingkungan Pemerintah Kabupaten Sidoarjo',
        'nomor_dokumen': 'Perbup No. 58 Tahun 2021',
        'jenis_dokumen': 'perbup',
        'kategori': 'Disiplin Pegawai & Kode Etik',
        'tags': ['disiplin', 'kode etik', 'hukuman disiplin', 'kehadiran'],
        'tahun': 2021,
        'tanggal_terbit': datetime(2021, 11, 5, 8, 0),
        'status': 'berlaku',
        'deskripsi': 'Mengatur norma perilaku, kewajiban, larangan, serta mekanisme pemeriksaan pelanggaran disiplin dan sidang majelis kode etik bagi seluruh ASN.',
        'file_url': 'https://raw.githubusercontent.com/mozilla/pdf.js/ba2edeae/examples/learning/helloworld.pdf',
        'file_name': 'Perbup_58_2021_Disiplin_Kode_Etik.pdf',
        'ukuran_file': 1760000,
        'view_count': 1630,
        'download_count': 740,
        'created_at': datetime(2021, 11, 5, 9, 0),
        'updated_at': datetime(2021, 11, 5, 9, 0),
        'created_by': 'admin_bkd_sidoarjo',
    },
    {
        'id': 'doc-bkd-007',
        'judul': 'Pemberian Tambahan Penghasilan Pegawai (TPP) Aparatur Sipil Negara Kabupaten Sidoarjo Tahun 2024',
        'nomor_dokumen': 'Perbup No. 8 Tahun 2024',
        'jenis_dokumen': 'perbup',
        'kategori': 'Kesejahteraan, Cuti & Pensiun',
        'tags': ['tpp', 'tunjangan', 'kesejahteraan', 'produktivitas'],
        'tahun': 2024,
        'tanggal_terbit': datetime(2024, 1, 15, 10, 0),
        'status': 'berlaku',
        'deskripsi': 'Pedoman kriteria perhitungan, bobot beban kerja, kondisi kerja, dan kelangkaan profesi dalam penetapan TPP ASN Sidoarjo.',
        'file_url': 'https://raw.githubusercontent.com/mozilla/pdf.js/ba2edeae/examples/learning/helloworld.pdf',
        'file_name': 'Perbup_8_2024_TPP_ASN.pdf',
        'ukuran_file': 2240000,
        'view_count': 4890,
        'download_count': 2670,
        'created_at': datetime(2024, 1, 15, 11, 0),
        'updated_at': datetime(2024, 1, 15, 11, 0),
        'created_by': 'admin_bkd_sidoarjo',
    },
    {
        'id': 'doc-bkd-008',
        'judul': 'Tata Cara Pengusulan Pensiun Pertama dan Layanan Klim Otomatis bagi PNS Purna Tugas',
        'nomor_dokumen': 'SE Kepala BKD No. 800/512/438.5.3/2023',
        'jenis_dokumen': 'se',
        'kategori': 'Kesejahteraan, Cuti & Pensiun',
        'tags': ['pensiun', 'layanan klim', 'taspen', 'purna tugas'],
        'tahun': 2023,
        'tanggal_terbit': datetime(2023, 10, 8, 9, 0),
        'status': 'berlaku',
        'deskripsi': 'Prosedur satu pintu integrasi BKD dengan PT Taspen untuk kemudahan penetapan SK Pensiun dan pembayaran hak tabungan hari tua.',
        'file_url': 'https://raw.githubusercontent.com/mozilla/pdf.js/ba2edeae/examples/learning/helloworld.pdf',
        'file_name': 'SE_Layanan_Pensiun_BKD.pdf',
        'ukuran_file': 540000,
        'view_count': 820,
        'download_count': 390,
        'created_at': datetime(2023, 10, 8, 10, 0),
        'updated_at': datetime(2023, 10, 8, 10, 0),
        'created_by': 'admin_bkd_sidoarjo',
    },
    {
        'id': 'doc-bkd-009',
        'judul': 'Pembentukan dan Susunan Perangkat Daerah Kabupaten Sidoarjo (Regulasi Lama)',
        'nomor_dokumen': 'Perda No. 8 Tahun 2016',
        'jenis_dokumen': 'perda',
        'kategori': 'Tata Kelola Kepegawaian Daerah',
        'tags': ['perda', 'kelembagaan', 'organisasi'],
        'tahun': 2016,
        'tanggal_terbit': datetime(2016, 9, 22, 14, 0),
        'status': 'dicabut',
        'deskripsi': 'Perda pembentukan susunan dinas dan badan. Dinyatakan dicabut dan digantikan oleh Perda No. 2 Tahun 2022.',
        'file_url': 'https://raw.githubusercontent.com/mozilla/pdf.js/ba2edeae/examples/learning/helloworld.pdf',
        'file_name': 'Perda_8_2016_Susunan_Perangkat_Daerah.pdf',
        'ukuran_file': 3100000,
        'view_count': 640,
        'download_count': 190,
        'created_at': datetime(2016, 9, 22, 15, 0),
        'updated_at': datetime(2022, 3, 10, 10, 0),
        'created_by': 'admin_bkd_sidoarjo',
    },
]


def _format_firestore_doc(doc_snapshot):
    """Formats Firestore document snapshot into standardized dictionary."""
    data = doc_snapshot.to_dict()
    data['id'] = doc_snapshot.id
    # Convert Firestore Timestamps to datetime
    for field in ['tanggal_terbit', 'created_at', 'updated_at']:
        val = data.get(field)
        if hasattr(val, 'to_datetime'):
            data[field] = val.to_datetime()
    return data


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
    Search, filter, and paginate documents from Firestore (or mock in dev).

    Di production: query Firestore, exception di-raise ke caller.
    Di dev lokal (mock mode): gunakan _MOCK_DOCUMENTS.

    Returns a dict with:
        items, total_items, total_pages, current_page,
        has_previous, has_next, previous_page_number, next_page_number, page_range
    """
    db = get_firestore_db()

    if db and not is_mock_mode():
        # Production: query Firestore — biarkan exception naik ke view jika gagal
        coll_ref = db.collection(COLLECTION_NAME)
        docs = coll_ref.stream()
        results = [_format_firestore_doc(doc) for doc in docs]
        logger.info(f"[get_documents] Firestore: fetched {len(results)} raw docs.")
    else:
        # Dev lokal: gunakan mock data
        logger.debug("[get_documents] Mock mode: using _MOCK_DOCUMENTS.")
        results = list(_MOCK_DOCUMENTS)

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
        results.sort(key=lambda x: x.get('view_count', 0) + x.get('download_count', 0) * 2, reverse=True)
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
    """Retrieve single document by ID from Firestore (or mock in dev)."""
    db = get_firestore_db()
    if db and not is_mock_mode():
        # Production: exception naik ke caller, tidak ada fallback mock
        doc_ref = db.collection(COLLECTION_NAME).document(doc_id)
        doc = doc_ref.get()
        if doc.exists:
            return _format_firestore_doc(doc)
        return None

    # Dev lokal: cari di mock
    for d in _MOCK_DOCUMENTS:
        if d['id'] == doc_id:
            return d
    return None


def create_document(data, user_uid="admin_bkd"):
    """
    Create a new document in Firestore (or mock in dev).
    Di production: exception naik ke caller jika Firestore gagal.
    """
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

    db = get_firestore_db()
    if db and not is_mock_mode():
        # Production: tulis ke Firestore, exception naik ke caller
        doc_ref = db.collection(COLLECTION_NAME).document(doc_id)
        doc_ref.set(doc_data)
        logger.info(f"[create_document] Firestore: created doc_id={doc_id}")
        return doc_data

    # Dev lokal: simpan ke mock in-memory
    logger.debug(f"[create_document] Mock mode: inserting doc_id={doc_id}")
    _MOCK_DOCUMENTS.insert(0, doc_data)
    return doc_data


def update_document(doc_id, data):
    """
    Update document metadata in Firestore (or mock in dev).
    Di production: exception naik ke caller jika Firestore gagal.
    """
    now = datetime.now()
    db = get_firestore_db()

    clean_data = {k: v for k, v in data.items() if k not in ['id', 'created_at', 'created_by']}
    clean_data['updated_at'] = now

    if db and not is_mock_mode():
        # Production: update Firestore, exception naik ke caller
        doc_ref = db.collection(COLLECTION_NAME).document(doc_id)
        doc_ref.update(clean_data)
        logger.info(f"[update_document] Firestore: updated doc_id={doc_id}")
        return get_document_by_id(doc_id)

    # Dev lokal: update mock in-memory
    for idx, d in enumerate(_MOCK_DOCUMENTS):
        if d['id'] == doc_id:
            _MOCK_DOCUMENTS[idx].update(clean_data)
            return _MOCK_DOCUMENTS[idx]
    return None


def delete_document(doc_id, soft=True):
    """
    Delete document. If soft=True, sets status='dihapus'. If soft=False, permanent delete.
    Di production: exception naik ke caller jika Firestore gagal.
    """
    db = get_firestore_db()
    if db and not is_mock_mode():
        # Production: mutasi Firestore, exception naik ke caller
        doc_ref = db.collection(COLLECTION_NAME).document(doc_id)
        if soft:
            doc_ref.update({'status': 'dihapus', 'updated_at': datetime.now()})
        else:
            doc_ref.delete()
        logger.info(f"[delete_document] Firestore: doc_id={doc_id} soft={soft}")
        return True

    # Dev lokal: mutasi mock in-memory
    for idx, d in enumerate(_MOCK_DOCUMENTS):
        if d['id'] == doc_id:
            if soft:
                _MOCK_DOCUMENTS[idx]['status'] = 'dihapus'
                _MOCK_DOCUMENTS[idx]['updated_at'] = datetime.now()
            else:
                _MOCK_DOCUMENTS.pop(idx)
            return True
    return False


def restore_document(doc_id):
    """Restore a soft-deleted document to 'berlaku'.
    Di production: exception naik ke caller jika Firestore gagal.
    """
    db = get_firestore_db()
    if db and not is_mock_mode():
        # Production: update Firestore, exception naik ke caller
        doc_ref = db.collection(COLLECTION_NAME).document(doc_id)
        doc_ref.update({'status': 'berlaku', 'updated_at': datetime.now()})
        logger.info(f"[restore_document] Firestore: restored doc_id={doc_id}")
        return True

    # Dev lokal: update mock in-memory
    for idx, d in enumerate(_MOCK_DOCUMENTS):
        if d['id'] == doc_id:
            _MOCK_DOCUMENTS[idx]['status'] = 'berlaku'
            _MOCK_DOCUMENTS[idx]['updated_at'] = datetime.now()
            return True
    return False


def bulk_delete_documents(doc_ids, soft=True):
    """
    Bulk delete multiple documents via WriteBatch (atomic, max 500 ops).
    Di production: exception naik ke caller jika Firestore gagal.
    """
    if not doc_ids:
        return 0

    db = get_firestore_db()
    if db and not is_mock_mode():
        # Production: WriteBatch ke Firestore, exception naik ke caller
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

    # Dev lokal: mutasi mock in-memory
    count = 0
    now = datetime.now()
    for doc_id in doc_ids:
        for idx, d in enumerate(_MOCK_DOCUMENTS):
            if d['id'] == doc_id:
                if soft:
                    _MOCK_DOCUMENTS[idx]['status'] = 'dihapus'
                    _MOCK_DOCUMENTS[idx]['updated_at'] = now
                else:
                    _MOCK_DOCUMENTS.pop(idx)
                count += 1
                break
    return count


def bulk_restore_documents(doc_ids):
    """
    Bulk restore multiple documents via WriteBatch.
    Di production: exception naik ke caller jika Firestore gagal.
    """
    if not doc_ids:
        return 0

    db = get_firestore_db()
    if db and not is_mock_mode():
        # Production: WriteBatch ke Firestore, exception naik ke caller
        batch = db.batch()
        now = datetime.now()
        for doc_id in doc_ids:
            doc_ref = db.collection(COLLECTION_NAME).document(doc_id)
            batch.update(doc_ref, {'status': 'berlaku', 'updated_at': now})
        batch.commit()
        logger.info(f"[bulk_restore_documents] Firestore: restored {len(doc_ids)} docs")
        return len(doc_ids)

    # Dev lokal: update mock in-memory
    count = 0
    now = datetime.now()
    for doc_id in doc_ids:
        for idx, d in enumerate(_MOCK_DOCUMENTS):
            if d['id'] == doc_id:
                _MOCK_DOCUMENTS[idx]['status'] = 'berlaku'
                _MOCK_DOCUMENTS[idx]['updated_at'] = now
                count += 1
                break
    return count


def increment_view_count(doc_id):
    """Increment document view count. Non-critical — silent skip on failure."""
    db = get_firestore_db()
    if db and not is_mock_mode():
        try:
            doc_ref = db.collection(COLLECTION_NAME).document(doc_id)
            doc_ref.update({'view_count': firestore.Increment(1)})
        except Exception as e:
            # Counter bukan data kritis — log warning dan lanjutkan
            logger.warning(f"[increment_view_count] Skipped for {doc_id}: {e}")
        return  # Jangan mutasi mock di production

    # Dev lokal: update mock in-memory
    for d in _MOCK_DOCUMENTS:
        if d['id'] == doc_id:
            d['view_count'] = int(d.get('view_count') or 0) + 1  # type: ignore[arg-type]
            break


def increment_download_count(doc_id):
    """Increment document download count. Non-critical — silent skip on failure."""
    db = get_firestore_db()
    if db and not is_mock_mode():
        try:
            doc_ref = db.collection(COLLECTION_NAME).document(doc_id)
            doc_ref.update({'download_count': firestore.Increment(1)})
        except Exception as e:
            # Counter bukan data kritis — log warning dan lanjutkan
            logger.warning(f"[increment_download_count] Skipped for {doc_id}: {e}")
        return  # Jangan mutasi mock di production

    # Dev lokal: update mock in-memory
    for d in _MOCK_DOCUMENTS:
        if d['id'] == doc_id:
            d['download_count'] = int(d.get('download_count') or 0) + 1  # type: ignore[arg-type]
            break


def _get_raw_dataset():
    """
    Helper untuk statistik dan get_available_years().
    - Production (Firestore connected): query Firestore, return list (bisa kosong [])
      Exception naik ke caller — TIDAK fallback ke mock.
    - Dev lokal (mock mode): return _MOCK_DOCUMENTS.
    """
    db = get_firestore_db()
    if db and not is_mock_mode():
        # Log identitas koneksi: pastikan memakai klien Firestore yang sama
        logger.info(
            f"[_get_raw_dataset] Firestore client id={id(db)} "
            f"(get_documents memakai get_firestore_db() yang sama)"
        )
        # Production: exception naik ke caller
        items = [_format_firestore_doc(doc) for doc in db.collection(COLLECTION_NAME).stream()]
        logger.info(f"[_get_raw_dataset] Firestore: {len(items)} docs fetched.")
        return items

    # Dev lokal
    logger.debug("[_get_raw_dataset] Mock mode: using _MOCK_DOCUMENTS.")
    return list(_MOCK_DOCUMENTS)


def get_statistics():
    """
    Returns general metrics for public hero and admin dashboard.

    Menghitung langsung dari Firestore (jika terhubung) atau mock data.
    Dokumen dengan status 'dihapus' (soft-deleted) TIDAK ikut terhitung.
    Field jenis_dokumen di-compare lowercase agar tidak case-sensitive.
    """
    all_docs = _get_raw_dataset()

    # ── Logging diagnostik: tampilkan data mentah SEBELUM filter ────────────────
    source = "Firestore" if (not is_mock_mode() and get_firestore_db()) else "Mock"
    sample_jenis = [d.get('jenis_dokumen') for d in all_docs[:5]]
    sample_status = [d.get('status') for d in all_docs[:5]]
    logger.info(
        f"[get_statistics] source={source} "
        f"total_raw={len(all_docs)} "
        f"sample_jenis={sample_jenis} "
        f"sample_status={sample_status}"
    )

    # Exclude soft-deleted documents (status == 'dihapus' — sesuai delete_document())
    docs = [d for d in all_docs if str(d.get('status', '')).lower() != 'dihapus']
    logger.info(
        f"[get_statistics] setelah filter dihapus: total_aktif={len(docs)} "
        f"(dikecualikan={len(all_docs) - len(docs)} dokumen dengan status='dihapus')"
    )

    total_docs = len(docs)
    total_views = sum(d.get('view_count', 0) for d in docs)
    total_downloads = sum(d.get('download_count', 0) for d in docs)

    # Hitung per jenis dokumen — lowercase comparison agar robust
    perbup_count = sum(1 for d in docs if str(d.get('jenis_dokumen', '')).lower() == 'perbup')
    sk_count = sum(1 for d in docs if str(d.get('jenis_dokumen', '')).lower() == 'sk')
    perda_count = sum(1 for d in docs if str(d.get('jenis_dokumen', '')).lower() == 'perda')
    se_count = sum(1 for d in docs if str(d.get('jenis_dokumen', '')).lower() == 'se')
    instruksi_count = sum(1 for d in docs if str(d.get('jenis_dokumen', '')).lower() == 'instruksi')
    permen_count = sum(1 for d in docs if str(d.get('jenis_dokumen', '')).lower() == 'permen')

    # Hitung per status aktif
    berlaku_count = sum(1 for d in docs if str(d.get('status', '')).lower() == 'berlaku')
    diubah_count = sum(1 for d in docs if str(d.get('status', '')).lower() == 'diubah')
    dicabut_count = sum(1 for d in docs if str(d.get('status', '')).lower() == 'dicabut')

    # Log ringkasan hasil hitung
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

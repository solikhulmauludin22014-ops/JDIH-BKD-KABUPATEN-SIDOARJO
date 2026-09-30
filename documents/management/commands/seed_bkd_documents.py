"""
Management command untuk seed data dokumen JDIH ke Firestore.
Hanya untuk keperluan development/testing.

CATATAN: _MOCK_DOCUMENTS telah dihapus dari codebase.
Command ini sekarang menggunakan data seed yang didefinisikan lokal di sini,
sehingga tidak ada dependensi ke mock data di documents/services.py.

Penggunaan:
  python manage.py seed_bkd_documents            # seed dokumen contoh
  python manage.py seed_bkd_documents --dry-run  # preview tanpa menulis
  python manage.py seed_bkd_documents --clear    # hapus semua dulu, lalu seed
"""

from datetime import datetime
from django.core.management.base import BaseCommand, CommandError
from core.firebase_config import get_firestore_db, is_mock_mode
from documents.services import COLLECTION_NAME

# Data seed lokal (hanya untuk dev, TIDAK digunakan di runtime production)
_SEED_DOCUMENTS = [
    {
        'id': 'seed-bkd-001',
        'judul': 'Pedoman Pelaksanaan Evaluasi Kinerja PNS di Lingkungan Pemerintah Kabupaten Sidoarjo',
        'nomor_dokumen': 'Perbup No. 42 Tahun 2023',
        'jenis_dokumen': 'perbup',
        'kategori': 'Manajemen Kinerja & SKP',
        'tags': ['kinerja', 'skp', 'pns', 'evaluasi'],
        'tahun': 2023,
        'tanggal_terbit': datetime(2023, 8, 15, 9, 0),
        'status': 'berlaku',
        'deskripsi': 'Peraturan mengenai tata cara penilaian kinerja PNS tahunan dan periodik.',
        'file_url': '',
        'file_name': 'Perbup_42_2023_Manajemen_Kinerja_PNS.pdf',
        'ukuran_file': 1245184,
        'appwrite_file_id': '',
        'view_count': 0,
        'download_count': 0,
        'created_at': datetime(2023, 8, 15, 10, 0),
        'updated_at': datetime(2023, 8, 15, 10, 0),
        'created_by': 'seed_command',
    },
    {
        'id': 'seed-bkd-002',
        'judul': 'Penetapan Kebutuhan PPPK di Lingkungan Pemerintah Kabupaten Sidoarjo Formasi 2024',
        'nomor_dokumen': 'Keputusan Bupati No. 188/245/438.1.1/2024',
        'jenis_dokumen': 'sk',
        'kategori': 'Kepegawaian',
        'tags': ['pppk', 'formasi', 'casn'],
        'tahun': 2024,
        'tanggal_terbit': datetime(2024, 3, 20, 8, 30),
        'status': 'berlaku',
        'deskripsi': 'Penetapan rincian kebutuhan dan alokasi formasi PPPK.',
        'file_url': '',
        'file_name': 'SK_Bupati_188_245_2024_Formasi_PPPK.pdf',
        'ukuran_file': 892416,
        'appwrite_file_id': '',
        'view_count': 0,
        'download_count': 0,
        'created_at': datetime(2024, 3, 20, 9, 15),
        'updated_at': datetime(2024, 3, 20, 9, 15),
        'created_by': 'seed_command',
    },
]


class Command(BaseCommand):
    help = 'Seed dokumen contoh BKD ke Firestore. Hanya untuk development.'

    def add_arguments(self, parser):
        parser.add_argument('--clear', action='store_true', help='Hapus semua dokumen sebelum seed.')
        parser.add_argument('--dry-run', action='store_true', dest='dry_run', help='Preview tanpa menulis ke Firestore.')

    def handle(self, *args, **options):
        if is_mock_mode():
            raise CommandError(
                'Firebase tidak aktif (Mock Mode). '
                'Pastikan credentials Firebase dikonfigurasi sebelum menjalankan seed.'
            )
        db = get_firestore_db()
        if not db:
            raise CommandError('Tidak dapat terhubung ke Firestore.')

        coll = db.collection(COLLECTION_NAME)

        if options['dry_run']:
            self.stdout.write(self.style.WARNING(f'DRY RUN - {len(_SEED_DOCUMENTS)} dokumen akan di-seed:'))
            for d in _SEED_DOCUMENTS:
                self.stdout.write(f'  {d["id"]} - {d["nomor_dokumen"]}')
            return

        if options['clear']:
            docs = list(coll.stream())
            if docs:
                b = db.batch()
                for d in docs:
                    b.delete(d.reference)
                b.commit()
                self.stdout.write(self.style.WARNING(f'{len(docs)} dokumen dihapus dari Firestore.'))

        n = 0
        for sd in _SEED_DOCUMENTS:
            p = dict(sd)
            did = str(p.pop('id', ''))
            if did:
                coll.document(did).set(p)
                n += 1
                self.stdout.write(f'  Seeded: {did} - {p.get("nomor_dokumen")}')

        self.stdout.write(self.style.SUCCESS(f'{n} dokumen seed berhasil ditulis ke Firestore.'))
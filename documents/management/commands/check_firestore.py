"""
Management command: check_firestore

Diagnosa koneksi Firestore dan tampilkan status database secara real.
Berguna untuk verifikasi setelah database baru dibuat atau setelah deploy.

Usage:
    python manage.py check_firestore
    python manage.py check_firestore --collection documents
"""

from django.core.management.base import BaseCommand
from core.firebase_config import get_firestore_db, is_mock_mode


class Command(BaseCommand):
    help = "Diagnosa koneksi Firestore: cek mode (real/mock), hitung dokumen, dan tampilkan sample field."

    def add_arguments(self, parser):
        parser.add_argument(
            '--collection',
            type=str,
            default='documents',
            help="Nama koleksi Firestore yang akan diperiksa (default: documents).",
        )

    def handle(self, *args, **options):
        collection_name = options['collection']

        self.stdout.write(self.style.MIGRATE_HEADING("\n══════════════════════════════════════════════"))
        self.stdout.write(self.style.MIGRATE_HEADING("  JDIH BKD Sidoarjo — Firestore Diagnostic"))
        self.stdout.write(self.style.MIGRATE_HEADING("══════════════════════════════════════════════\n"))

        # 1. Cek mode
        mock = is_mock_mode()
        db = get_firestore_db()

        if mock or db is None:
            self.stdout.write(self.style.ERROR("  ✗ MODE: MOCK (tidak ada koneksi Firestore nyata)"))
            self.stdout.write(self.style.WARNING(
                "\n  Pastikan satu dari berikut tersedia:\n"
                "  • FIREBASE_SERVICE_ACCOUNT_JSON di environment variable, atau\n"
                "  • serviceAccountKey.json di root proyek\n"
            ))
            return

        self.stdout.write(self.style.SUCCESS("  ✓ MODE: FIRESTORE (koneksi production aktif)\n"))

        # 2. Cek koleksi
        self.stdout.write(f"  Memeriksa koleksi: '{collection_name}'")
        try:
            docs = list(db.collection(collection_name).stream())
            total = len(docs)
            self.stdout.write(self.style.SUCCESS(f"  ✓ Total dokumen di '{collection_name}': {total}\n"))

            if total == 0:
                self.stdout.write(self.style.WARNING(
                    "  ⚠ Koleksi kosong — ini normal jika Firestore baru saja dibuat.\n"
                    "  Upload dokumen pertama via Admin Panel untuk mengisi database.\n"
                ))
            else:
                # Tampilkan sample 3 dokumen pertama
                self.stdout.write(self.style.MIGRATE_LABEL("  Sample dokumen (maks 3):"))
                for i, doc in enumerate(docs[:3]):
                    data = doc.to_dict() or {}
                    judul = str(data.get('judul', '(tanpa judul)'))[:60]
                    nomor = data.get('nomor_dokumen', '-')
                    jenis = data.get('jenis_dokumen', '-')
                    status = data.get('status', '-')
                    self.stdout.write(
                        f"  [{i + 1}] ID: {doc.id}\n"
                        f"       Judul  : {judul}\n"
                        f"       Nomor  : {nomor}\n"
                        f"       Jenis  : {jenis}  |  Status: {status}\n"
                    )

                # Ringkasan statistik
                all_data = [doc.to_dict() or {} for doc in docs]
                active = [d for d in all_data if d.get('status') != 'dihapus']
                self.stdout.write(self.style.MIGRATE_LABEL("  Ringkasan:"))
                self.stdout.write(f"  • Total raw (termasuk dihapus) : {total}")
                self.stdout.write(f"  • Aktif (status != dihapus)    : {len(active)}")

                jenis_counts: dict[str, int] = {}
                for d in active:
                    j = str(d.get('jenis_dokumen') or 'unknown')
                    jenis_counts[j] = jenis_counts.get(j, 0) + 1
                self.stdout.write("  • Per jenis dokumen:")
                for j, c in sorted(jenis_counts.items(), key=lambda x: -x[1]):
                    self.stdout.write(f"    - {j}: {c}")

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  ✗ GAGAL mengakses koleksi '{collection_name}': {e}"))
            self.stdout.write(self.style.WARNING(
                "\n  Kemungkinan penyebab:\n"
                "  • Koleksi belum pernah dibuat (akan terbuat otomatis saat dokumen pertama diupload)\n"
                "  • Firestore Security Rules belum dikonfigurasi untuk server-side access\n"
                "  • Service account tidak punya izin Firestore\n"
            ))

        self.stdout.write(self.style.MIGRATE_HEADING("\n══════════════════════════════════════════════\n"))

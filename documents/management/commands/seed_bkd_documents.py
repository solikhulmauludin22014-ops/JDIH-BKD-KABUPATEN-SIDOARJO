from django.core.management.base import BaseCommand, CommandError
from documents.services import _MOCK_DOCUMENTS, COLLECTION_NAME
from core.firebase_config import get_firestore_db, is_mock_mode


class Command(BaseCommand):
    help = 'Seed dokumen contoh BKD ke Firestore. Hanya untuk development.'

    def add_arguments(self, parser):
        parser.add_argument('--clear', action='store_true')
        parser.add_argument('--dry-run', action='store_true', dest='dry_run')

    def handle(self, *args, **options):
        if is_mock_mode():
            raise CommandError('Firebase tidak aktif (Mock Mode).')
        db = get_firestore_db()
        if not db:
            raise CommandError('Tidak dapat terhubung ke Firestore.')
        coll = db.collection(COLLECTION_NAME)
        if options['dry_run']:
            for d in _MOCK_DOCUMENTS:
                self.stdout.write('  ' + d['id'] + ' - ' + d['nomor_dokumen'])
            return
        if options['clear']:
            docs = list(coll.stream())
            if docs:
                b = db.batch()
                for d in docs: b.delete(d.reference)
                b.commit()
                self.stdout.write(self.style.WARNING(str(len(docs)) + ' dokumen dihapus.'))
        n = 0
        for sd in _MOCK_DOCUMENTS:
            p = dict(sd)
            did = str(p.pop('id', ''))
            if did:
                coll.document(did).set(p)
                n += 1
        self.stdout.write(self.style.SUCCESS(str(n) + ' dokumen ditulis.'))

"""
Views for Public JDIH BKD Sidoarjo.
Supports instant search and filter via HTMX or full page render.
"""

import logging
from django.shortcuts import render, redirect
from django.http import Http404, HttpResponseNotFound
from .services import (
    get_documents,
    get_document_by_id,
    increment_view_count,
    increment_download_count,
    get_statistics,
    get_available_years,
    DOCUMENT_TYPES,
    CATEGORIES,
    STATUS_CHOICES,
)

logger = logging.getLogger(__name__)


def _empty_stats():
    """Return zeroed stats dict — digunakan saat Firestore error."""
    return {
        'total_documents': 0, 'total_views': 0, 'total_downloads': 0,
        'perbup_count': 0, 'sk_count': 0, 'perda_count': 0,
        'se_count': 0, 'instruksi_count': 0, 'permen_count': 0,
        'berlaku_count': 0, 'diubah_count': 0, 'dicabut_count': 0,
    }


def _empty_pagination():
    """Return empty pagination dict — digunakan saat Firestore error."""
    return {
        'items': [], 'total_items': 0, 'total_pages': 1, 'current_page': 1,
        'has_previous': False, 'has_next': False,
        'previous_page_number': 0, 'next_page_number': 2, 'page_range': [1],
    }


def index_view(request):
    """
    Public Home Page.
    Handles both full page loads and HTMX partial requests.
    Jika Firestore gagal, tampilkan banner error jujur — BUKAN data palsu.
    """
    search_query = request.GET.get('q', '').strip()
    jenis = request.GET.get('jenis', '').strip()
    tahun = request.GET.get('tahun', '').strip()
    kategori = request.GET.get('kategori', '').strip()
    status = request.GET.get('status', '').strip()
    sort_by = request.GET.get('sort', 'terbaru').strip()
    page = request.GET.get('page', 1)

    try:
        page = int(page)
    except (ValueError, TypeError):
        page = 1

    firestore_error = False
    docs_data = _empty_pagination()
    stats = _empty_stats()
    available_years: list = [2026]

    try:
        docs_data = get_documents(
            search_query=search_query,
            jenis=jenis,
            tahun=tahun,
            kategori=kategori,
            status=status,
            sort_by=sort_by,
            page=page,
            page_size=9,
            include_deleted=False,
        )
        stats = get_statistics()
        available_years = get_available_years()
    except Exception as e:
        logger.exception(f"[index_view] Gagal fetch data dari Firestore: {e}")
        firestore_error = True

    context = {
        'documents': docs_data['items'],
        'pagination': docs_data,
        'search_query': search_query,
        'selected_jenis': jenis,
        'selected_tahun': tahun,
        'selected_kategori': kategori,
        'selected_status': status,
        'selected_sort': sort_by,
        'document_types': DOCUMENT_TYPES,
        'categories': CATEGORIES,
        'statuses': STATUS_CHOICES,
        'available_years': available_years,
        'stats': stats,
        'firestore_error': firestore_error,
    }

    # If requested via HTMX, return only the document list and pagination partial
    if request.headers.get('HX-Request') or request.GET.get('partial') == '1':
        return render(request, 'documents/partials/document_list.html', context)

    return render(request, 'documents/index.html', context)


def detail_view(request, doc_id):
    """
    Detailed document view with embedded PDF viewer, metadata, and view counter.
    """
    try:
        document = get_document_by_id(doc_id)
    except Exception as e:
        logger.exception(f"[detail_view] Gagal fetch dokumen {doc_id} dari Firestore: {e}")
        raise Http404("Dokumen hukum tidak ditemukan.")

    if not document or document.get('status') == 'dihapus':
        raise Http404("Dokumen hukum tidak ditemukan.")

    # Increment view counter (non-critical)
    increment_view_count(doc_id)
    document['view_count'] = document.get('view_count', 0) + 1

    # Fetch related documents from same category
    try:
        related = get_documents(
            kategori=document.get('kategori'),
            page=1,
            page_size=4,
            include_deleted=False,
        )
        related_items = [d for d in related['items'] if d['id'] != doc_id][:3]
    except Exception:
        related_items = []

    context = {
        'document': document,
        'related_documents': related_items,
        'document_types_dict': dict(DOCUMENT_TYPES),
    }
    return render(request, 'documents/detail.html', context)


def download_view(request, doc_id):
    """
    Handle document download action and increment download counter.
    Menampilkan pesan ramah jika file tidak tersedia, bukan error mentah.
    """
    try:
        document = get_document_by_id(doc_id)
    except Exception as e:
        logger.exception(f"[download_view] Gagal fetch dokumen {doc_id}: {e}")
        document = None

    if not document or document.get('status') == 'dihapus':
        return HttpResponseNotFound(
            '<html><body style="font-family:sans-serif;padding:2rem;text-align:center;">'
            '<h2 style="color:#dc2626;">Dokumen Tidak Ditemukan</h2>'
            '<p style="color:#64748b;">Dokumen yang Anda cari tidak tersedia atau telah dihapus.</p>'
            '<a href="/" style="color:#2563eb;">&#8592; Kembali ke Beranda</a>'
            '</body></html>'
        )

    file_url = document.get('file_url', '').strip()
    if not file_url:
        return redirect('documents:detail', doc_id=doc_id)

    # Increment counter hanya jika file tersedia
    increment_download_count(doc_id)
    return redirect(file_url)

"""
Views for Public JDIH BKD Sidoarjo.
Supports instant search and filter via HTMX or full page render.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, Http404
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


def index_view(request):
    """
    Public Home Page.
    Handles both full page loads and HTMX partial requests.
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
        'available_years': get_available_years(),
        'stats': get_statistics(),
    }

    # If requested via HTMX, return only the document list and pagination partial
    if request.headers.get('HX-Request') or request.GET.get('partial') == '1':
        return render(request, 'documents/partials/document_list.html', context)

    return render(request, 'documents/index.html', context)


def detail_view(request, doc_id):
    """
    Detailed document view with embedded PDF viewer, metadata, and view counter.
    """
    document = get_document_by_id(doc_id)
    if not document or document.get('status') == 'dihapus':
        raise Http404("Dokumen hukum tidak ditemukan.")

    # Increment view counter
    increment_view_count(doc_id)
    # Refresh local count
    document['view_count'] = document.get('view_count', 0) + 1

    # Fetch related documents from same category or jenis
    related = get_documents(
        kategori=document.get('kategori'),
        page=1,
        page_size=4,
        include_deleted=False,
    )
    related_items = [d for d in related['items'] if d['id'] != doc_id][:3]

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
    document = get_document_by_id(doc_id)
    if not document or document.get('status') == 'dihapus':
        from django.http import HttpResponseNotFound
        return HttpResponseNotFound(
            '<html><body style="font-family:sans-serif;padding:2rem;text-align:center;">'
            '<h2 style="color:#dc2626;">Dokumen Tidak Ditemukan</h2>'
            '<p style="color:#64748b;">Dokumen yang Anda cari tidak tersedia atau telah dihapus.</p>'
            '<a href="/" style="color:#2563eb;">&#8592; Kembali ke Beranda</a>'
            '</body></html>'
        )

    file_url = document.get('file_url', '').strip()
    if not file_url:
        # File belum diunggah — arahkan kembali ke halaman detail dengan pesan
        from django.contrib import messages as django_messages
        return redirect('documents:detail', doc_id=doc_id)

    # Increment counter hanya jika file tersedia
    increment_download_count(doc_id)
    return redirect(file_url)

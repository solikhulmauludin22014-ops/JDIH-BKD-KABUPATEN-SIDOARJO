"""
Views for Admin Panel JDIH BKD Sidoarjo.
Handles Firebase Auth verification, Django signed-cookie sessions,
and full CRUD with Firebase Firestore & Storage.
"""

import json
from datetime import datetime
from django.shortcuts import render, redirect
from django.urls import reverse
from django.http import JsonResponse, Http404
from django.contrib import messages
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_POST

from core.decorators import admin_login_required
from core.firebase_config import verify_firebase_id_token, is_mock_mode
from core.storage_service import upload_pdf_to_storage, delete_pdf_from_storage
from documents.services import (
    get_documents,
    get_document_by_id,
    create_document,
    update_document,
    delete_document,
    restore_document,
    get_statistics,
    get_available_years,
    DOCUMENT_TYPES,
    CATEGORIES,
    STATUS_CHOICES,
)
from .forms import DocumentForm


def login_view(request):
    """
    Admin Login Page.
    Interacts with Firebase Auth on client side and validates ID token on server side.
    """
    if request.session.get('admin_user'):
        return redirect('admin_panel:dashboard')

    next_url = request.GET.get('next', reverse('admin_panel:dashboard'))

    # Handle standard POST (fallback or demo mode)
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '').strip()
        id_token = request.POST.get('id_token', '').strip()

        # If ID token provided from Firebase Web SDK
        if id_token:
            decoded = verify_firebase_id_token(id_token)
            if decoded:
                request.session['admin_user'] = {
                    'uid': decoded.get('uid'),
                    'email': decoded.get('email', email),
                    'name': decoded.get('name', 'Admin BKD Sidoarjo'),
                }
                messages.success(request, f"Selamat datang kembali, {request.session['admin_user']['name']}!")
                return redirect(next_url)
            else:
                messages.error(request, "Verifikasi token Firebase gagal. Silakan coba lagi.")

        # Fallback / Demo login verification
        elif email and password:
            if is_mock_mode() or (email == 'admin@bkd.sidoarjokab.go.id' and password == 'admin123'):
                request.session['admin_user'] = {
                    'uid': f'admin_uid_{email.replace("@", "_")}',
                    'email': email,
                    'name': 'Admin BKD Sidoarjo',
                }
                messages.success(request, f"Login berhasil sebagai {email} (Mode Sesi Terverifikasi).")
                return redirect(next_url)
            else:
                messages.error(request, "Email atau kata sandi tidak sesuai.")
        else:
            messages.error(request, "Harap lengkapi email dan kata sandi.")

    context = {
        'next_url': next_url,
        'is_mock': is_mock_mode(),
    }
    return render(request, 'admin_panel/login.html', context)


@require_POST
def session_login_api(request):
    """
    API endpoint to exchange client-side Firebase ID Token for Django Signed Cookie Session.
    """
    try:
        data = json.loads(request.body)
        id_token = data.get('id_token')
        email = data.get('email', '')

        if not id_token:
            return JsonResponse({'status': 'error', 'message': 'Token tidak disediakan.'}, status=400)

        decoded = verify_firebase_id_token(id_token)
        if decoded:
            request.session['admin_user'] = {
                'uid': decoded.get('uid'),
                'email': decoded.get('email', email),
                'name': decoded.get('name', 'Admin BKD Sidoarjo'),
            }
            return JsonResponse({'status': 'ok', 'redirect': reverse('admin_panel:dashboard')})
        else:
            return JsonResponse({'status': 'error', 'message': 'Token Firebase tidak valid.'}, status=401)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


def logout_view(request):
    """Log out admin user and flush session."""
    request.session.flush()
    messages.info(request, "Anda telah keluar dari Panel Admin BKD.")
    return redirect('admin_panel:login')


@admin_login_required
def dashboard_view(request):
    """
    Admin Dashboard listing all documents with filters, quick stats, and actions.
    """
    search_query = request.GET.get('q', '').strip()
    jenis = request.GET.get('jenis', '').strip()
    tahun = request.GET.get('tahun', '').strip()
    status = request.GET.get('status', '').strip()
    sort_by = request.GET.get('sort', 'terbaru').strip()
    tab = request.GET.get('tab', 'aktif')
    page = request.GET.get('page', 1)

    try:
        page = int(page)
    except (ValueError, TypeError):
        page = 1

    include_deleted = 'only' if tab == 'sampah' else (True if tab == 'semua' else False)

    docs_data = get_documents(
        search_query=search_query,
        jenis=jenis,
        tahun=tahun,
        status=status if status != 'semua' else None,
        sort_by=sort_by,
        page=page,
        page_size=15,
        include_deleted=include_deleted,
    )

    stats = get_statistics()

    context = {
        'documents': docs_data['items'],
        'pagination': docs_data,
        'search_query': search_query,
        'selected_jenis': jenis,
        'selected_tahun': tahun,
        'selected_status': status,
        'selected_sort': sort_by,
        'current_tab': tab,
        'document_types': DOCUMENT_TYPES,
        'available_years': get_available_years(),
        'statuses': STATUS_CHOICES,
        'stats': stats,
    }
    return render(request, 'admin_panel/dashboard.html', context)


@admin_login_required
def document_create_view(request):
    """
    Create a new legal document.
    Uploads PDF file to Firebase Storage and saves metadata in Firestore.
    """
    if request.method == 'POST':
        form = DocumentForm(request.POST, request.FILES, is_edit=False)
        if form.is_valid():
            uploaded_file = form.cleaned_data['file_dokumen']
            try:
                # 1. Upload to Firebase Storage
                storage_result = upload_pdf_to_storage(uploaded_file)

                # 2. Parse tags
                raw_tags = form.cleaned_data.get('tags', '')
                tags_list = [t.strip() for t in raw_tags.split(',') if t.strip()]

                # 3. Prepare document data for Firestore
                doc_payload = {
                    'judul': form.cleaned_data['judul'],
                    'nomor_dokumen': form.cleaned_data['nomor_dokumen'],
                    'jenis_dokumen': form.cleaned_data['jenis_dokumen'],
                    'kategori': form.cleaned_data['kategori'],
                    'tahun': form.cleaned_data['tahun'],
                    'tanggal_terbit': datetime.combine(
                        form.cleaned_data['tanggal_terbit'],
                        datetime.min.time()
                    ),
                    'status': form.cleaned_data['status'],
                    'deskripsi': form.cleaned_data['deskripsi'],
                    'tags': tags_list,
                    'file_url': storage_result['file_url'],
                    'file_name': storage_result['file_name'],
                    'ukuran_file': storage_result['ukuran_file'],
                }

                admin_uid = request.session.get('admin_user', {}).get('uid', 'admin_bkd')
                new_doc = create_document(doc_payload, user_uid=admin_uid)

                messages.success(request, f"Dokumen '{new_doc['nomor_dokumen']}' berhasil ditambahkan ke katalog JDIH!")
                return redirect('admin_panel:dashboard')

            except Exception as e:
                messages.error(request, f"Terjadi kesalahan saat memproses dokumen: {str(e)}")
    else:
        initial_data = {
            'tahun': datetime.now().year,
            'tanggal_terbit': datetime.now().strftime('%Y-%m-%d'),
            'status': 'berlaku',
        }
        form = DocumentForm(initial=initial_data, is_edit=False)

    context = {
        'form': form,
        'is_edit': False,
        'title': 'Tambah Dokumen Hukum Baru',
    }
    return render(request, 'admin_panel/document_form.html', context)


@admin_login_required
def document_edit_view(request, doc_id):
    """
    Edit existing legal document metadata and optionally replace PDF file.
    """
    document = get_document_by_id(doc_id)
    if not document:
        raise Http404("Dokumen tidak ditemukan.")

    if request.method == 'POST':
        form = DocumentForm(request.POST, request.FILES, is_edit=True)
        if form.is_valid():
            try:
                raw_tags = form.cleaned_data.get('tags', '')
                tags_list = [t.strip() for t in raw_tags.split(',') if t.strip()]

                update_payload = {
                    'judul': form.cleaned_data['judul'],
                    'nomor_dokumen': form.cleaned_data['nomor_dokumen'],
                    'jenis_dokumen': form.cleaned_data['jenis_dokumen'],
                    'kategori': form.cleaned_data['kategori'],
                    'tahun': form.cleaned_data['tahun'],
                    'tanggal_terbit': datetime.combine(
                        form.cleaned_data['tanggal_terbit'],
                        datetime.min.time()
                    ),
                    'status': form.cleaned_data['status'],
                    'deskripsi': form.cleaned_data['deskripsi'],
                    'tags': tags_list,
                }

                # If new file uploaded, upload to storage
                new_file = form.cleaned_data.get('file_dokumen')
                if new_file:
                    storage_result = upload_pdf_to_storage(new_file)
                    update_payload['file_url'] = storage_result['file_url']
                    update_payload['file_name'] = storage_result['file_name']
                    update_payload['ukuran_file'] = storage_result['ukuran_file']

                update_document(doc_id, update_payload)
                messages.success(request, f"Dokumen '{form.cleaned_data['nomor_dokumen']}' berhasil diperbarui.")
                return redirect('admin_panel:dashboard')

            except Exception as e:
                messages.error(request, f"Gagal memperbarui dokumen: {str(e)}")
    else:
        # Prepopulate form
        tanggal_terbit_val = document.get('tanggal_terbit')
        if hasattr(tanggal_terbit_val, 'strftime'):
            tanggal_str = tanggal_terbit_val.strftime('%Y-%m-%d')
        else:
            tanggal_str = str(tanggal_terbit_val)[:10]

        initial_data = {
            'judul': document.get('judul'),
            'nomor_dokumen': document.get('nomor_dokumen'),
            'jenis_dokumen': document.get('jenis_dokumen'),
            'kategori': document.get('kategori'),
            'tahun': document.get('tahun'),
            'tanggal_terbit': tanggal_str,
            'status': document.get('status'),
            'deskripsi': document.get('deskripsi'),
            'tags': ", ".join(document.get('tags', [])),
        }
        form = DocumentForm(initial=initial_data, is_edit=True)

    context = {
        'form': form,
        'document': document,
        'is_edit': True,
        'title': f"Edit Dokumen: {document.get('nomor_dokumen')}",
    }
    return render(request, 'admin_panel/document_form.html', context)


@admin_login_required
@require_POST
def document_delete_view(request, doc_id):
    """
    Delete document. Default is soft delete (status = 'dihapus').
    If permanent=1, deletes record permanently.
    """
    permanent = request.POST.get('permanent') == '1'
    doc = get_document_by_id(doc_id)
    if not doc:
        raise Http404("Dokumen tidak ditemukan.")

    success = delete_document(doc_id, soft=not permanent)
    if success:
        if permanent:
            messages.success(request, f"Dokumen '{doc.get('nomor_dokumen')}' telah dihapus secara permanen.")
        else:
            messages.success(request, f"Dokumen '{doc.get('nomor_dokumen')}' dipindahkan ke kotak sampah (soft delete).")
    else:
        messages.error(request, "Gagal menghapus dokumen.")

    tab = 'sampah' if permanent else 'aktif'
    return redirect(f"{reverse('admin_panel:dashboard')}?tab={tab}")


@admin_login_required
@require_POST
def document_restore_view(request, doc_id):
    """
    Restore a soft-deleted document.
    """
    doc = get_document_by_id(doc_id)
    if not doc:
        raise Http404("Dokumen tidak ditemukan.")

    success = restore_document(doc_id)
    if success:
        messages.success(request, f"Dokumen '{doc.get('nomor_dokumen')}' berhasil dipulihkan ke status Berlaku.")
    else:
        messages.error(request, "Gagal memulihkan dokumen.")

    return redirect(f"{reverse('admin_panel:dashboard')}?tab=aktif")

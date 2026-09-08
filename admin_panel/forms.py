"""
Forms for Admin Panel CRUD operations.
Pure Django Forms validating metadata and PDF file upload constraints.
"""

from django import forms
from documents.services import DOCUMENT_TYPES, CATEGORIES, STATUS_CHOICES
from core.storage_service import validate_pdf_file


class DocumentForm(forms.Form):
    judul = forms.CharField(
        label="Judul Dokumen",
        max_length=500,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'w-full rounded-xl border-slate-200 shadow-sm focus:border-blue-600 focus:ring-blue-600 text-sm py-2.5 px-3.5',
            'placeholder': 'Contoh: Pedoman Manajemen Kinerja Pegawai Negeri Sipil...'
        })
    )

    nomor_dokumen = forms.CharField(
        label="Nomor Dokumen / Regulasi",
        max_length=200,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'w-full rounded-xl border-slate-200 shadow-sm focus:border-blue-600 focus:ring-blue-600 text-sm py-2.5 px-3.5',
            'placeholder': 'Contoh: Perbup No. 42 Tahun 2023 atau 188/245/438.1.1/2024'
        })
    )

    jenis_dokumen = forms.ChoiceField(
        label="Jenis Dokumen",
        choices=DOCUMENT_TYPES,
        required=True,
        widget=forms.Select(attrs={
            'class': 'w-full rounded-xl border-slate-200 shadow-sm focus:border-blue-600 focus:ring-blue-600 text-sm py-2.5 px-3.5'
        })
    )

    kategori = forms.ChoiceField(
        label="Kategori / Topik Kepegawaian",
        choices=[(c, c) for c in CATEGORIES],
        required=True,
        widget=forms.Select(attrs={
            'class': 'w-full rounded-xl border-slate-200 shadow-sm focus:border-blue-600 focus:ring-blue-600 text-sm py-2.5 px-3.5'
        })
    )

    tahun = forms.IntegerField(
        label="Tahun Terbit",
        min_value=1945,
        max_value=2100,
        required=True,
        widget=forms.NumberInput(attrs={
            'class': 'w-full rounded-xl border-slate-200 shadow-sm focus:border-blue-600 focus:ring-blue-600 text-sm py-2.5 px-3.5',
            'placeholder': '2024'
        })
    )

    tanggal_terbit = forms.DateField(
        label="Tanggal Terbit / Penetapan",
        required=True,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'w-full rounded-xl border-slate-200 shadow-sm focus:border-blue-600 focus:ring-blue-600 text-sm py-2.5 px-3.5'
        })
    )

    status = forms.ChoiceField(
        label="Status Dokumen",
        choices=STATUS_CHOICES,
        initial='berlaku',
        required=True,
        widget=forms.Select(attrs={
            'class': 'w-full rounded-xl border-slate-200 shadow-sm focus:border-blue-600 focus:ring-blue-600 text-sm py-2.5 px-3.5'
        })
    )

    tags = forms.CharField(
        label="Kata Kunci / Tags",
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'w-full rounded-xl border-slate-200 shadow-sm focus:border-blue-600 focus:ring-blue-600 text-sm py-2.5 px-3.5',
            'placeholder': 'kinerja, pns, skp, evaluasi, bkd (pisahkan dengan koma)'
        })
    )

    deskripsi = forms.CharField(
        label="Ringkasan / Abstraksi Dokumen",
        required=True,
        widget=forms.Textarea(attrs={
            'rows': 4,
            'class': 'w-full rounded-xl border-slate-200 shadow-sm focus:border-blue-600 focus:ring-blue-600 text-sm py-2.5 px-3.5',
            'placeholder': 'Uraian singkat mengenai latar belakang, tujuan, atau pokok-pokok isi regulasi hukum kepegawaian ini...'
        })
    )

    file_dokumen = forms.FileField(
        label="File Dokumen PDF",
        required=False,
        widget=forms.FileInput(attrs={
            'accept': 'application/pdf,.pdf',
            'class': 'block w-full text-sm text-slate-500 file:mr-4 file:py-2.5 file:px-4 file:rounded-xl file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100'
        })
    )

    def __init__(self, *args, is_edit=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.is_edit = is_edit
        if not is_edit:
            self.fields['file_dokumen'].required = True

    def clean_file_dokumen(self):
        file = self.cleaned_data.get('file_dokumen')
        if not file and not self.is_edit:
            raise forms.ValidationError("File dokumen PDF wajib diunggah.")
        if file:
            is_valid, err = validate_pdf_file(file)
            if not is_valid:
                raise forms.ValidationError(err)
        return file

# PROMPT: Website JDIH — Badan Kepegawaian Daerah (BKD) Kabupaten Sidoarjo

## Konteks Proyek
Buatkan website **JDIH (Jaringan Dokumentasi dan Informasi Hukum)** untuk BKD Kabupaten Sidoarjo. Website ini terdiri dari dua bagian utama:

1. **Beranda publik (interaktif)** — pengunjung dapat mencari, melihat detail, dan mendownload dokumen hukum tanpa perlu login.
2. **Panel admin (login only)** — admin BKD dapat mengupload, mengedit, dan menghapus dokumen.

Referensi pola desain dan struktur kategori: **JDIH BKN** (jdih.bkn.go.id) dan menu "Regulasi > JDIH BKN" pada bkn.go.id.

---

## Tech Stack (WAJIB DIIKUTI)

| Komponen | Pilihan |
|---|---|
| Backend framework | **Django (Python)** |
| Styling | **Tailwind CSS** |
| Interaktivitas (search/filter tanpa reload) | **HTMX** atau **Alpine.js** (pilih salah satu, ringan) |
| Database dokumen | **Firebase Firestore** (NoSQL) |
| Penyimpanan file | **Firebase Storage** |
| Autentikasi admin | **Firebase Authentication** (Email & Password) |
| SDK server-side | **firebase-admin (Python)** |

### Catatan arsitektur penting
- **Jangan gunakan `django.contrib.admin` bawaan** untuk CRUD dokumen — itu berbasis Django ORM/model relasional, sedangkan data dokumen disimpan di Firestore (NoSQL). Buat halaman admin custom (views + template Django sendiri).
- **Jangan gunakan sistem auth bawaan Django** (`django.contrib.auth`) sebagai sumber utama login admin. Gunakan **Firebase Authentication**: Django hanya memverifikasi ID token dari Firebase lewat `firebase-admin`, lalu menyimpan status login di Django session.
- Django tetap boleh memakai SQLite lokal HANYA untuk kebutuhan internal framework (session, csrf), bukan untuk menyimpan data dokumen atau akun admin.
- Simpan kredensial Firebase (service account JSON) di environment variable / `.env`, jangan pernah di-hardcode atau ikut ter-commit ke git.

---

## 1. Beranda Publik (Tanpa Login)

### Fitur pencarian & filter
- Search bar untuk mencari berdasarkan judul atau nomor dokumen
- Filter: jenis dokumen (contoh: Peraturan Bupati, SK, Perda, dll — sesuaikan dengan kebutuhan BKD kepegawaian), tahun terbit, kategori/topik, status (berlaku/dicabut/diubah)
- Hasil pencarian tampil sebagai list/card, update otomatis saat filter berubah (pakai HTMX/Alpine, tanpa reload penuh)
- Pagination pada daftar hasil

### Halaman detail dokumen
- Menampilkan seluruh metadata dokumen
- Preview PDF langsung di halaman (embed viewer)
- Tombol download file asli
- (Opsional) penghitung jumlah dilihat & jumlah didownload

### Desain
- Responsive, mobile-friendly
- Tailwind CSS, tone formal/institusional (sesuai identitas instansi pemerintah)

---

## 2. Panel Admin (Login Required)

### Login
- Form login email & password → diverifikasi lewat Firebase Authentication
- Redirect ke dashboard jika berhasil; halaman admin lain diproteksi middleware/decorator (tidak bisa diakses tanpa login)

### Dashboard admin
- Tabel daftar seluruh dokumen: kolom judul, nomor, jenis, tahun, status, aksi (edit/hapus)
- Fitur search & sort pada tabel
- Tombol "Tambah Dokumen Baru"

### Tambah / Edit dokumen
- Form metadata: judul, nomor dokumen, jenis dokumen, kategori, tahun, tanggal terbit, status, ringkasan/deskripsi, tag
- Upload file PDF → disimpan ke Firebase Storage, URL hasil upload disimpan ke field Firestore
- Validasi: hanya file PDF, batas ukuran maksimum (tentukan misal 10MB)

### Hapus dokumen
- Konfirmasi sebelum hapus
- (Opsional) soft delete — tandai status `dihapus` alih-alih hapus permanen, agar bisa dipulihkan

---

## 3. Struktur Data Firestore

Koleksi: `documents`

```
{
  id: string (auto-generated),
  judul: string,
  nomor_dokumen: string,
  jenis_dokumen: string,       // enum: perbup, sk, perda, dst
  kategori: string,
  tags: array<string>,
  tahun: number,
  tanggal_terbit: timestamp,
  status: string,               // "berlaku" | "dicabut" | "diubah"
  deskripsi: string,
  file_url: string,             // dari Firebase Storage
  file_name: string,
  ukuran_file: number,
  view_count: number,
  download_count: number,
  created_at: timestamp,
  updated_at: timestamp,
  created_by: string            // uid admin dari Firebase Auth
}
```

---

## 4. Deliverable yang Diminta dari AI Coding Agent

1. Struktur project Django lengkap (apps, urls, views, templates)
2. Implementasi seluruh fitur beranda publik & panel admin di atas
3. Modul integrasi Firebase (Firestore, Storage, Authentication) menggunakan `firebase-admin`
4. Middleware/decorator proteksi halaman admin
5. File `.env.example` berisi daftar environment variable yang dibutuhkan (tanpa nilai asli)
6. Dokumentasi singkat (`README.md`): cara setup project Firebase, cara menjalankan project secara lokal, dan struktur folder

---

## 5. Target Deployment: Vercel

Project ini akan di-deploy ke **Vercel** (dukungan Django zero-configuration: Vercel mendeteksi `manage.py` dan menjalankan WSGI/ASGI sebagai Vercel Functions). Sesuaikan konfigurasi berikut sejak awal:

- **Session engine WAJIB `django.contrib.sessions.backends.signed_cookies`** (bukan default DB-backed session), karena Django berjalan sebagai serverless function tanpa disk/DB relasional persisten antar-invocation.
- Set `ALLOWED_HOSTS` agar mencakup domain `.vercel.app` dan domain custom instansi.
- Semua kredensial (Firebase service account JSON, secret key Django, dsb.) dibaca dari **Environment Variables Vercel**, bukan file lokal yang ikut di-deploy.
- Jangan mengandalkan penyimpanan file lokal (disk) untuk apa pun — seluruh file dokumen sudah didesain lewat Firebase Storage, jadi ini sudah sesuai.
- Sertakan `vercel.json` (jika diperlukan) dan pastikan struktur project kompatibel dengan Python runtime Vercel (`manage.py` di root atau path yang terdeteksi otomatis).
- Jika ke depan dibutuhkan tugas terjadwal (misal reminder dokumen kedaluwarsa), gunakan **Vercel Cron Jobs**, bukan cron job sistem biasa.

---

## Batasan
- Fokus hanya pada dua bagian ini: beranda publik interaktif + panel admin CRUD. Jangan menambahkan fitur di luar scope (misal: modul kepegawaian lain di luar JDIH) kecuali diminta.
- Gunakan bahasa Indonesia untuk seluruh teks antarmuka (label, tombol, pesan error).

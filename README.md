# Website JDIH — Badan Kepegawaian Daerah (BKD) Kabupaten Sidoarjo

Portal resmi **Jaringan Dokumentasi dan Informasi Hukum (JDIH)** Badan Kepegawaian Daerah Pemerintah Kabupaten Sidoarjo. Mengadopsi standar arsitektur dan pola navigasi modern serupa JDIH BKN (`jdih.bkn.go.id`).

Website ini dirancang menggunakan **Django (Python)**, **Tailwind CSS**, **HTMX & Alpine.js**, **Firebase Firestore** (NoSQL Database), **Firebase Storage** (Penyimpanan Dokumen PDF), dan **Firebase Authentication** (Autentikasi Admin), serta telah dioptimasi untuk deployment serverless ke **Vercel** (`signed_cookies` session).

---

## Fitur Utama

### 1. Beranda Publik (Tanpa Perlu Login)
- **Pencarian Live Real-Time (HTMX)**: Pengunjung dapat mengetik judul atau nomor dokumen dengan respon instan tanpa *full page reload*.
- **Filter Multi-Kriteria**:
  - Jenis Dokumen (Peraturan Bupati, Keputusan Bupati/SK, Perda, Surat Edaran, dll)
  - Tahun Terbit
  - Kategori Kepegawaian (Manajemen Kinerja & SKP, PPPK & CPNS, Mutasi & Promosi, Kesejahteraan ASN, Disiplin Pegawai)
  - Status Regulasi (Berlaku, Diubah, Dicabut)
- **Pagination Dinamis**: Navigasi halaman cepat tanpa reload.
- **Halaman Detail Dokumen**:
  - Metadata lengkap dan status keberlakuan hukum.
  - **Embedded PDF Viewer** responsif langsung di peramban dengan mode layar penuh (*fullscreen*).
  - Penghitung otomatis statistik jumlah dilihat (*views*) dan diunduh (*downloads*).
  - Tautan regulasi terkait.

### 2. Panel Admin Pengelola BKD (Login Required)
- **Autentikasi Firebase**: Verifikasi ID token Firebase di sisi server menggunakan `firebase-admin`, disimpan secara aman di sesi Django (`signed_cookies`).
- **Dashboard Statistik**: Metrik total dokumen, dokumen aktif berlaku, total views, dan total downloads.
- **Manajemen CRUD Dokumen**:
  - Form input metadata terstruktur.
  - Upload file PDF langsung ke Firebase Storage dengan validasi tipe file (.pdf) dan batas ukuran maksimal 10MB.
- **Fitur Soft Delete & Pulihkan (Restore)**: Mencegah dokumen terhapus secara tidak sengaja melalui tab Kotak Sampah, serta opsi hapus permanen jika diperlukan.
- **Mode Demo Otomatis**: Jika kredensial Firebase belum dimasukkan, website otomatis berjalan dalam mode *mock provider* dengan data regulasi kepegawaian realistis Kabupaten Sidoarjo, sehingga langsung siap diuji tanpa setup awal.

---

## Struktur Folder Proyek

```
JDIH BKD Sidoarjo/
│
├── manage.py                     # Entrypoint CLI Django
├── vercel.json                   # Konfigurasi routing Vercel Serverless Function
├── requirements.txt              # Daftar dependensi Python
├── .env.example                  # Template konfigurasi environment variables
├── .gitignore                    # Berkas pengecualian Git
├── README.md                     # Dokumentasi panduan lengkap
│
├── jdih_sidoarjo/                # Konfigurasi inti proyek Django
│   ├── __init__.py
│   ├── settings.py               # Pengaturan signed cookies, ALLOWED_HOSTS, Whitenoise
│   ├── urls.py                   # Routing utama publik & admin panel
│   ├── wsgi.py                   # Entrypoint WSGI Vercel / server
│   └── asgi.py
│
├── core/                         # Integrasi Firebase & Layanan Inti
│   ├── firebase_config.py        # Inisialisasi Firebase Admin SDK & token verifier
│   ├── decorators.py             # Decorator proteksi @admin_login_required
│   ├── storage_service.py        # Upload & hapus berkas PDF Firebase Storage
│   └── context_processors.py     # Data instansi & kredensial web Firebase ke template
│
├── documents/                    # Aplikasi Portal Publik
│   ├── services.py               # Layer kueri Firestore, filter, counter, & seed data
│   ├── views.py                  # View beranda publik, HTMX search partial, & detail
│   └── urls.py                   # Rute URL publik
│
├── admin_panel/                  # Aplikasi Panel Admin
│   ├── forms.py                  # Validasi form dokumen & batas file PDF
│   ├── views.py                  # View login, dashboard, create, edit, delete, restore
│   └── urls.py                   # Rute URL panel admin
│
├── templates/                    # Template HTML Django
│   ├── base.html                 # Layout publik (Navbar, Footer BKD Sidoarjo)
│   ├── admin_base.html           # Layout panel admin (Sidebar & Topbar)
│   ├── documents/
│   │   ├── index.html            # Beranda dengan Hero & Filter
│   │   ├── detail.html           # Detail dokumen + PDF Embed Viewer
│   │   └── partials/
│   │       ├── document_card.html# Komponen kartu dokumen
│   │       └── document_list.html# Partial HTMX swap untuk hasil pencarian
│   └── admin_panel/
│       ├── login.html            # Form login pengelola (Firebase Auth)
│       ├── dashboard.html        # Tabel manajemen dokumen & statistik
│       └── document_form.html    # Form tambah / edit dokumen
│
└── static/                       # Aset statis
    └── css/
        └── custom.css            # Styling kustom & animasi transisi HTMX
```

---

## Panduan Menjalankan Proyek Secara Lokal

### 1. Prasyarat
- Python 3.10 ke atas
- Pip

### 2. Kloning dan Buat Virtual Environment
```bash
# Masuk ke folder proyek
cd "JDIH BKD Sidoarjo"

# Buat virtual environment
python -m venv .venv

# Aktifkan virtual environment
# Pada Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# Pada Linux / macOS:
# source .venv/bin/activate
```

### 3. Instalasi Dependensi
```bash
pip install -r requirements.txt
```

### 4. Salin Konfigurasi Environment
Salin berkas `.env.example` menjadi `.env`:
```bash
cp .env.example .env
```
*(Catatan: Anda dapat langsung menjalankan proyek tanpa mengisi kredensial Firebase; sistem akan otomatis aktif dalam mode demo interaktif).*

### 5. Jalankan Server Pengembangan
```bash
python manage.py runserver
```
Buka peramban di `http://127.0.0.1:8000/`:
- **Beranda Publik**: `http://127.0.0.1:8000/`
- **Panel Admin**: `http://127.0.0.1:8000/admin-panel/login/`
  - Kredensial Demo:
    - **Email**: `admin@bkd.sidoarjokab.go.id`
    - **Password**: `admin123`

---

## Panduan Setup Firebase

Untuk menghubungkan website ke basis data Firestore dan penyimpanan berkas Firebase Storage produksi milik BKD:

1. **Buat Proyek di Firebase Console**:
   - Buka [Firebase Console](https://console.firebase.google.com/) dan buat proyek baru (misal: `jdih-bkd-sidoarjo`).
2. **Aktifkan Firestore Database**:
   - Masuk ke menu **Build > Firestore Database** dan klik **Create Database**.
   - Pilih lokasi server terdekat (contoh: `asia-southeast2` Jakarta).
   - Buat koleksi dengan nama `documents`.
3. **Aktifkan Firebase Storage**:
   - Masuk ke menu **Build > Storage** dan klik **Get Started**.
   - Atur rules agar dokumen publik dapat dibaca dan hanya admin yang dapat mengunggah.
4. **Aktifkan Firebase Authentication**:
   - Masuk ke menu **Build > Authentication > Sign-in method**.
   - Aktifkan penyedia **Email/Password**.
   - Di tab **Users**, buat akun pengelola BKD (contoh: `admin@bkd.sidoarjokab.go.id`).
5. **Unduh Service Account Key (Server-Side)**:
   - Buka **Project Settings > Service accounts**.
   - Klik **Generate new private key** dan simpan berkas JSON tersebut.
   - Atur path file di `.env` pada variabel `FIREBASE_CREDENTIALS_PATH=serviceAccountKey.json` atau letakkan isi JSON-nya pada variabel `FIREBASE_SERVICE_ACCOUNT_JSON`.
6. **Ambil Web App Config (Client-Side Login)**:
   - Buka **Project Settings > General > Your apps** dan pilih icon Web `</>`.
   - Salin nilai `apiKey`, `authDomain`, `projectId`, dan `appId` ke berkas `.env`.

---

## Panduan Deployment ke Vercel

Proyek ini telah dikonfigurasi secara zero-configuration untuk Vercel melalui `vercel.json` dan WSGI serverless:

1. **Push ke GitHub / GitLab**:
   Pastikan berkas `.env` dan `serviceAccountKey.json` **TIDAK** ikut ter-commit (sudah diatur di `.gitignore`).
2. **Import Proyek ke Vercel**:
   - Buka dashboard [Vercel](https://vercel.com/) dan klik **Add New > Project**.
   - Pilih repositori JDIH BKD Sidoarjo.
3. **Atur Environment Variables di Vercel Settings**:
   Tambahkan variabel berikut:
   - `DJANGO_SECRET_KEY`: Kunci rahasia acak yang aman.
   - `DEBUG`: `False`
   - `ALLOWED_HOSTS`: `.vercel.app,jdih.bkd.sidoarjokab.go.id`
   - `FIREBASE_PROJECT_ID`: ID proyek Firebase Anda.
   - `FIREBASE_STORAGE_BUCKET`: `nama-proyek.firebasestorage.app`
   - `FIREBASE_SERVICE_ACCOUNT_JSON`: Salin seluruh teks JSON service account dalam satu baris.
   - `FIREBASE_WEB_API_KEY`: Kunci API Web Firebase.
   - `FIREBASE_AUTH_DOMAIN`: Domain autentikasi Firebase.
   - `FIREBASE_APP_ID`: ID aplikasi Web Firebase.
4. **Klik Deploy**:
   Vercel akan mendeteksi `manage.py` dan `jdih_sidoarjo/wsgi.py` secara otomatis. Sesi pengguna berjalan mandiri menggunakan `signed_cookies` tanpa memerlukan server database relasional.

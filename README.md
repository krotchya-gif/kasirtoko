# 🏪 KasirToko

Aplikasi kasir UMKM berbasis web dengan Python + Flask + SQLite/PostgreSQL. Support multi-platform: Desktop, Tablet, dan Mobile.

[![Version](https://img.shields.io/badge/version-v2.1.1-blue.svg)]()
[![Python](https://img.shields.io/badge/python-3.9+-green.svg)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-orange.svg)]()

---

## 📑 Daftar Isi

- [Fitur Utama](#-fitur-utama)
- [Tech Stack](#-tech-stack)
- [Quick Start](#-quick-start)
- [Panduan Penggunaan](#-panduan-penggunaan)
- [Deployment](#-deployment)
- [Database Schema](#-database-schema)
- [API Endpoints](#-api-endpoints)
- [Changelog](#-changelog)

---

## ✨ Fitur Utama

### 🛒 Kasir
- Transaksi dengan keranjang belanja
- Diskon (persen/nominal)
- Multi metode pembayaran: Tunai, Transfer, QRIS, **Piutang**
- Hitung kembalian otomatis

### 📱 Scan Barcode
- Input produk via kamera HP (Chrome Android)
- Support format: EAN-13, EAN-8, CODE-39, CODE-128, QR Code

### 🏷️ Barcode Generator
- Generate barcode otomatis (EAN13/Code128)
- Cetak label barcode sheet PDF

### 🖨️ Cetak Struk
- Thermal printer support: USB, Bluetooth (RawBT), PDF
- Format 58mm & 80mm

### 📊 Laporan & Grafik
- Visualisasi data (Chart.js)
- Export PDF & CSV
- Produk terlaris, stok rendah

### 🔐 Manajemen Lengkap
- **Multi User**: Superadmin, Pemilik, Karyawan
- **Multi Tenant**: Multi toko/cabang
- **Void Transaksi**: Batalkan dengan pengembalian stok
- **Piutang**: Transaksi belum lunas dengan cicilan
- **Tutup Kasir**: End-of-day closing

---

## 🛠️ Tech Stack

| Komponen | Teknologi |
|----------|-----------|
| **Backend** | Flask 3.0+ (Python) |
| **Database** | SQLite (dev) / PostgreSQL (prod) |
| **Frontend** | Jinja2 + Vanilla JS + Custom CSS |
| **Charts** | Chart.js 4.4.1 |
| **PDF Export** | ReportLab 4.1.0, jsPDF 2.5.1 |
| **Barcode** | python-barcode 0.15.1 |
| **QR Scanner** | html5-qrcode 2.3.8 |

---

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Jalankan Aplikasi
```bash
python app.py
```

### 3. Buka Browser
```
http://localhost:5000
```

Untuk akses dari HP (dalam WiFi sama), gunakan IP yang muncul di terminal.

### 🔐 Login Default

| Username | Password | Role |
|----------|----------|------|
| `superadmin` | `superadmin123` | Setup toko & pemilik |
| `pemilik` | `pemilik123` | Full akses |
| `karyawan` | `karyawan123` | Kasir only |

> ⚠️ **Penting**: Ganti password default setelah login pertama!

---

## 📖 Panduan Penggunaan

### Struktur Project
```
kasirtoko/
├── app.py                 # Main Flask Application
├── README.md              # Dokumentasi utama (file ini)
├── detail-project.md      # Dokumentasi teknis lengkap
├── requirements.txt       # Python dependencies
├── kasirtoko.db          # Database SQLite
├── deploy.sh             # Script deployment
├── docker-compose.yml    # Docker config
├── Dockerfile            # Docker image
├── railway.json          # Railway config
├── vercel.json           # Vercel config
├── fix_unicode.py        # Helper Windows encoding
├── migrate_to_postgres.py # Migrasi database
│
├── templates/            # Jinja2 Templates
│   ├── index.html       # Main UI (kasir)
│   ├── login.html       # Halaman login
│   └── offline.html     # PWA offline page
│
├── static/              # Static Assets
│   ├── manifest.json    # PWA manifest
│   ├── sw.js           # Service Worker
│   └── icons/          # App icons
│
└── deploy/             # Deployment scripts
    ├── deploy-vps.sh   # VPS Ubuntu deploy
    └── nginx.conf      # Nginx config
```

### Transaksi Kasir
1. Pilih produk dari grid (klik/tap)
2. Atur quantity di keranjang
3. Pilih pelanggan (opsional)
4. Atur diskon jika perlu
5. Pilih metode bayar
6. Klik "BAYAR SEKARANG"

### Void Transaksi
1. Buka "📋 Riwayat Transaksi"
2. Klik transaksi yang akan di-void
3. Klik menu (⋮) → "🗑 Void Transaksi"
4. Masukkan alasan
5. Konfirmasi — stok otomatis dikembalikan

### Piutang (Hutang)
1. Saat transaksi, pilih metode "⏳ Piutang"
2. Input nama pelanggan & pembayaran awal (opsional)
3. Simpan transaksi
4. Untuk bayar cicilan: Buka menu Piutang → pilih transaksi → bayar

### Cetak Struk
| Metode | Cara |
|--------|------|
| Browser | Tombol 🖨️ Cetak (Ctrl+P) |
| RawBT | Tombol 📱 RawBT (Android Bluetooth) |
| PDF | Tombol 📤 PDF (share/download) |

---

## 🌐 Deployment

### Environment Variables
```bash
# Database Production
DATABASE_URL=postgresql://user:pass@host:port/db

# Security
SECRET_KEY=your-secret-key-min-32-chars
```

### Docker
```bash
docker-compose up -d
```

### Vercel (Serverless + PostgreSQL)
```bash
npm i -g vercel
vercel --prod
```

### VPS Ubuntu
```bash
bash deploy/deploy-vps.sh domain.com
```

---

## 🗄️ Database Schema

### Tabel Utama

```sql
-- Produk
CREATE TABLE produk (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nama TEXT NOT NULL,
    harga INTEGER DEFAULT 0,
    stok INTEGER DEFAULT 0,
    emoji TEXT DEFAULT '📦',
    kategori TEXT DEFAULT 'Umum',
    aktif INTEGER DEFAULT 1,
    harga_modal INTEGER DEFAULT 0,      -- HPP
    stok_min INTEGER DEFAULT 0,          -- Alert stok
    diskon INTEGER DEFAULT 0,            -- Diskon %
    barcode TEXT DEFAULT '',
    store_id INTEGER DEFAULT 1
);

-- Transaksi
CREATE TABLE transaksi (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    no_trx TEXT NOT NULL UNIQUE,         -- TRXYYMMDDHHMMSS
    waktu TEXT DEFAULT (datetime('now','localtime')),
    subtotal INTEGER DEFAULT 0,
    diskon INTEGER DEFAULT 0,
    total INTEGER DEFAULT 0,
    bayar INTEGER DEFAULT 0,
    kembalian INTEGER DEFAULT 0,
    kasir TEXT DEFAULT 'Kasir 1',
    pelanggan_id INTEGER,
    metode_bayar TEXT DEFAULT 'tunai',   -- tunai/transfer/qris/piutang
    status TEXT DEFAULT 'aktif',         -- aktif/void
    void_reason TEXT DEFAULT '',
    void_by TEXT DEFAULT '',
    is_lunas INTEGER DEFAULT 1,          -- 1=lunas, 0=piutang
    terbayar INTEGER DEFAULT 0,
    sisa_piutang INTEGER DEFAULT 0,
    store_id INTEGER DEFAULT 1
);

-- Transaksi Item (Detail)
CREATE TABLE transaksi_item (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    transaksi_id INTEGER NOT NULL,
    produk_id INTEGER NOT NULL,
    nama_produk TEXT NOT NULL,
    emoji TEXT DEFAULT '[BOX]',
    harga INTEGER NOT NULL,
    qty INTEGER NOT NULL,
    subtotal INTEGER NOT NULL
);

-- Pelanggan
CREATE TABLE pelanggan (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nama TEXT NOT NULL,
    telepon TEXT DEFAULT '',
    alamat TEXT DEFAULT '',
    catatan TEXT DEFAULT ''
);

-- Users (Multi-role)
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    nama TEXT NOT NULL,
    password TEXT NOT NULL,              -- Hashed
    role TEXT DEFAULT 'karyawan',        -- superadmin/pemilik/karyawan
    is_superadmin INTEGER DEFAULT 0,
    aktif INTEGER DEFAULT 1
);

-- Stores (Multi-tenant)
CREATE TABLE stores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    slug TEXT NOT NULL UNIQUE,
    address TEXT,
    phone TEXT,
    owner_id INTEGER NOT NULL
);

-- Kas/Dompet
CREATE TABLE kas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tipe TEXT NOT NULL,                  -- pemasukan/pengeluaran
    jumlah INTEGER NOT NULL,
    keterangan TEXT DEFAULT '',
    metode TEXT DEFAULT 'tunai'
);

-- Stok Log
CREATE TABLE stok_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    produk_id INTEGER NOT NULL,
    tipe TEXT NOT NULL,                  -- masuk/keluar/adjust
    jumlah INTEGER NOT NULL,
    stok_sebelum INTEGER NOT NULL,
    stok_sesudah INTEGER NOT NULL,
    alasan TEXT DEFAULT '',
    dibuat_oleh TEXT DEFAULT ''
);

-- Piutang Pembayaran
CREATE TABLE piutang_bayar (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    transaksi_id INTEGER NOT NULL,
    nominal INTEGER DEFAULT 0,
    metode_bayar TEXT DEFAULT 'tunai',
    catatan TEXT DEFAULT ''
);
```

📄 **Detail lengkap**: Lihat `detail-project.md`

---

## 🔌 API Endpoints

### Autentikasi
- `POST /login` - Login
- `GET /logout` - Logout

### Produk
- `GET /api/produk` - List produk
- `POST /api/produk` - Tambah produk
- `PUT /api/produk/<id>` - Update produk
- `DELETE /api/produk/<id>` - Hapus produk
- `GET /api/produk/scan/<barcode>` - Scan barcode

### Transaksi
- `GET /api/transaksi` - List transaksi
- `POST /api/transaksi` - Buat transaksi
- `GET /api/transaksi/<id>` - Detail transaksi
- `POST /api/transaksi/<id>/void` - Void transaksi

### Laporan
- `GET /api/laporan/hari-ini` - Laporan hari ini
- `GET /api/laporan/rentang` - Laporan periode
- `GET /api/laporan/chart` - Data grafik
- `GET /api/export/pdf` - Export PDF
- `GET /api/export/csv` - Export CSV

📄 **Semua endpoint**: Lihat `detail-project.md` bagian API Endpoints

---

## 📝 Changelog

### v2.1.1 (2026-03-21) - Bug Fixes
- ✅ **Fix**: Export PDF crash (koneksi database ditutup terlalu awal)
- ✅ **Fix**: Multi-tenant data leak - semua query kini filter `store_id`
- ✅ **Fix**: SQLite syntax hardcoded yang error di PostgreSQL
- ✅ **Fix**: GROUP BY hilang di daftar pelanggan
- ✅ **Fix**: Sinkronisasi tabel `pengguna` dan `users`
- ✅ **Fix**: Auto-assign karyawan ke toko saat migrasi

### v2.1.0 (2026-03-21)
- ✅ Redesign Riwayat Transaksi dengan tab Lunas/Belum Lunas
- ✅ Summary Card dengan statistik real-time
- ✅ Detail Transaksi lengkap dengan preview struk
- ✅ Export CSV dari frontend
- ✅ Dual Database (SQLite/PostgreSQL auto-switching)

### v2.0.0 (2026-03-17)
- ✅ **Void Transaksi** dengan pengembalian stok otomatis
- ✅ **Adjust Stok Manual** dengan alasan
- ✅ **Riwayat Stok Log** tracking perubahan stok
- ✅ **Grafik Penjualan** (Chart.js)
- ✅ **Export PDF Laporan**
- ✅ **Barcode Generator** & Print Sheet

### v1.11.0 (2026-03-16)
- ✅ Scan barcode via kamera HP
- ✅ Field barcode di produk
- ✅ Multi metode pembayaran (Tunai/Transfer/QRIS)

---

## 📄 License

MIT License — bebas digunakan untuk personal maupun komersial.

---

<div align="center">
  <sub>Dibuat dengan ❤️ untuk UMKM Indonesia</sub>
</div>

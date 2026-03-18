# 📱 Dokumentasi Aplikasi KasirToko

## 📋 Informasi Umum

| Atribut | Nilai |
|---------|-------|
| **Nama Aplikasi** | KasirToko |
| **Versi** | 2.1.0 |
| **Platform** | Web (Cross-platform) |
| **Backend** | Python Flask |
| **Database** | SQLite (local) / PostgreSQL (production) |
| **Frontend** | HTML5, CSS3, Vanilla JavaScript |
| **Template Engine** | Jinja2 |

---

## 🎯 Fitur Utama

### 1. Manajemen Produk
- ✅ Tambah, edit, hapus produk (soft delete)
- ✅ Kategorisasi produk
- ✅ Emoji/icon untuk produk
- ✅ Manajemen stok otomatis
- ✅ Harga modal dan harga jual
- ✅ Diskon per item
- ✅ **Barcode support** (input manual, scan, auto-generate)

### 2. Transaksi Penjualan
- ✅ Keranjang belanja dengan kalkulasi otomatis
- ✅ Diskon per item atau total transaksi (persen/nominal)
- ✅ Multi-metode pembayaran (Tunai, Transfer, QRIS, **Piutang**)
- ✅ **Void/Cancel transaksi** dengan pengembalian stok otomatis
- ✅ **Restore transaksi** yang sudah di-void
- ✅ Pilih pelanggan saat transaksi (opsional)
- ✅ **Piutang/Hutang** - Transaksi belum lunas dengan pembayaran cicilan

### 3. Scan Barcode
- 📷 **Scan barcode menggunakan kamera** (html5-qrcode)
- ⌨️ Input barcode manual
- 🔍 Pencarian produk via barcode
- 🏷️ **Generate barcode otomatis** (EAN13/Code128)
- 📄 **Cetak label barcode** (sheet PDF)

### 4. Printing & Struk
- 🖨️ **Print via browser** (Ctrl+P)
- 📱 **Print via mobile app** (RawBT, PrintHand)
- 🔌 **Print via USB Serial** (Web Serial API - Chrome Desktop)
- 📄 **PDF Struk** dengan jsPDF
- 👁️ **Preview Struk** — Lihat struk sebelum cetak dengan header toko
- 🎨 **Template Struk** — Customizable header, alamat, logo (PRO)
- 📤 **Share Struk Digital** — Multi platform:
  - 💬 **WhatsApp** — Gambar struk atau teks
  - ✈️ **Telegram** — Share dengan format teks
  - 📷 **Instagram** — Download & upload
  - ✉️ **Email** — Kirim detail transaksi
  - 🔗 **Native Share** — Web Share API (mobile)
  - 💾 **Download Image** — Simpan PNG struk
- 📐 **Format 58mm** — Optimized untuk printer thermal mini

### 5. Laporan & Analitik
- 📊 **Riwayat Transaksi** — Tab Lunas/Belum Lunas dengan summary card
- 📅 **Filter Periode** — Harian / Mingguan / Bulanan
- 🔍 **Search Transaksi** — Cari No. TRX atau Nama Pelanggan
- 📈 **Grafik penjualan** (Chart.js - Harian/Mingguan/Bulanan)
- 📉 Produk terlaris
- ⚠️ Stok menipis (alert)
- 📥 **Export data ke CSV/Excel**
- 📤 **Export laporan ke PDF** (ReportLab)

### 6. Manajemen Stok
- 📦 **Riwayat perubahan stok** (stok_log)
- ⚠️ Notifikasi stok menipis
- 🔧 **Adjust stok manual** dengan alasan
- 📝 Tracking stok masuk/keluar/void

### 7. Manajemen Pelanggan
- 👥 Daftar pelanggan dengan pencarian
- 📱 Nomor telepon dan kontak
- 💳 Riwayat pembelian per pelanggan
- 📊 Statistik belanja pelanggan

### 8. Multi Pengguna & Keamanan
- 👤 Manajemen pengguna (Pemilik/Karyawan)
- 🔐 Role-based access control
- 🔑 Ganti password sendiri
- 🔑 Reset password user (pemilik only)
- 📝 **Tutup Kasir** dengan konfirmasi pemilik

### 9. Manajemen Kas (Dompet)
- 💰 Arus kas manual (pemasukan/pengeluaran)
- 💵 Filter per metode (Tunai/Transfer/QRIS)
- 📊 Saldo keseluruhan & per metode
- 🗑️ Hapus entri kas

### 10. Import/Export Data
- 📤 Export produk ke CSV
- 📥 Import produk dari CSV (3 mode: tambah/timpa/ganti)
- 📄 Template CSV tersedia

---

## 🏗️ Arsitektur Teknis

### Struktur Proyek

```
kasirtoko/
├── app.py                 # Main Flask application
├── kasirtoko.db           # SQLite database
├── requirements.txt       # Python dependencies
├── fix_unicode.py         # Helper script for Windows encoding fix
├── templates/
│   ├── index.html         # Main UI (kasir)
│   └── login.html         # Login page
├── static/
│   ├── manifest.json      # PWA manifest
│   ├── sw.js              # Service Worker (tidak aktif)
│   └── icons/             # App icons
├── deploy/                # Deployment scripts
├── DOKUMENTASI.md         # Dokumentasi ini
├── DEPLOY.md              # Panduan deployment
└── CARA-PAKAI.md          # Panduan penggunaan
```

### Tech Stack

| Komponen | Teknologi |
|----------|-----------|
| **Backend Framework** | Flask 3.0+ |
| **Language** | Python 3.9+ |
| **Database** | SQLite (dev) / PostgreSQL (prod) — Auto switching |
| **Database Driver** | psycopg2-binary (PostgreSQL) |
| **Template** | Jinja2 |
| **CSS** | Custom CSS Variables (Dark/Light mode) |
| **JavaScript** | Vanilla ES6+ |
| **Charts** | Chart.js 4.4.1 |
| **PDF Export** | ReportLab 4.1.0 |
| **PDF Client** | jsPDF 2.5.1 |
| **Barcode** | python-barcode 0.15.1 |
| **QR/Barcode Scan** | html5-qrcode 2.3.8 |
| **Font** | Inter, DM Sans (Google Fonts) |

---

## 🔌 Dependencies

### Python Packages

```txt
flask==3.0.3
flask-cors==4.0.1
gunicorn==22.0.0
psycopg2-binary==2.9.9
reportlab==4.1.0
python-barcode==0.15.1
pillow==10.3.0
```

### CDN Resources

| Resource | URL | Fungsi |
|----------|-----|--------|
| Chart.js | `cdn.jsdelivr.net/npm/chart.js@4.4.1` | Grafik penjualan |
| jsPDF | `cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1` | Generate PDF struk |
| html5-qrcode | `unpkg.com/html5-qrcode@2.3.8` | Scan barcode kamera |

---

## 🚀 Cara Menggunakan Fitur

### Menjalankan Aplikasi (Local)

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Jalankan aplikasi
python app.py

# 3. Buka browser
# Local: http://localhost:5000
# Network: http://<IP>:5000 (untuk akses mobile)
```

### Login Default

| Username | Password | Role |
|----------|----------|------|
| `pemilik` | `pemilik123` | Pemilik Toko |
| `karyawan` | `karyawan123` | Karyawan |

### Riwayat Transaksi

**Akses:** Menu → 📋 Riwayat Transaksi

**Fitur:**
- **Tab Navigation**: "Lunas" 💰 vs "Belum Lunas" ⏳ (Piutang)
- **Search**: Cari No. Transaksi atau Nama Pelanggan
- **Filter Periode**: Harian 📅 / Mingguan 📆 / Bulanan 📊
- **Summary Card**: 
  - Lunas: Jumlah TRX, Produk Terjual, Omzet, Profit
  - Belum Lunas: Jumlah TRX, Produk Terjual, Total Piutang, Terbayar, Sisa Piutang
- **Export CSV**: Download data transaksi

**Card Transaksi:**
- Box tanggal kuning (tanggal besar, bulan, waktu)
- No. TRX dan Nama Pelanggan
- Total nominal (hijau besar)
- Badge metode bayar (TUNAI/TRANSFER/QRIS)
- Info kasir

### Detail Transaksi

Klik card transaksi untuk melihat detail:
- **Rincian**: Dibuat Oleh, Pembayaran, Tanggal lengkap
- **Tabel Pesanan**: Nama Barang | Jumlah (format: Rp20.000 x 2) | Harga
- **Ringkasan**: Total Pesanan, Total, Bayar, Kembali
- **Pelanggan**: Nama pelanggan (jika ada) dengan tombol copy
- **Actions**:
  - 🧾 Lihat Struk — Preview struk sebelum cetak
  - ⋮ Menu — Cetak, Bagikan, Void (pemilik only)

### Preview & Cetak Struk

1. Dari Detail Transaksi, klik "🧾 Lihat Struk"
2. Preview struk akan muncul dengan:
   - Header Toko (nama, alamat, telepon)
   - Info Transaksi (atas nama, no, tanggal, kasir, metode)
   - Tabel Item lengkap
   - Total, Bayar, Kembali
   - Footer "Terima kasih"
3. **Toggle Logo** (PRO): Aktifkan/nonaktifkan logo di struk
4. Klik "🖨️ Cetak Struk (58mm)" untuk print

### Void Transaksi

1. Buka "📋 Riwayat Transaksi"
2. Klik card transaksi yang akan di-void
3. Klik tombol "⋮" → "🗑 Void Transaksi"
4. Masukkan alasan void (wajib)
5. Konfirmasi — **Stok akan otomatis dikembalikan**

**Note:** 
- Void hanya bisa dilakukan oleh pemilik
- Transaksi void tetap muncul di riwayat dengan label "VOID"

### Adjust Stok Manual

1. Buka "⚙️ Kelola Produk"
2. Klik tombol "⚖️ Stok" pada produk
3. Masukkan stok baru
4. Pilih alasan adjust:
   - Stok Fisik Berbeda
   - Barang Rusak/Hilang
   - Barang Expired
   - Penyesuaian Awal
   - Lainnya
5. Simpan - perubahan tercatat di riwayat

### Generate & Cetak Barcode

**Generate Otomatis:**
1. Tambah/Edit produk
2. Klik tombol "🎲 Generate"
3. Barcode 13 digit otomatis terisi

**Cetak Label Barcode:**
1. Menu → 🏷️ Cetak Barcode
2. Pilih produk (checkbox) atau "Pilih Semua"
3. Klik "📄 Generate Sheet PDF"
4. Print PDF ke printer label

**Preview Individual:**
- Di modal Kelola Produk, klik "🏷️" pada produk
- Atau di modal Cetak Barcode, klik "👁 Preview"

### Lihat Grafik Penjualan

1. Buka "📊 Laporan" (hanya pemilik)
2. Klik tab "📈 Grafik"
3. Pilih tipe: Harian / Mingguan / Bulanan
4. Atur rentang tanggal
5. Grafik otomatis ter-update

### Export Laporan PDF

1. Buka "📊 Laporan"
2. Atur rentang tanggal
3. Klik tombol "📄 Export PDF"
4. PDF akan ter-download otomatis

### Share Struk Digital

Setelah transaksi sukses:

1. Klik tombol "📤 Share" di modal sukses
2. Pilih aplikasi tujuan:
   - **💬 WhatsApp** — Share gambar struk ke chat
   - **✈️ Telegram** — Share teks format ke channel/grup
   - **📷 Instagram** — Download gambar, lalu upload ke story/post
   - **✉️ Email** — Kirim detail transaksi ke email pelanggan
   - **🖨️ RawBT** — Print langsung ke printer Bluetooth
   - **💾 Simpan** — Download gambar PNG struk
3. Atau klik "📋 Salin Teks Struk" untuk copy teks

**Note:** Fitur share gambar menggunakan Web Share API (support di Chrome Android). Jika tidak support, gambar akan di-download otomatis.

### Scan Barcode (Kasir)

1. Klik tombol "🔢 Scan" di halaman kasir
2. Izinkan akses kamera
3. Arahkan kamera ke barcode produk
4. Produk otomatis masuk ke keranjang

**Note:** Scan barcode support Chrome/Edge Android. Firefox/Safari belum support kamera.

---

## 📊 Database Schema

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
    harga_modal INTEGER DEFAULT 0,
    stok_min INTEGER DEFAULT 0,
    diskon INTEGER DEFAULT 0,
    barcode TEXT DEFAULT '',
    dibuat TEXT DEFAULT (datetime('now','localtime')),
    diubah TEXT DEFAULT (datetime('now','localtime'))
);

-- Transaksi
CREATE TABLE transaksi (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    no_trx TEXT NOT NULL UNIQUE,
    waktu TEXT DEFAULT (datetime('now','localtime')),
    subtotal INTEGER DEFAULT 0,
    diskon INTEGER DEFAULT 0,
    diskon_val REAL DEFAULT 0,
    diskon_tipe TEXT DEFAULT 'persen',
    total INTEGER DEFAULT 0,
    bayar INTEGER DEFAULT 0,
    kembalian INTEGER DEFAULT 0,
    kasir TEXT DEFAULT 'Kasir 1',
    pelanggan_id INTEGER,              -- NULL = pelanggan umum
    metode_bayar TEXT DEFAULT 'tunai', -- tunai/transfer/qris/piutang
    tutup_kasir_id INTEGER,
    store_id INTEGER DEFAULT NULL,     -- Multi tenant
    -- Void fields
    status TEXT DEFAULT 'aktif',       -- aktif/void
    void_reason TEXT DEFAULT '',       -- alasan pembatalan
    void_by TEXT DEFAULT '',           -- user yang void
    void_at TEXT DEFAULT '',           -- waktu void
    -- Piutang fields
    is_lunas INTEGER DEFAULT 1,        -- 1=lunas, 0=belum lunas
    terbayar INTEGER DEFAULT 0,        -- jumlah sudah dibayar
    sisa_piutang INTEGER DEFAULT 0     -- sisa yang harus dibayar
);

-- Piutang Pembayaran (History cicilan)
CREATE TABLE piutang_bayar (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    transaksi_id INTEGER NOT NULL,
    nominal INTEGER NOT NULL DEFAULT 0,
    metode_bayar TEXT NOT NULL DEFAULT 'tunai',
    catatan TEXT DEFAULT '',
    dibuat_oleh TEXT DEFAULT '',
    store_id INTEGER DEFAULT NULL,
    waktu TEXT DEFAULT (datetime('now','localtime'))
);

-- Stok Log (Riwayat Perubahan Stok)
CREATE TABLE stok_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    produk_id INTEGER NOT NULL,
    tipe TEXT NOT NULL CHECK(tipe IN ('masuk','keluar','adjust')),
    jumlah INTEGER NOT NULL,
    stok_sebelum INTEGER NOT NULL,
    stok_sesudah INTEGER NOT NULL,
    alasan TEXT DEFAULT '',
    keterangan TEXT DEFAULT '',
    transaksi_id INTEGER DEFAULT NULL,
    dibuat_oleh TEXT DEFAULT '',
    waktu TEXT DEFAULT (datetime('now','localtime'))
);
```

---

## 🔌 API Endpoints

### Autentikasi
| Endpoint | Method | Deskripsi |
|----------|--------|-----------|
| `/login` | POST | Login user |
| `/logout` | GET | Logout user |

### Produk
| Endpoint | Method | Deskripsi |
|----------|--------|-----------|
| `/api/produk` | GET | List produk (dengan filter) |
| `/api/produk` | POST | Tambah produk |
| `/api/produk/<id>` | PUT | Update produk |
| `/api/produk/<id>` | DELETE | Hapus produk (soft) |
| `/api/produk/<id>/adjust-stok` | POST | Adjust stok manual |
| `/api/produk/<id>/stok-history` | GET | Riwayat stok produk |
| `/api/produk/scan/<barcode>` | GET | Cari produk by barcode |
| `/api/produk/kategori` | GET | List kategori |
| `/api/produk/stok-rendah` | GET | Produk stok menipis |

### Transaksi
| Endpoint | Method | Deskripsi |
|----------|--------|-----------|
| `/api/transaksi` | GET | List transaksi |
| `/api/transaksi` | POST | Buat transaksi |
| `/api/transaksi/<id>` | GET | Detail transaksi |
| `/api/transaksi/<id>/void` | POST | Void transaksi |
| `/api/transaksi/<id>/restore` | POST | Restore transaksi |

### Piutang
| Endpoint | Method | Deskripsi |
|----------|--------|-----------|
| `/api/piutang` | GET | List piutang belum lunas |
| `/api/piutang/<id>/bayar` | POST | Bayar cicilan piutang |
| `/api/piutang/<id>/history` | GET | History pembayaran piutang |
| `/api/piutang/reminder` | GET | Piutang jatuh tempo (>30 hari) |

### Laporan
| Endpoint | Method | Deskripsi |
|----------|--------|-----------|
| `/api/laporan/hari-ini` | GET | Laporan hari ini |
| `/api/laporan/rentang` | GET | Laporan rentang tanggal |
| `/api/laporan/top-produk` | GET | Produk terlaris |
| `/api/laporan/chart` | GET | Data grafik |

### Export
| Endpoint | Method | Deskripsi |
|----------|--------|-----------|
| `/api/export/csv` | GET | Export transaksi CSV |
| `/api/export/pdf` | GET | Export laporan PDF |
| `/api/produk/export-csv` | GET | Export produk CSV |
| `/api/produk/import-csv` | POST | Import produk CSV |

### Struk & Share
| Endpoint | Method | Deskripsi |
|----------|--------|-----------|
| `/api/struk/<id>/image` | GET | Generate struk sebagai gambar PNG |
| `/api/barcode/generate` | POST | Generate barcode image |
| `/api/barcode/print-sheet` | POST | Generate sheet PDF |

### Stok Log
| Endpoint | Method | Deskripsi |
|----------|--------|-----------|
| `/api/stok-log` | GET | Riwayat perubahan stok |

---

## 🐛 Troubleshooting

### Database Locked
```bash
# Hapus lock file
rm kasirtoko.db-shm kasirtoko.db-wal
```

### Port 5000 sudah digunakan
```bash
# Gunakan port lain
python app.py --port 5001
# Atau edit di app.py: app.run(port=5001)
```

### Scan Barcode tidak berfungsi
1. Pastikan menggunakan Chrome/Edge (terutama di Android)
2. Izinkan akses kamera saat diminta
3. Pastikan barcode terbaca jelas oleh kamera
4. Gunakan input manual sebagai alternatif

### Print tidak keluar
1. **Browser Print:** Pastikan printer terinstall di OS
2. **RawBT:** Install aplikasi RawBT dari Play Store
3. **Serial/USB:** Gunakan Chrome Desktop, cek koneksi printer

---

## 📝 Changelog

### v2.1.0 (Latest)
- ✅ **Redesign Riwayat Transaksi** — Tab Lunas/Belum Lunas, Summary Card, Filter Periode
- ✅ **Card Transaksi Baru** — Box tanggal kuning, badge metode bayar, info kasir
- ✅ **Detail Transaksi Lengkap** — Tabel pesanan, section pelanggan, action buttons
- ✅ **Preview Struk** — Lihat struk sebelum cetak dengan header toko customizable
- ✅ **Mobile Responsive** — Font Inter, touch targets lebih besar, layout optimized
- ✅ **Export CSV** — Download riwayat transaksi dari frontend
- ✅ **Dual Database** — SQLite (local) / PostgreSQL (production) otomatis switching

### v2.0.0
- ✅ **Void Transaksi** - Batalkan transaksi dengan pengembalian stok
- ✅ **Adjust Stok Manual** - Penyesuaian stok dengan alasan
- ✅ **Riwayat Stok Log** - Tracking semua perubahan stok
- ✅ **Grafik Penjualan** - Visualisasi data (Chart.js)
- ✅ **Export PDF Laporan** - Laporan dalam format PDF
- ✅ **Barcode Generator** - Generate & cetak label barcode
- ✅ **Restore Transaksi** - Kembalikan transaksi yang di-void
- ✅ Multi-metode pembayaran (Tunai/Transfer/QRIS)
- ✅ Tutup Kasir dengan konfirmasi pemilik

### v1.0.0
- ✅ Manajemen produk, transaksi, pelanggan
- ✅ Multi user dengan role
- ✅ Laporan dasar & export CSV
- ✅ Scan barcode kamera
- ✅ Print struk (browser, RawBT, Serial)

---

## 🚀 Deployment Guide

### Quick Start

```bash
# Vercel (Gratis + Serverless)
npm i -g vercel && vercel --prod

# Docker
docker-compose up -d

# VPS Ubuntu
bash deploy/deploy-vps.sh domain.com

# Local
./deploy.sh local
```

### Pilihan Platform

| Platform | Database | Biaya | Cocok Untuk |
|----------|----------|-------|-------------|
| **Vercel** | PostgreSQL | Gratis | Production, skala besar |
| **Railway** | PostgreSQL | Gratis tier | Production, simple |
| **Render** | PostgreSQL | Gratis tier | Production, simple |
| **VPS** | PostgreSQL | $5-20/bulan | Full control, private |
| **Docker** | SQLite/PostgreSQL | Variabel | Self-hosted, development |

### Deploy ke Vercel

1. **Install CLI & Login:**
```bash
npm i -g vercel
vercel login
```

2. **Deploy:**
```bash
vercel --prod
```

3. **Set Environment Variables** di Dashboard:
- `SECRET_KEY`: Generate dengan `openssl rand -hex 32`
- `DATABASE_URL` atau `POSTGRES_URL`: URL PostgreSQL (contoh: Neon, Supabase)

**Note:** Aplikasi otomatis menggunakan PostgreSQL saat environment variable `DATABASE_URL`/`POSTGRES_URL` tersedia. Jika tidak ada, akan fallback ke SQLite.

### Deploy dengan Docker

```bash
docker-compose up -d
```

Aplikasi tersedia di `http://localhost:5000`

### Deploy ke VPS

```bash
# Download script
curl -fsSL https://raw.githubusercontent.com/user/kasirtoko/main/deploy/deploy-vps.sh | bash -s domain.com
```

📖 Lihat [DEPLOY.md](DEPLOY.md) untuk panduan lengkap.

---

## 👨‍💻 Developer Info

**Dikembangkan oleh:** Permatari  
**Versi Web:** Flask + SQLite/PostgreSQL  
**Lisensi:** MIT License

---

---

## 📊 Status Fitur Setelah Rollback (Update: 19 Maret 2026)

### 🚨 Alasan Rollback
Rollback ke commit `a549494` dilakukan karena fitur **Service Worker & Push Notification** menyebabkan:
- Blank page putih di browser
- JavaScript code muncul di halaman
- Cache tidak ter-update

### ✅ FITUR AKTIF (Sudah Diimplementasikan)

| Fitur | Status | Keterangan |
|-------|--------|------------|
| **Transaksi Kasir** | ✅ OK | Tunai, Transfer, QRIS, Piutang |
| **Multi Metode Bayar** | ✅ OK | Semua metode berfungsi normal |
| **Manajemen Produk** | ✅ OK | CRUD, kategori, emoji, barcode |
| **Scan Barcode** | ✅ OK | Kamera & input manual |
| **Generate Barcode** | ✅ OK | EAN13/Code128 otomatis |
| **Cetak Label Barcode** | ✅ OK | PDF sheet |
| **Print Struk** | ✅ OK | Browser, RawBT, Serial USB |
| **Preview Struk** | ✅ OK | Customizable header |
| **Share Struk Digital** | ✅ OK | WA, Telegram, Email, Download |
| **Void Transaksi** | ✅ OK | Soft delete dengan restore stok |
| **Restore Transaksi** | ✅ OK | Un-void transaksi |
| **Multi User (RBAC)** | ✅ OK | Pemilik & Karyawan |
| **Tutup Kasir** | ✅ OK | Konfirmasi pemilik |
| **Manajemen Pelanggan** | ✅ OK | Daftar, riwayat, statistik |
| **Manajemen Kas/Dompet** | ✅ OK | Arus kas manual |
| **Piutang (Hutang)** | ✅ OK | Transaksi belum lunas, cicilan |
| **Riwayat Transaksi** | ✅ OK | Tab Lunas/Belum Lunas |
| **Laporan & Grafik** | ✅ OK | Chart.js, export PDF |
| **Stok Log** | ✅ OK | Riwayat perubahan stok |
| **Adjust Stok Manual** | ✅ OK | Dengan alasan |
| **Import/Export CSV** | ✅ OK | Produk & transaksi |
| **PWA Manifest** | ✅ OK | Install to home screen |
| **Multi Tenant** | ✅ OK | Multi toko dengan store_id |

### ❌ FITUR ROLLBACK (Belum/Tidak Aktif)

| Fitur | Status | Alasan Rollback |
|-------|--------|-----------------|
| **Service Worker** | ❌ Ter-rollback | Menyebabkan blank page |
| **Push Notification** | ❌ Ter-rollback | Bergantung pada SW |
| **Background Sync** | ❌ Ter-rollback | Bergantung pada SW |
| **Offline Mode** | ❌ Ter-rollback | Bergantung pada SW |

### 📝 Perubahan Database Pasca-Rollback

Rollback tidak menghapus struktur database. Kolom yang ditambahkan tetap ada:
- `metode_bayar` (tunai/transfer/qris/piutang)
- `is_lunas` (1=lunas, 0=belum lunas)
- `terbayar` (jumlah sudah dibayar untuk piutang)
- `sisa_piutang` (sisa yang harus dibayar)
- `store_id` (multi tenant)
- `tipe_harga` (eco/normal/premium)

### 🐛 BUG YANG SUDAH DI-FIX Pasca-Rollback

| Bug | Fix | Commit |
|-----|-----|--------|
| Unicode emoji error di Windows | Ganti emoji dengan ASCII | `f30202c` |
| `login_required` decorator missing | Tambah decorator | `f30202c` |
| `_piutangPelangganList.find is not a function` | Add Array.isArray check | `e3ee137` |
| Piutang status salah di riwayat | Gunakan `is_lunas` dari backend | `ab34985` |
| Syntax error kurung kurawal | Fix typo `})` | `bd91a4f` |

---

## 🧪 Testing Checklist

### Test Kasir Core
- [ ] Tambah produk ke keranjang
- [ ] Edit qty & hapus item
- [ ] Terapkan diskon (persen & nominal)
- [ ] Transaksi tunai - uang pas
- [ ] Transaksi tunai - ada kembalian
- [ ] Transaksi transfer
- [ ] Transaksi QRIS
- [ ] Transaksi piutang - bayar partial
- [ ] Transaksi piutang - bayar full

### Test Print & Share
- [ ] Print struk via browser
- [ ] Preview struk
- [ ] Share ke WhatsApp
- [ ] Download struk PNG

### Test Produk
- [ ] CRUD produk
- [ ] Generate barcode otomatis
- [ ] Scan barcode kamera
- [ ] Cetak label barcode PDF
- [ ] Adjust stok manual

### Test Transaksi Management
- [ ] Lihat riwayat transaksi (Lunas)
- [ ] Lihat riwayat transaksi (Belum Lunas)
- [ ] Detail transaksi
- [ ] Void transaksi (pemilik)
- [ ] Restore transaksi
- [ ] Filter periode (hari/minggu/bulan)

### Test Piutang
- [ ] Buat transaksi piutang
- [ ] Cek tab "Belum Lunas"
- [ ] Bayar cicilan piutang
- [ ] Lihat history pembayaran piutang
- [ ] Verifikasi status jadi lunas setelah full bayar

### Test Multi User
- [ ] Login sebagai pemilik
- [ ] Login sebagai karyawan
- [ ] Test role access (karyawan tidak bisa void)
- [ ] Ganti password

### Test Laporan
- [ ] Laporan harian
- [ ] Laporan mingguan
- [ ] Laporan bulanan
- [ ] Grafik penjualan
- [ ] Export CSV
- [ ] Export PDF

---

*Dokumen ini terakhir diperbarui: 19 Maret 2026*

# 📋 KasirToko — Riwayat Versi

Semua perubahan signifikan pada aplikasi KasirToko dicatat di sini.
Format: `[Versi] — Tanggal — Ringkasan`

---

## [v2.0.0] — 2026-03-17 — 🎉 Major Update

### ✨ Fitur Baru

#### 🗑️ Void Transaksi
- **Void transaksi** — Batalkan transaksi yang salah dengan pengembalian stok otomatis
- **Restore transaksi** — Kembalikan transaksi yang sudah di-void (batalkan void)
- **Alasan void wajib** — Setiap void harus ada keterangan
- **Filter status** — Lihat transaksi aktif, void, atau semua
- **Audit trail** — Tercatat siapa yang void dan kapan

#### 📦 Riwayat Perubahan Stok (Stok Log)
- **Tabel `stok_log`** — Tracking semua perubahan stok
- **Tipe perubahan**: masuk, keluar, adjust
- **Detail perubahan**: stok sebelum → sesudah, jumlah, alasan
- **Filter & search** — Filter berdasarkan tanggal, tipe, produk
- **Siapa & kapan** — Tercatat user dan timestamp

#### ⚖️ Adjust Stok Manual
- **Form adjust stok** — Ubah stok fisik dengan alasan
- **Pilihan alasan**:
  - Stok Fisik Berbeda
  - Barang Rusak/Hilang
  - Barang Expired
  - Penyesuaian Awal
  - Lainnya
- **Keterangan tambahan** — Catat detail penyesuaian
- **Preview selisih** — Lihat perubahan sebelum simpan

#### 📊 Grafik Penjualan (Chart.js)
- **Integrasi Chart.js 4.4.1**
- **3 tipe grafik**: Harian, Mingguan, Bulanan
- **Dual axis**: Bar (Omzet) + Line (Jumlah Transaksi)
- **Interactive**: Hover untuk detail
- **Stats ringkasan**: Total transaksi, omzet, diskon

#### 📄 Export PDF Laporan
- **Library ReportLab 4.1.0**
- **Laporan lengkap**: Ringkasan + detail transaksi
- **Desain gelap** — Sesuai tema aplikasi
- **Printable A4** — Siap print atau simpan

#### 🏷️ Barcode Generator
- **Generate otomatis** — Tombol 🎲 di form produk (13 digit EAN13)
- **Format support**: EAN13 & Code128
- **Cetak label barcode**:
  - Sheet PDF dengan grid layout
  - 55 label per halaman A4
  - Pilih multiple produk
- **Preview individual** — Lihat barcode sebelum cetak
- **Download PNG** — Simpan barcode per produk

#### 📤 Share Struk Digital
- **Multi-platform share**:
  - 💬 WhatsApp — Gambar struk langsung ke chat
  - ✈️ Telegram — Share format teks rapi
  - 📷 Instagram — Download & upload story/post
  - ✉️ Email — Kirim detail transaksi lengkap
  - 🖨️ RawBT — Print langsung dari share menu
  - 💾 Download — Simpan PNG struk
- **Modal share** — UI grid pilihan aplikasi
- **Preview struk** — Lihat sebelum share
- **Salin teks** — Copy struk ke clipboard
- **API**: `GET /api/struk/<id>/image` — Generate PNG

### 🖼️ Perubahan Database

#### Tabel Baru
```sql
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

#### Kolom Baru (tabel transaksi)
- `status` — 'aktif' atau 'void'
- `void_reason` — Alasan pembatalan
- `void_by` — User yang melakukan void
- `void_at` — Timestamp void

### 🔌 API Endpoints Baru

| Endpoint | Method | Deskripsi |
|----------|--------|-----------|
| `/api/transaksi/<id>/void` | POST | Void transaksi |
| `/api/transaksi/<id>/restore` | POST | Restore transaksi |
| `/api/produk/<id>/adjust-stok` | POST | Adjust stok manual |
| `/api/produk/<id>/stok-history` | GET | Riwayat stok produk |
| `/api/stok-log` | GET | Semua riwayat stok |
| `/api/laporan/chart` | GET | Data grafik |
| `/api/export/pdf` | GET | Export laporan PDF |
| `/api/struk/<id>/image` | GET | Generate struk PNG |
| `/api/barcode/generate` | POST | Generate barcode image |
| `/api/barcode/print-sheet` | POST | Generate sheet PDF |

### 📦 Dependencies Baru
```txt
reportlab==4.1.0      # PDF export
python-barcode==0.15.1 # Barcode generator
pillow==10.3.0        # Image processing
```

### 📚 Dokumentasi
- Update DOKUMENTASI.md — Dokumentasi teknis lengkap
- Update README.md — Quick start & fitur baru
- Update CHANGELOG.md — Riwayat perubahan

---

## [v1.11.3] — 2026-03-16

### 📚 Dokumentasi
- **Panduan Akses dari HP untuk Scan Barcode**
  - Penjelasan mengapa butuh HTTPS/localhost untuk kamera
  - Opsi 1: ADB Reverse (untuk development)
  - Opsi 2: ngrok (tunneling HTTPS)
  - Opsi 3: LocalTunnel (alternatif gratis)
  - Opsi 4: Deploy ke server (production)
- **Update pesan startup** — sekarang menampilkan IP untuk akses mobile

---

## [v1.11.2] — 2026-03-16

### 🐛 Perbaikan
- **Ganti ke Library html5-qrcode**
  - Sebelumnya: Menggunakan BarcodeDetector API native (tidak support banyak browser)
  - Sekarang: Menggunakan library **html5-qrcode** (support lebih banyak browser)
  - Fallback tetap ke BarcodeDetector jika tersedia
  - Auto-deteksi library yang tersedia

---

## [v1.11.1] — 2026-03-16

### 🐛 Perbaikan
- **Tombol 📷 Scan di Form Produk**
  - Sebelumnya: Barcode hanya bisa diketik manual
  - Sekarang: Ada tombol **📷 Scan** di sebelah field barcode
  - Scan langsung mengisi field barcode di form

- **Error Handling Kamera**
  - Pesan error yang lebih informatif
  - Deteksi izin kamera secara eksplisit
  - Visual feedback dengan warna (hijau/kuning/merah)
  - Auto-reset kamera saat retry

### 📋 Dokumentasi
- Update panduan scan barcode dengan troubleshooting lengkap
- Penjelasan persyaratan HTTPS/localhost untuk kamera

---

## [v1.11.0] — 2026-03-16

### ✨ Fitur Baru
- **Scan Barcode untuk Input Produk**
  - Tombol 🔢 Scan di sebelah search bar
  - Menggunakan BarcodeDetector API (Chrome/Edge Android)
  - Support format: EAN-13, EAN-8, CODE-39, CODE-128, UPC-A, UPC-E, QR Code
  - Fallback: Input barcode manual jika kamera tidak tersedia
  - Field barcode di form tambah/edit produk
  - API endpoint: `GET /api/produk/scan/{barcode}`

### 🖼️ Perubahan Database
- Kolom baru `barcode` pada tabel `produk`

---

## [v1.10.0] — 2026-03-16

### ✨ Fitur Baru
- **Pilihan Aplikasi Printer Mobile**
  - Sebelumnya: hanya mendukung RawBT (hardcoded)
  - Sekarang: bisa pilih aplikasi printer di Pengaturan Toko
  - Pilihan: RawBT (default) / Aplikasi Custom (myprinter) / PrintHand / Lainnya
  - Custom URI Scheme: input manual untuk integrasi aplikasi printer sendiri (Flutter, native, dll)
  - Data tersimpan di database: `printer_app_scheme` dan `printer_app_name`

### 🖼️ Perubahan Database
- Kolom baru `printer_app_scheme` (default: 'rawbt')
- Kolom baru `printer_app_name` (default: 'RawBT')

---

## [v1.9.3] — 2026-02-27

### 🐛 Perbaikan
- **RawBT — Hapus prefix `text?charset=utf-8&text=` dari struk**
  - Root cause: URI scheme salah → `rawbt:text?charset=utf-8&text=...`
  - Fix: `rawbt:?charset=utf-8&text=...` (hapus kata "text" dari path)
  - Sebelumnya: baris pertama struk muncul teks `text?charset=utf-8&text=`

- **Desktop Browser Print — Struk terbalik 180°**
  - Root cause: `position:fixed` pada `#printArea` menyebabkan Chrome mengirim halaman dengan orientasi salah ke driver Rongta
  - Fix: `position:fixed` → `position:static`
  - Tambah `@page { size: 58mm auto; }` yang sesuai dengan setting driver Rongta

- **Desktop Browser Print — Konten keluar dari kertas fisik 57mm**
  - Root cause: `@page size` 58mm (driver) vs kertas fisik 57mm menyebabkan konten terpotong di tepi
  - Fix: konten width dikurangi ke 55mm + `margin: 0 1.5mm` agar centered dalam 58mm page
  - Perhitungan: 1.5mm + 55mm + 1.5mm = 58mm (page) → semua masuk dalam 57mm kertas fisik

- **Desktop Browser Print — Struk terputus-putus saat cetak**
  - Root cause: browser menyisipkan page break otomatis di tengah konten struk
  - Fix: tambah `page-break-inside: avoid` + `break-inside: avoid` pada semua elemen struk (`*`, `#printArea`, `.psrow`, `.psitem`, `.psitem-h`, `.psfooter`, `.psdiv`)
  - Tambah `orphans: 1; widows: 1` pada body untuk mencegah baris terpotong sendirian

---

## [v1.9.2] — 2026-02-27

### ✨ Fitur Baru
- **Emoji Picker Berkategori (151 emoji)**
  - Sebelumnya: 51 emoji flat tanpa kategori
  - Sekarang: 151 emoji dikelompokkan dalam 6 tab kategori
  - 🍔 Makanan (54) · 🥤 Minuman (18) · 🧼 Kebutuhan (25) · 👗 Fashion (32) · 📱 Elektronik (21) · 📦 Umum (29)
  - Tab kategori klik → grid emoji berganti, tab aktif highlight

- **Navigasi Desktop — Dropdown ⚙️ Pengaturan**
  - Topbar disederhanakan dari 10 tombol individual → 5 tombol utama + 1 dropdown
  - Tombol tetap di topbar: 📋 Riwayat, 📊 Laporan, 💰 Dompet, 👥 Pelanggan, 🔒 Tutup Kasir
  - Dropdown ⚙️ Pengaturan ▾ berisi: ➕ Tambah Produk, ⚙️ Kelola Produk, 📤 Import/Export, 👥 Tim, 🏪 Pengaturan Toko, 🔑 Akun/Password
  - Dropdown tutup otomatis saat klik di luar area

- **Navigasi Mobile — Accordion ⚙️ Pengaturan di Drawer**
  - Drawer disederhanakan: item manajemen dipindah ke accordion
  - Level utama drawer: Laporan, Dompet, Pelanggan, Riwayat Transaksi, Tutup Kasir
  - Tap ⚙️ Pengaturan → expand/collapse accordion berisi semua item management
  - Accordion item: Tambah Produk, Kelola Produk, Import/Export, Tim, Pengaturan Toko, Akun/Password

---

## [v1.9.1] — 2026-02-27

### ✨ Fitur Baru
- **Smart Print Buttons (Platform Detection)**
  - Tombol cetak di modal sukses muncul sesuai platform secara otomatis
  - 🖨️ Cetak — semua platform (window.print via browser)
  - 📱 RawBT — hanya muncul di Android (deep link `rawbt:text?...`)
  - 🔌 Serial/USB — hanya muncul di Chrome desktop (Web Serial API)
  - 📤 PDF — semua platform (jsPDF, share/download otomatis)

- **Print via Web Serial API (ESC/POS)**
  - Kirim data langsung ke printer USB/COM port tanpa dialog OS
  - Format ESC/POS: init, center/left align, bold, row, full cut
  - Port diingat otomatis (`getPorts()`) setelah pertama dipilih
  - Lebar struk otomatis: 32 char (58mm) / 42 char (80mm)

- **Print via RawBT Deep Link**
  - URI scheme `rawbt:text?charset=utf-8&text=...` untuk Android
  - Struk plain-text terformat (header center, item rows, footer)
  - Mendukung printer Bluetooth Classic & BLE via app RawBT

### 🐛 Perbaikan
- **PDF Struk — Ukuran Tepat Sesuai Kertas**
  - Root cause: estimasi tinggi pre-kalkulasi (`LH=4.5mm`) tidak cocok dengan step aktual drawing (`fs×0.38+0.8` ≈ 3.46mm), menghasilkan ~25mm whitespace kosong di bawah
  - Fix: two-pass approach — Pass 1 simulasi tracking `y` tanpa menggambar untuk dapat `docH` akurat; Pass 2 buat jsPDF dengan `format:[W, docH]` dan gambar
  - Font lebih besar: 7pt → 8pt untuk baris item, 10pt → 11pt untuk judul di 58mm
- **Print CSS (window.print)**
  - Ganti `body *{visibility:hidden}` → `body>*:not(#printArea){display:none!important}` untuk isolasi lebih bersih
  - Tambah `box-sizing:border-box` pada `#printArea` agar lebar tepat
  - Font size & line-height dikalibrasi: 10px/1.35 untuk 58mm, 11px/1.35 untuk 80mm
  - `updatePrintCSS()` memperbarui CSS dinamis saat ukuran kertas di pengaturan berubah

---

## [v1.9.0] — 2026-02-27

### ✨ Fitur Baru
- **Tutup Kasir (End of Day)**
  - Karyawan bisa proses tutup kasir → status *pending*
  - Pemilik konfirmasi → otomatis buat entri Kas per metode pembayaran
  - Badge `!` merah di tombol Tutup Kasir jika ada pending konfirmasi
  - Bisa tutup beberapa kali sehari (hanya transaksi belum ditutup yang ikut)
- **Metode Pembayaran di Checkout**
  - Selector 💵 Tunai / 🏦 Transfer / 📱 QRIS saat proses bayar
  - Transfer & QRIS: nominal bayar otomatis = total, kembalian disembunyikan
  - Metode tersimpan di database & tampil di struk
- **Bagikan Struk sebagai PDF**
  - Tombol "📤 Bagikan PDF" di modal sukses transaksi
  - PDF ukuran menyesuaikan setting kertas toko (58mm / 80mm)
  - Android/iOS: share sheet ke app printer Bluetooth (PrintHand, RawBT, dll)
  - Desktop: fallback otomatis ke download PDF

### 🗃️ Perubahan Database
- Kolom baru `metode_bayar` (tunai/transfer/qris) pada tabel `transaksi`
- Kolom baru `tutup_kasir_id` pada tabel `transaksi`
- Tabel baru `tutup_kasir` (id, waktu, total, total_tunai, total_transfer, total_qris, jumlah_trx, keterangan, status, dibuat_oleh, dikonfirmasi_oleh, waktu_konfirmasi)

### 🔌 API Baru
| Method | Endpoint | Akses | Keterangan |
|--------|----------|-------|------------|
| GET | `/api/tutup-kasir/preview` | Semua | Preview transaksi belum ditutup |
| POST | `/api/tutup-kasir` | Semua | Proses tutup kasir (pending) |
| GET | `/api/tutup-kasir` | Pemilik | Riwayat tutup kasir |
| POST | `/api/tutup-kasir/<id>/konfirmasi` | Pemilik | Konfirmasi ke Kas |

---

## [v1.8.0] — 2026-02-27

### ✨ Fitur Baru
- **Sistem Login & Sesi**
  - Halaman login sebelum masuk aplikasi
  - Sesi tersimpan 30 hari (tidak perlu login ulang kecuali logout)
  - Tombol Logout di topbar
- **Manajemen Pengguna (Role-Based Access)**
  - Role **Pemilik**: akses penuh semua fitur
  - Role **Karyawan**: hanya kasir, pelanggan, riwayat transaksi
  - Pemilik bisa tambah/hapus/reset password karyawan
  - Modal "👥 Tim" khusus pemilik
- **Ganti Password**
  - Semua user bisa ganti password sendiri
  - Verifikasi password lama sebelum ganti
- **Responsive Mobile**
  - Bottom navigation bar (mobile)
  - Hamburger drawer sidebar (mobile)
  - Layout 1 kolom di layar kecil
- **Dark / Light Mode**
  - Toggle ☀️/🌙 di topbar
  - Preferensi tersimpan di browser (`localStorage`)

### 🗃️ Perubahan Database
- Tabel baru `pengguna` (id, username, nama, password, role, aktif, dibuat)
- Akun default seed: `pemilik/pemilik123` dan `karyawan/karyawan123`

### 🔌 API Baru
| Method | Endpoint | Akses | Keterangan |
|--------|----------|-------|------------|
| GET/POST | `/login` | Publik | Halaman & proses login |
| GET | `/logout` | Login | Logout & hapus sesi |
| GET/POST | `/api/pengguna` | Pemilik | List & tambah pengguna |
| DELETE | `/api/pengguna/<id>` | Pemilik | Nonaktifkan pengguna |
| POST | `/api/pengguna/<id>/reset-password` | Pemilik | Reset password karyawan |
| POST | `/api/pengguna/ganti-password` | Semua | Ganti password sendiri |

---

## [v1.7.0] — 2026-02

### ✨ Fitur Baru
- **Kelola Produk — Search & Sort**
  - Pencarian produk real-time di modal kelola
  - Sort berdasarkan nama, stok, harga, kategori
  - Filter produk aktif/nonaktif

---

## [v1.6.0] — 2026-02

### ✨ Fitur Baru
- **Deploy ke Server Ubuntu**
  - Konfigurasi production dengan Gunicorn + Nginx
  - Environment variable `SECRET_KEY` untuk keamanan
  - Akses dari jaringan lokal (LAN) via IP server

---

## [v1.5.0] — 2026-02

### ✨ Fitur Baru
- **Produk Lanjutan**
  - Kolom `harga_modal` (HPP) — untuk hitung laba
  - Kolom `stok_min` — trigger alert stok rendah
  - Kolom `diskon` — diskon per produk (%)
- **Laporan Stok Rendah**
  - Daftar produk dengan stok ≤ `stok_min`

### 🗃️ Perubahan Database
- Kolom baru `harga_modal`, `stok_min`, `diskon` pada tabel `produk`

---

## [v1.4.0] — 2026-02

### ✨ Fitur Baru
- **Laporan Lanjutan**
  - Top 10 produk terlaris (by qty & omzet)
  - Stok rendah alert
  - Grafik omzet harian (range tanggal)
- **Export CSV Laporan**
  - Export data transaksi ke CSV
  - Export data produk ke CSV
  - Template CSV untuk import produk massal

---

## [v1.3.0] — 2026-01

### ✨ Fitur Baru
- **Manajemen Pelanggan**
  - CRUD pelanggan (nama, telepon, alamat, catatan)
  - Pilih pelanggan saat transaksi
  - Riwayat belanja per pelanggan
  - Total belanja & jumlah transaksi per pelanggan

### 🗃️ Perubahan Database
- Tabel baru `pelanggan`
- Kolom baru `pelanggan_id` pada tabel `transaksi`

---

## [v1.2.0] — 2026-01

### ✨ Fitur Baru
- **Dompet / Kas**
  - Catat pemasukan & pengeluaran manual
  - Metode: Tunai, Transfer Bank, QRIS
  - Filter periode (dari–ke tanggal)
  - Saldo real-time (all-time) + breakdown tunai/non-tunai
  - Total masuk & keluar per periode
  - Hapus entri kas

### 🗃️ Perubahan Database
- Tabel baru `kas` (id, tipe, jumlah, keterangan, waktu, metode)

---

## [v1.1.0] — 2026-01

### ✨ Fitur Baru
- **PWA (Progressive Web App)**
  - Install ke homescreen Android/iOS
  - Ikon aplikasi & splash screen
  - Mode offline (halaman offline.html)
  - Service Worker caching aset statis
- **Pengaturan Toko**
  - Nama toko, alamat, telepon
  - Pesan footer struk
  - Ukuran kertas struk (58mm / 80mm)

### 🗃️ Perubahan Database
- Tabel baru `pengaturan` (key-value store)

---

## [v1.0.0] — 2026-01

### 🎉 Rilis Pertama

**Fitur dasar kasir:**
- Daftar produk dengan emoji, nama, harga, stok, kategori
- Keranjang belanja (tambah, kurang, hapus item)
- Diskon transaksi (nominal atau persen)
- Proses bayar — hitung kembalian otomatis
- Struk transaksi (modal & cetak ke printer thermal via `window.print()`)
- Riwayat transaksi (list + detail per transaksi)
- Laporan harian (omzet, total transaksi, rata-rata)
- Import / Export produk via CSV
- CRUD produk (tambah, edit, hapus/nonaktifkan)
- Filter produk berdasarkan kategori
- Database SQLite dengan WAL mode

### 🗃️ Database Awal
- Tabel `produk`
- Tabel `transaksi`
- Tabel `transaksi_item`

---

## 🔐 Akun Default

| Username | Password | Role |
|----------|----------|------|
| `pemilik` | `pemilik123` | Pemilik (akses penuh) |
| `karyawan` | `karyawan123` | Karyawan (kasir only) |

> **Penting:** Ganti password default setelah pertama kali login!

---

## 🗄️ Struktur Database Lengkap (v1.11)

| Tabel | Keterangan | Kolom Penting |
|-------|------------|---------------|
| `produk` | Data produk & stok | `barcode` (baru v1.11) |
| `transaksi` | Header transaksi penjualan | `metode_bayar`, `tutup_kasir_id` |
| `transaksi_item` | Detail item per transaksi | - |
| `kas` | Arus kas manual (dompet) | `metode` |
| `tutup_kasir` | Riwayat tutup kasir harian | - |
| `pelanggan` | Data pelanggan | - |
| `pengaturan` | Konfigurasi toko (key-value) | `printer_app_scheme`, `printer_app_name` (baru v1.10) |
| `pengguna` | Akun login & role | `role` (pemilik/karyawan) |

---

## 🔌 API Endpoints (Ringkasan)

| Method | Endpoint | Akses | Keterangan |
|--------|----------|-------|------------|
| GET | `/api/produk` | Semua | List produk (filter: kategori, cari) |
| GET | `/api/produk/scan/{barcode}` | Semua | **(Baru v1.11)** Cari produk by barcode |
| POST | `/api/produk` | Pemilik | Tambah produk |
| PUT | `/api/produk/{id}` | Pemilik | Edit produk |
| DELETE | `/api/produk/{id}` | Pemilik | Hapus produk (soft delete) |
| POST | `/api/transaksi` | Semua | Buat transaksi baru |
| GET | `/api/transaksi` | Semua | List riwayat transaksi |
| GET | `/api/laporan/hari-ini` | Pemilik | Laporan hari ini |
| GET | `/api/kas` | Pemilik | Arus kas/dompet |
| POST | `/api/kas` | Pemilik | Tambah pemasukan/pengeluaran |
| GET | `/api/tutup-kasir/preview` | Semua | Preview tutup kasir |
| POST | `/api/tutup-kasir` | Semua | Proses tutup kasir |
| GET | `/api/pelanggan` | Semua | List pelanggan |
| POST | `/api/pelanggan` | Semua | Tambah pelanggan |
| GET/POST | `/api/pengaturan` | Pemilik | Get/update pengaturan toko |
| GET/POST | `/api/pengguna` | Pemilik | Manajemen user |

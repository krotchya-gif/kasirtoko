# 📋 Dokumentasi Lengkap KasirToko

> **Tujuan Dokumen Ini**: Panduan komprehensif untuk mengenal, memahami, dan menduplikasi project KasirToko ke framework lain.

---

## 📌 1. OVERVIEW PROJECT

| Atribut | Nilai |
|---------|-------|
| **Nama** | KasirToko |
| **Versi** | v2.1.1 |
| **Deskripsi** | Aplikasi Point of Sale (POS) untuk UMKM berbasis web |
| **Arsitektur** | Monolithic - Server Rendered + REST API |
| **Platform** | Cross-platform (Desktop, Tablet, Mobile) |
| **Deployment** | Local (SQLite), Production (PostgreSQL) |

---

## 🏗️ 2. STRUKTUR PROJECT

```
kasirtoko/
├── app.py                 # Main Flask Application (4.000+ baris)
├── README.md              # Dokumentasi utama (start here)
├── detail-project.md      # Dokumentasi teknis lengkap
├── requirements.txt       # Python dependencies
├── kasirtoko.db          # SQLite database (auto-generated)
├── fix_unicode.py        # Helper script Windows encoding
├── migrate_to_postgres.py # Script migrasi database
├── deploy.sh             # Script deployment otomatis
├── docker-compose.yml    # Docker setup
├── Dockerfile            # Docker image config
├── railway.json          # Railway deployment config
├── vercel.json           # Vercel deployment config
│
├── templates/            # Jinja2 Templates
│   ├── index.html       # Main UI (kasir)
│   ├── login.html       # Halaman login
│   └── offline.html     # Halaman offline (PWA)
│
├── static/              # Static Assets
│   ├── manifest.json    # PWA manifest
│   ├── sw.js           # Service Worker (inactive)
│   └── icons/          # App icons
│
└── deploy/             # Deployment scripts (minimal)
    ├── deploy-vps.sh   # VPS Ubuntu deployment
    └── nginx.conf      # Nginx configuration
```

---

## 🛠️ 3. TECH STACK

### Backend
| Komponen | Teknologi | Versi |
|----------|-----------|-------|
| Framework | Flask | 3.0.3 |
| Language | Python | 3.9+ |
| Database (Dev) | SQLite | Built-in |
| Database (Prod) | PostgreSQL | 13+ |
| Database Driver | psycopg2-binary | 2.9.9 |
| CORS | flask-cors | 4.0.1 |
| WSGI Server | gunicorn | 22.0.0 |

### Frontend
| Komponen | Teknologi | Source |
|----------|-----------|--------|
| Template Engine | Jinja2 | Flask built-in |
| Styling | Custom CSS Variables | Native |
| JavaScript | Vanilla ES6+ | Native |
| Icons | Emoji Unicode | Native |
| Fonts | Inter, DM Sans | Google Fonts CDN |

### External Libraries (CDN)
| Library | Version | Purpose |
|---------|---------|---------|
| Chart.js | 4.4.1 | Grafik penjualan |
| jsPDF | 2.5.1 | Generate PDF struk |
| html5-qrcode | 2.3.8 | Scan barcode kamera |

### Python Libraries (PDF/Barcode)
| Library | Version | Purpose |
|---------|---------|---------|
| reportlab | 4.1.0 | Export laporan PDF |
| python-barcode | 0.15.1 | Generate barcode |
| pillow | 10.3.0 | Image processing |

---

## 🗄️ 4. DATABASE SCHEMA LENGKAP

### 4.1 Tabel Core

#### `produk` - Data Produk
```sql
CREATE TABLE produk (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,  -- ID unik
    nama            TEXT NOT NULL,                       -- Nama produk
    harga           INTEGER DEFAULT 0,                   -- Harga jual
    stok            INTEGER DEFAULT 0,                   -- Stok saat ini
    emoji           TEXT DEFAULT '[BOX]',               -- Icon produk
    kategori        TEXT DEFAULT 'Umum',                -- Kategori
    aktif           INTEGER DEFAULT 1,                  -- Soft delete flag
    -- Kolom lanjutan
    harga_modal     INTEGER DEFAULT 0,                  -- HPP (Harga Pokok Penjualan)
    stok_min        INTEGER DEFAULT 0,                  -- Batas stok minimum
    diskon          INTEGER DEFAULT 0,                  -- Diskon % per item
    barcode         TEXT DEFAULT '',                    -- Kode barcode
    -- Metadata
    dibuat          TEXT DEFAULT (datetime('now','localtime')),
    diubah          TEXT DEFAULT (datetime('now','localtime')),
    -- Multi-tenant
    store_id        INTEGER DEFAULT 1
);
```

#### `transaksi` - Header Transaksi
```sql
CREATE TABLE transaksi (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    no_trx          TEXT NOT NULL UNIQUE,               -- Nomor transaksi (TRXYYMMDDHHMMSS)
    waktu           TEXT DEFAULT (datetime('now','localtime')),
    subtotal        INTEGER DEFAULT 0,                  -- Total sebelum diskon
    diskon          INTEGER DEFAULT 0,                  -- Nilai diskon
    diskon_val      REAL DEFAULT 0,                     -- Nilai diskon (raw)
    diskon_tipe     TEXT DEFAULT 'persen',              -- 'persen' atau 'nominal'
    total           INTEGER DEFAULT 0,                  -- Total setelah diskon
    bayar           INTEGER DEFAULT 0,                  -- Jumlah dibayar
    kembalian       INTEGER DEFAULT 0,                  -- Kembalian
    kasir           TEXT DEFAULT 'Kasir 1',             -- Nama kasir
    
    -- Relasi
    pelanggan_id    INTEGER,                            -- FK ke pelanggan (NULL = umum)
    
    -- Pembayaran
    metode_bayar    TEXT DEFAULT 'tunai',               -- 'tunai', 'transfer', 'qris', 'piutang'
    
    -- Tutup Kasir
    tutup_kasir_id  INTEGER,                            -- FK ke tutup_kasir
    
    -- Void/Status
    status          TEXT DEFAULT 'aktif',               -- 'aktif' atau 'void'
    void_reason     TEXT DEFAULT '',                    -- Alasan void
    void_by         TEXT DEFAULT '',                    -- User yang void
    void_at         TEXT DEFAULT '',                    -- Waktu void
    
    -- Piutang
    is_lunas        INTEGER DEFAULT 1,                  -- 1=lunas, 0=belum lunas
    terbayar        INTEGER DEFAULT 0,                  -- Jumlah sudah dibayar
    sisa_piutang    INTEGER DEFAULT 0,                  -- Sisa yang harus dibayar
    
    -- Multi-tenant
    store_id        INTEGER DEFAULT 1
);
```

#### `transaksi_item` - Detail Item Transaksi
```sql
CREATE TABLE transaksi_item (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    transaksi_id    INTEGER NOT NULL,                   -- FK ke transaksi
    produk_id       INTEGER NOT NULL,                   -- FK ke produk
    nama_produk     TEXT NOT NULL,                      -- Snapshot nama (saat transaksi)
    emoji           TEXT DEFAULT '[BOX]',              -- Snapshot emoji
    harga           INTEGER NOT NULL,                   -- Snapshot harga
    qty             INTEGER NOT NULL,                   -- Jumlah
    subtotal        INTEGER NOT NULL,                   -- harga * qty
    FOREIGN KEY (transaksi_id) REFERENCES transaksi(id) ON DELETE CASCADE
);
```

### 4.2 Tabel Manajemen

#### `pelanggan` - Data Pelanggan
```sql
CREATE TABLE pelanggan (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    nama            TEXT NOT NULL,
    telepon         TEXT DEFAULT '',
    alamat          TEXT DEFAULT '',
    catatan         TEXT DEFAULT '',
    dibuat          TEXT DEFAULT (datetime('now','localtime')),
    store_id        INTEGER DEFAULT 1
);
```

#### `kas` - Arus Kas/Dompet Manual
```sql
CREATE TABLE kas (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    tipe            TEXT NOT NULL,                      -- 'pemasukan' atau 'pengeluaran'
    jumlah          INTEGER NOT NULL,
    keterangan      TEXT DEFAULT '',
    metode          TEXT DEFAULT 'tunai',              -- 'tunai', 'transfer', 'qris'
    waktu           TEXT DEFAULT (datetime('now','localtime')),
    store_id        INTEGER DEFAULT 1
);
```

#### `tutup_kasir` - End of Day Closing
```sql
CREATE TABLE tutup_kasir (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    waktu               TEXT DEFAULT (datetime('now','localtime')),
    total               INTEGER DEFAULT 0,              -- Total semua metode
    total_tunai         INTEGER DEFAULT 0,
    total_transfer      INTEGER DEFAULT 0,
    total_qris          INTEGER DEFAULT 0,
    jumlah_trx          INTEGER DEFAULT 0,
    keterangan          TEXT DEFAULT '',
    status              TEXT DEFAULT 'pending',        -- 'pending' atau 'confirmed'
    dibuat_oleh         TEXT DEFAULT '',
    dikonfirmasi_oleh   TEXT DEFAULT '',
    waktu_konfirmasi    TEXT DEFAULT '',
    store_id            INTEGER DEFAULT 1
);
```

#### `stok_log` - Riwayat Perubahan Stok
```sql
CREATE TABLE stok_log (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    produk_id       INTEGER NOT NULL,                   -- FK ke produk
    tipe            TEXT NOT NULL,                      -- 'masuk', 'keluar', 'adjust'
    jumlah          INTEGER NOT NULL,                   -- Jumlah perubahan
    stok_sebelum    INTEGER NOT NULL,                   -- Stok sebelum perubahan
    stok_sesudah    INTEGER NOT NULL,                   -- Stok setelah perubahan
    alasan          TEXT DEFAULT '',                    -- Alasan perubahan
    keterangan      TEXT DEFAULT '',                    -- Keterangan tambahan
    transaksi_id    INTEGER DEFAULT NULL,               -- FK (jika terkait transaksi)
    dibuat_oleh     TEXT DEFAULT '',                    -- User yang melakukan
    waktu           TEXT DEFAULT (datetime('now','localtime')),
    store_id        INTEGER DEFAULT 1,
    FOREIGN KEY (produk_id) REFERENCES produk(id) ON DELETE CASCADE
);
```

### 4.3 Tabel Multi-Tenant

#### `users` - Pengguna Sistem (Modern)
```sql
CREATE TABLE users (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    username        TEXT NOT NULL UNIQUE COLLATE NOCASE,
    nama            TEXT NOT NULL,
    password        TEXT NOT NULL,                      -- Hashed (pbkdf2:sha256)
    role            TEXT DEFAULT 'karyawan',           -- 'superadmin', 'pemilik', 'karyawan'
    is_superadmin   INTEGER DEFAULT 0,                  -- 1 = superadmin
    aktif           INTEGER DEFAULT 1,
    dibuat          TEXT DEFAULT (datetime('now','localtime'))
);
```

#### `pengguna` - Pengguna Sistem (Legacy - backward compatible)
```sql
CREATE TABLE pengguna (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    username        TEXT NOT NULL UNIQUE COLLATE NOCASE,
    nama            TEXT NOT NULL,
    password        TEXT NOT NULL,
    role            TEXT DEFAULT 'karyawan',           -- 'pemilik' atau 'karyawan'
    aktif           INTEGER DEFAULT 1,
    dibuat          TEXT DEFAULT (datetime('now','localtime'))
);
```

#### `stores` - Data Toko/Cabang
```sql
CREATE TABLE stores (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL,                      -- Nama toko
    slug            TEXT NOT NULL UNIQUE COLLATE NOCASE, -- URL-friendly name
    address         TEXT,
    phone           TEXT,
    email           TEXT,
    owner_id        INTEGER NOT NULL,                   -- FK ke users
    is_active       INTEGER DEFAULT 1,
    dibuat          TEXT DEFAULT (datetime('now','localtime')),
    FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE CASCADE
);
```

#### `user_stores` - Relasi Karyawan ke Toko
```sql
CREATE TABLE user_stores (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL,                   -- FK ke users (karyawan)
    store_id        INTEGER NOT NULL,                   -- FK ke stores
    role            TEXT NOT NULL,                      -- 'admin' atau 'kasir'
    dibuat          TEXT DEFAULT (datetime('now','localtime')),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (store_id) REFERENCES stores(id) ON DELETE CASCADE,
    UNIQUE(user_id, store_id)
);
```

#### `admin_logs` - Audit Trail Superadmin
```sql
CREATE TABLE admin_logs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    admin_id        INTEGER NOT NULL,                   -- FK ke users (superadmin)
    store_id        INTEGER,                            -- Toko yang terkena aksi
    action_type     TEXT NOT NULL,                      -- Jenis aksi
    target_table    TEXT,                               -- Tabel yang diubah
    target_id       INTEGER,                            -- ID record yang diubah
    old_value       TEXT,                               -- Nilai lama (JSON)
    new_value       TEXT,                               -- Nilai baru (JSON)
    ip_address      TEXT,
    dibuat          TEXT DEFAULT (datetime('now','localtime')),
    FOREIGN KEY (admin_id) REFERENCES users(id),
    FOREIGN KEY (store_id) REFERENCES stores(id)
);
```

### 4.4 Tabel Piutang

#### `piutang_bayar` - History Pembayaran Cicilan
```sql
CREATE TABLE piutang_bayar (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    transaksi_id    INTEGER NOT NULL,                   -- FK ke transaksi
    nominal         INTEGER DEFAULT 0,                  -- Jumlah bayar
    metode_bayar    TEXT DEFAULT 'tunai',
    catatan         TEXT DEFAULT '',
    dibuat_oleh     TEXT DEFAULT '',
    waktu           TEXT DEFAULT (datetime('now','localtime')),
    store_id        INTEGER DEFAULT 1,
    FOREIGN KEY (transaksi_id) REFERENCES transaksi(id) ON DELETE CASCADE
);
```

### 4.5 Tabel Konfigurasi

#### `pengaturan` - Key-Value Store
```sql
CREATE TABLE pengaturan (
    kunci           TEXT PRIMARY KEY,
    nilai           TEXT NOT NULL
);

-- Default values:
-- ('nama_toko', 'TOKO KELONTONG MAJU JAYA')
-- ('alamat', 'Jl. Raya No. 1')
-- ('telp', '0812-xxxx-xxxx')
-- ('pesan_struk', 'Terima kasih sudah berbelanja!')
-- ('ukuran_kertas', '58')  -- 58mm atau 80mm
-- ('printer_app_scheme', 'rawbt')
-- ('printer_app_name', 'RawBT')
```

---

## 🔌 5. API ENDPOINTS LENGKAP

### 5.1 Autentikasi
| Endpoint | Method | Akses | Deskripsi |
|----------|--------|-------|-----------|
| `/login` | POST | Public | Login user |
| `/logout` | GET | Public | Logout user |

### 5.2 Superadmin (Multi-Tenant)
| Endpoint | Method | Akses | Deskripsi |
|----------|--------|-------|-----------|
| `/api/admin/stores` | GET | Superadmin | List semua toko |
| `/api/admin/stores` | POST | Superadmin | Buat toko baru |
| `/api/admin/stores/<id>` | PUT | Superadmin | Update data toko (termasuk slug & owner) |
| `/api/admin/owners` | GET | Superadmin | List semua pemilik |
| `/api/admin/owners` | POST | Superadmin | Buat pemilik baru |
| `/api/admin/owners/<id>/reset-password` | POST | Superadmin | Reset password pemilik |
| `/api/admin/enter-store/<id>` | POST | Superadmin | Ghost mode masuk toko |
| `/api/admin/exit-store` | POST | Superadmin | Keluar ghost mode |
| `/api/admin/logs` | GET | Superadmin | Audit logs |

### 5.3 Store Management
| Endpoint | Method | Akses | Deskripsi |
|----------|--------|-------|-----------|
| `/api/my-stores` | GET | Login | List toko yang bisa diakses |
| `/api/switch-store/<id>` | POST | Login | Switch toko aktif |
| `/api/stores/<id>/users` | GET | Pemilik | List karyawan toko |
| `/api/stores/<id>/users` | POST | Pemilik | Tambah karyawan |
| `/api/stores/<id>/users/<uid>` | DELETE | Pemilik | Hapus karyawan |

### 5.4 Produk
| Endpoint | Method | Akses | Deskripsi |
|----------|--------|-------|-----------|
| `/api/produk` | GET | Login | List produk (filter: kategori, cari) |
| `/api/produk` | POST | Pemilik | Tambah produk |
| `/api/produk/<id>` | PUT | Pemilik | Update produk |
| `/api/produk/<id>` | DELETE | Pemilik | Soft delete produk |
| `/api/produk/scan/<barcode>` | GET | Login | Cari produk by barcode |
| `/api/produk/kategori` | GET | Login | List kategori unik |
| `/api/produk/stok-rendah` | GET | Pemilik | Produk stok menipis |
| `/api/produk/<id>/adjust-stok` | POST | Pemilik | Adjust stok manual |
| `/api/produk/<id>/stok-history` | GET | Pemilik | Riwayat stok produk |

### 5.5 Transaksi
| Endpoint | Method | Akses | Deskripsi |
|----------|--------|-------|-----------|
| `/api/transaksi` | GET | Login | List transaksi (filter: dari, ke, status) |
| `/api/transaksi` | POST | Login | Buat transaksi baru |
| `/api/transaksi/<id>` | GET | Login | Detail transaksi |
| `/api/transaksi/<id>/void` | POST | Pemilik | Void transaksi |
| `/api/transaksi/<id>/restore` | POST | Pemilik | Restore transaksi |

### 5.6 Piutang
| Endpoint | Method | Akses | Deskripsi |
|----------|--------|-------|-----------|
| `/api/piutang` | GET | Login | List piutang belum lunas |
| `/api/piutang/<id>/bayar` | POST | Login | Bayar cicilan piutang |
| `/api/piutang/<id>/history` | GET | Login | History pembayaran |
| `/api/piutang/reminder` | GET | Login | Piutang jatuh tempo |

### 5.7 Kas/Dompet
| Endpoint | Method | Akses | Deskripsi |
|----------|--------|-------|-----------|
| `/api/kas` | GET | Pemilik | List arus kas |
| `/api/kas` | POST | Pemilik | Tambah pemasukan/pengeluaran |
| `/api/kas/<id>` | DELETE | Pemilik | Hapus entri kas |
| `/api/kas/reset` | POST | Pemilik | Reset saldo kas |

### 5.8 Tutup Kasir
| Endpoint | Method | Akses | Deskripsi |
|----------|--------|-------|-----------|
| `/api/tutup-kasir/preview` | GET | Login | Preview transaksi belum ditutup |
| `/api/tutup-kasir` | POST | Login | Proses tutup kasir |
| `/api/tutup-kasir` | GET | Pemilik | Riwayat tutup kasir |
| `/api/tutup-kasir/<id>/konfirmasi` | POST | Pemilik | Konfirmasi tutup kasir |

### 5.9 Pelanggan
| Endpoint | Method | Akses | Deskripsi |
|----------|--------|-------|-----------|
| `/api/pelanggan` | GET | Login | List pelanggan |
| `/api/pelanggan` | POST | Login | Tambah pelanggan |
| `/api/pelanggan/<id>` | GET | Login | Detail pelanggan + stats |
| `/api/pelanggan/<id>` | PUT | Login | Update pelanggan |
| `/api/pelanggan/<id>` | DELETE | Login | Hapus pelanggan |

### 5.10 Laporan
| Endpoint | Method | Akses | Deskripsi |
|----------|--------|-------|-----------|
| `/api/laporan/hari-ini` | GET | Pemilik | Laporan hari ini |
| `/api/laporan/rentang` | GET | Pemilik | Laporan rentang tanggal |
| `/api/laporan/top-produk` | GET | Pemilik | Produk terlaris |
| `/api/laporan/chart` | GET | Pemilik | Data grafik (harian/mingguan/bulanan) |
| `/api/laporan/stok` | GET | Pemilik | Laporan stok |
| `/api/laporan/keuangan` | GET | Pemilik | Laporan keuangan |

### 5.11 Export/Import
| Endpoint | Method | Akses | Deskripsi |
|----------|--------|-------|-----------|
| `/api/export/csv` | GET | Pemilik | Export transaksi CSV |
| `/api/export/pdf` | GET | Pemilik | Export laporan PDF |
| `/api/produk/export-csv` | GET | Pemilik | Export produk CSV |
| `/api/produk/import-csv` | POST | Pemilik | Import produk CSV |
| `/api/produk/template-csv` | GET | Pemilik | Download template CSV |

### 5.12 Barcode
| Endpoint | Method | Akses | Deskripsi |
|----------|--------|-------|-----------|
| `/api/barcode/generate` | POST | Pemilik | Generate barcode image |
| `/api/barcode/print-sheet` | POST | Pemilik | Generate sheet PDF |

### 5.13 Struk
| Endpoint | Method | Akses | Deskripsi |
|----------|--------|-------|-----------|
| `/api/struk/<id>/image` | GET | Login | Generate struk PNG |

### 5.14 Stok Log
| Endpoint | Method | Akses | Deskripsi |
|----------|--------|-------|-----------|
| `/api/stok-log` | GET | Pemilik | Riwayat perubahan stok |

### 5.15 Pengaturan
| Endpoint | Method | Akses | Deskripsi |
|----------|--------|-------|-----------|
| `/api/pengaturan` | GET | Login | Get pengaturan toko |
| `/api/pengaturan` | POST | Pemilik | Update pengaturan |

### 5.16 User Management
| Endpoint | Method | Akses | Deskripsi |
|----------|--------|-------|-----------|
| `/api/pengguna` | GET | Pemilik | List pengguna |
| `/api/pengguna` | POST | Pemilik | Tambah pengguna |
| `/api/pengguna/<id>` | DELETE | Pemilik | Nonaktifkan pengguna |
| `/api/pengguna/<id>/reset-password` | POST | Pemilik | Reset password |
| `/api/pengguna/ganti-password` | POST | Login | Ganti password sendiri |

---

## ⚙️ 6. BUSINESS LOGIC

### 6.1 Alur Transaksi
```
1. User memilih produk → masuk ke keranjang (session/client-side)
2. User pilih pelanggan (opsional)
3. User atur diskon (persen/nominal)
4. User pilih metode bayar:
   - Tunai: input nominal bayar → hitung kembalian
   - Transfer/QRIS: auto-fill total
   - Piutang: input nama pelanggan + pembayaran awal (opsional)
5. Simpan transaksi:
   - Insert header ke `transaksi`
   - Insert items ke `transaksi_item`
   - Update stok produk
   - Insert ke `kas` (jika bukan piutang)
   - Log stok keluar ke `stok_log`
```

### 6.2 Alur Void Transaksi
```
1. Pemilih memilih transaksi → klik Void
2. Input alasan void (wajib)
3. Validasi:
   - Transaksi harus exist dan status 'aktif'
   - Tidak bisa void jika sudah di tutup_kasir confirmed
4. Proses:
   - Kembalikan stok ke produk
   - Log stok masuk ke `stok_log` (alasan: void_transaksi)
   - Update status transaksi jadi 'void'
   - Insert pengeluaran ke `kas` (jika transaksi lunas)
```

### 6.3 Alur Tutup Kasir
```
1. Karyawan klik "Tutup Kasir"
2. System hitung transaksi yang belum ditutup
3. Preview: breakdown per metode (tunai, transfer, qris)
4. Karyawan submit → status 'pending'
5. Pemilik buka menu Tutup Kasir → lihat pending
6. Pemilik konfirmasi:
   - Insert pemasukan ke `kas` per metode
   - Update status jadi 'confirmed'
```

### 6.4 Alur Piutang
```
1. Transaksi dengan metode 'piutang' → is_lunas=0
2. List piutang belum lunas muncul di tab "Belum Lunas"
3. Pembayaran cicilan:
   - Input nominal dan metode
   - Insert ke `piutang_bayar`
   - Update `transaksi.terbayar` dan `sisa_piutang`
   - Jika sisa = 0 → is_lunas=1
   - Insert pemasukan ke `kas`
```

### 6.5 Permission Matrix

| Fitur | Superadmin | Pemilik | Karyawan |
|-------|------------|---------|----------|
| Kasir/Transaksi | ✗ | ✓ | ✓ |
| Lihat Produk | ✓ (View Only) | ✓ | ✓ |
| Kelola Produk | ✗ | ✓ | ✗ |
| Lihat Laporan | ✗ | ✓ | ✗ |
| Lihat Dompet | ✗ | ✓ | ✗ |
| Void Transaksi | ✗ | ✓ | ✗ |
| Adjust Stok | ✗ | ✓ | ✗ |
| Kelola Pengguna | ✗ | ✓ (tokonya) | ✗ |
| Tutup Kasir | ✗ | ✓ | ✓ (create only) |
| Multi Tenant Panel | ✓ | ✗ | ✗ |
| Reset Password Pemilik | ✓ | ✗ | ✗ |

---

## 🔐 7. SECURITY & AUTHENTICATION

### 7.1 Session Management
- Flask session dengan `SECRET_KEY`
- Session lifetime: 30 hari
- Session stored server-side (signed cookie)

### 7.2 Password Hashing
```python
from werkzeug.security import generate_password_hash, check_password_hash

# Hash saat create/update password
hash = generate_password_hash(password, method='pbkdf2:sha256')

# Verify saat login
valid = check_password_hash(stored_hash, input_password)
```

### 7.3 Role-Based Access Control
- Decorator `@login_required` - Cek session aktif
- Decorator `@pemilik_required` - Hanya pemilik/superadmin
- Decorator `@superadmin_required` - Hanya superadmin
- Decorator `@require_store_access` - Cek akses ke toko

### 7.4 Permission Helpers
```python
def is_superadmin(user_id)         # Cek apakah superadmin
def is_store_owner(user_id, store_id)  # Cek apakah owner toko
def can_access_store(user_id, store_id)  # Cek akses (superadmin/owner/assigned)
def can_manage_products(user_id, store_id)  # Cek bisa manage produk
```

---

## 🎨 8. FRONTEND ARCHITECTURE

### 8.1 CSS Variable System (Theme)
```css
:root {
  --bg: #0f1117;           /* Background */
  --surface: #1a1d27;      /* Card background */
  --surface2: #242736;     /* Secondary surface */
  --border: #2e3244;       /* Borders */
  --accent: #f5a623;       /* Primary accent (orange) */
  --green: #3dffa0;        /* Success */
  --red: #ff5c5c;          /* Danger/Error */
  --blue: #5c9aff;         /* Info */
  --purple: #b97cff;       /* Secondary accent */
  --text: #f0f0f8;         /* Primary text */
  --muted: #8891a8;        /* Secondary text */
  --fh: 'Inter', sans-serif;  /* Heading font */
  --fb: 'DM Sans', sans-serif; /* Body font */
}
```

### 8.2 Layout Structure
```
┌─────────────────────────────────────────────┐
│  [☰] LOGO                    [User] [⚙️] [↩] │  ← Topbar
├─────────────────────────────────────────────┤
│  ┌──────────────────┐  ┌─────────────────┐  │
│  │ Search: [______] │  │ Keranjang [0]   │  │
│  │ [Kategori Tabs]  │  │                 │  │
│  │                  │  │ [Item list...]  │  │
│  │ [Produk Grid]    │  │                 │  │
│  │                  │  │ Subtotal: Rp 0  │  │
│  │                  │  │ Diskon: - Rp 0  │  │
│  │                  │  │ TOTAL: Rp 0     │  │
│  │                  │  │ [💳 BAYAR]      │  │
│  └──────────────────┘  └─────────────────┘  │
├─────────────────────────────────────────────┤
│  [🏪] [🛒] [📦] [📊] [☰]                     │  ← Bottom Nav (Mobile)
└─────────────────────────────────────────────┘
```

### 8.3 State Management
- **Cart State**: JavaScript Object (`cart = {}`)
- **Selected Customer**: Hidden input + display label
- **Payment Method**: Button active state
- **Theme**: localStorage (`theme = 'light'|'dark'`)
- **Store ID**: Session server-side

### 8.4 Key JavaScript Functions
```javascript
// Cart Management
function addToCart(product)      // Tambah item
function updateQty(id, delta)    // Update quantity
function removeFromCart(id)      // Hapus item
function clearCart()             // Kosongkan keranjang

// UI Functions
function openModal(id)           // Buka modal
function closeModal(id)          // Tutup modal
function showToast(msg)          // Show notification
function toggleTheme()           // Dark/Light mode

// Transaction
function updateSummary()         // Update perhitungan
function hitungKem()             // Hitung kembalian
function prosesTrx()             // Submit transaksi

// Product
function filterProduk()          // Filter by search/category
function renderProduk()          // Render grid
```

---

## 🚀 9. DEPLOYMENT

### 9.1 Environment Variables
```bash
# Database (PostgreSQL untuk production)
POSTGRES_URL=postgresql://user:pass@host:port/db
DATABASE_URL=postgresql://user:pass@host:port/db

# Security
SECRET_KEY=your-secret-key-min-32-chars

# Optional (untuk local dev tidak wajib)
FLASK_ENV=production
```

### 9.2 Deployment Methods
```bash
# 1. Local Development
python app.py

# 2. Docker
docker-compose up -d

# 3. Vercel (Serverless + PostgreSQL)
npm i -g vercel
vercel --prod

# 4. VPS Ubuntu
bash deploy/deploy-vps.sh domain.com

# 5. Using deploy.sh
./deploy.sh local    # Run local
./deploy.sh docker   # Docker mode
./deploy.sh vercel   # Deploy to Vercel
./deploy.sh vps      # Deploy to VPS
```

---

## 🔄 10. DUPLIKASI KE FRAMEWORK LAIN

### 10.1 Checklist Port Framework

#### Backend (contoh: Node.js/Express)
- [ ] Setup database connection (SQLite/PostgreSQL)
- [ ] Implement semua tabel schema
- [ ] Buat model/repository untuk setiap tabel
- [ ] Implement semua API endpoints dengan validasi yang sama
- [ ] Setup session/auth middleware
- [ ] Implement role-based access control
- [ ] Setup template engine (EJS/Pug/Handlebars) atau API JSON saja

#### Frontend (contoh: React/Vue)
- [ ] Setup CSS variable system (copy dari style di index.html)
- [ ] Buat komponen: Topbar, ProductGrid, Cart, Modals
- [ ] Implement state management (Redux/Vuex/Context)
- [ ] Implement cart logic (add, update, remove, clear)
- [ ] Buat fungsi API calls ke backend
- [ ] Implement barcode scanner (html5-qrcode)
- [ ] Setup Chart.js untuk grafik
- [ ] Implement PDF generation (jsPDF)

#### Database Migration
```sql
-- Jalankan semua CREATE TABLE dari bagian 4 di atas
-- Setelah itu, insert default data:

-- Default users
INSERT INTO users (username, nama, password, role, is_superadmin) 
VALUES ('superadmin', 'Super Administrator', '<HASH>', 'superadmin', 1);

INSERT INTO users (username, nama, password, role) 
VALUES ('pemilik', 'Pemilik Toko', '<HASH>', 'pemilik');

INSERT INTO pengguna (username, nama, password, role) 
VALUES ('pemilik', 'Pemilik Toko', '<HASH>', 'pemilik');

-- Default settings
INSERT INTO pengaturan (kunci, nilai) VALUES
('nama_toko', 'TOKO SAYA'),
('alamat', 'Alamat Toko'),
('telp', '0812-xxxx-xxxx'),
('pesan_struk', 'Terima kasih!'),
('ukuran_kertas', '58'),
('printer_app_scheme', 'rawbt'),
('printer_app_name', 'RawBT');
```

### 10.2 Struktur JSON API Response

#### Response Standard
```json
// Success
{
  "ok": true,
  "data": { ... }
}

// List
{
  "rows": [...],
  "stats": { ... }
}

// Error
{
  "error": "Pesan error",
  "detail": "..."  // optional
}
```

#### Transaksi Object
```json
{
  "id": 123,
  "no_trx": "TRX260321143052",
  "waktu": "2026-03-21 14:30:52",
  "subtotal": 50000,
  "diskon": 5000,
  "diskon_tipe": "persen",
  "total": 45000,
  "bayar": 50000,
  "kembalian": 5000,
  "kasir": "Kasir 1",
  "pelanggan_id": null,
  "pelanggan_nama": "",
  "metode_bayar": "tunai",
  "status": "aktif",
  "is_lunas": 1,
  "items": [
    {
      "id": 1,
      "produk_id": 5,
      "nama_produk": "Indomie Goreng",
      "emoji": "🍜",
      "harga": 3500,
      "qty": 2,
      "subtotal": 7000
    }
  ]
}
```

#### Produk Object
```json
{
  "id": 5,
  "nama": "Indomie Goreng",
  "harga": 3500,
  "stok": 100,
  "emoji": "🍜",
  "kategori": "Makanan",
  "aktif": 1,
  "harga_modal": 2500,
  "stok_min": 10,
  "diskon": 0,
  "barcode": "8999999999999"
}
```

### 10.3 Logic Penting untuk Diport

#### 1. Perhitungan Transaksi
```javascript
// Hitung total
diskonAmount = diskonTipe === 'persen' 
  ? Math.round(subtotal * diskonVal / 100)
  : diskonVal;
total = subtotal - diskonAmount;

// Hitung kembalian
kembalian = bayar - total;

// Validasi
if (kembalian < 0) return error;
```

#### 2. Void Transaction Logic
```javascript
// 1. Cek transaksi exist dan status = 'aktif'
// 2. Cek transaksi belum di tutup_kasir confirmed
// 3. Loop items:
//    - Update produk.stok += item.qty
//    - Insert stok_log (tipe: 'masuk', alasan: 'void_transaksi')
// 4. Update transaksi.status = 'void'
// 5. Insert kas pengeluaran (jika lunas)
```

#### 3. Stok Adjustment Logic
```javascript
// 1. Get produk current stok
// 2. Calculate selisih = stok_baru - stok_sebelum
// 3. Update produk.stok = stok_baru
// 4. Insert stok_log:
//    tipe: selisih > 0 ? 'masuk' : 'keluar'
//    jumlah: abs(selisih)
//    stok_sebelum, stok_sesudah
//    alasan: user_input
```

---

## 📊 11. FITUR LENGKAP

### Core POS Features
| Fitur | Status | Keterangan |
|-------|--------|------------|
| Keranjang Belanja | ✅ | Add, edit qty, remove, clear |
| Diskon | ✅ | Persen atau nominal |
| Multi Metode Bayar | ✅ | Tunai, Transfer, QRIS, Piutang |
| Hitung Kembalian | ✅ | Otomatis |
| Struk Thermal | ✅ | 58mm & 80mm support |
| Print via Browser | ✅ | window.print() |
| Print via RawBT | ✅ | Android Bluetooth |
| Print via Serial | ✅ | Web Serial API |
| PDF Struk | ✅ | jsPDF |
| Share Digital | ✅ | WhatsApp, Telegram, Email, Download |

### Product Management
| Fitur | Status | Keterangan |
|-------|--------|------------|
| CRUD Produk | ✅ | Soft delete |
| Kategori | ✅ | Dynamic |
| Emoji Icon | ✅ | 151 emoji |
| Harga Modal (HPP) | ✅ | Untung/rugi |
| Stok Minimum | ✅ | Alert |
| Diskon per Item | ✅ | % |
| Barcode | ✅ | EAN13 & Code128 |

### Advanced Features
| Fitur | Status | Keterangan |
|-------|--------|------------|
| Void Transaksi | ✅ | Soft delete dengan restore stok |
| Restore Transaksi | ✅ | Batalkan void |
| Stok Log | ✅ | Track semua perubahan |
| Adjust Stok | ✅ | Manual dengan alasan |
| Piutang | ✅ | Cicilan dengan history |
| Tutup Kasir | ✅ | End-of-day dengan approval |
| Multi User | ✅ | Role-based access |
| Multi Tenant | ✅ | Multi toko |
| Superadmin Panel | ✅ | Ghost mode, audit logs |

### Reporting
| Fitur | Status | Keterangan |
|-------|--------|------------|
| Laporan Harian | ✅ | Omzet, transaksi, rata-rata |
| Laporan Rentang | ✅ | Custom date range |
| Top Produk | ✅ | By qty & omzet |
| Grafik | ✅ | Harian, Mingguan, Bulanan |
| Export CSV | ✅ | Transaksi & produk |
| Export PDF | ✅ | ReportLab |
| Stok Report | ✅ | Hampir habis, opname |

---

## 🔧 12. DEVELOPMENT NOTES

### Database Compatibility
- SQLite untuk development (file-based)
- PostgreSQL untuk production (auto-switch via env var)
- CursorWrapper untuk abstraksi placeholder (`?` vs `%s`)

### PostgreSQL vs SQLite Differences
```python
# SQLite
id INTEGER PRIMARY KEY AUTOINCREMENT
datetime('now', 'localtime')
?

# PostgreSQL  
id SERIAL PRIMARY KEY
CURRENT_TIMESTAMP
%s
```

### Important Indexes
```sql
CREATE INDEX idx_produk_kategori ON produk(kategori);
CREATE INDEX idx_produk_aktif ON produk(aktif);
CREATE INDEX idx_transaksi_waktu ON transaksi(waktu);
CREATE INDEX idx_transaksi_item_trxid ON transaksi_item(transaksi_id);
CREATE INDEX idx_piutang_bayar_trxid ON piutang_bayar(transaksi_id);
```

---

## 🆕 13. FITUR BARU (v2.1.2)

### Superadmin Reset Password Pemilik
- **Endpoint**: `POST /api/admin/owners/<owner_id>/reset-password`
- **Akses**: Superadmin only
- **Deskripsi**: Superadmin dapat mereset password pemilik jika lupa

### Emoji Produk Diperbanyak
- **Kategori Makanan**: +24 emoji baru (🦀🦞🦐🦑🦪 dll)
- **Kategori Minuman**: +14 emoji baru (🍼🍶🍻 dll)
- **Kategori Kebutuhan Rumah**: +14 emoji baru (🦷🧊🛒🧮 dll) - termasuk 🦷 untuk pasta gigi
- **Kategori Umum**: +50 emoji baru (📎✏️🔧💼📁 dll)

### Responsive Layout Full HD+
- Support layar 1080x2400 (20:9, 21:9)
- Viewport units: `dvh`, `vmin`, `-webkit-fill-available`
- Grid adaptif: 2→3→4 kolom berdasarkan lebar layar

### Superadmin Restriction
- Superadmin tidak bisa akses fitur transaksi (kasir, keranjang, piutang, tutup kasir)
- Hanya bisa akses Superadmin Panel (manajemen toko & pemilik)

---

## 🐛 14. BUG FIXES (v2.1.1)

### Critical Fixes

| Bug | Deskripsi | Fix |
|-----|-----------|-----|
| **#10** | Export PDF crash - `conn.close()` dipanggil sebelum loop selesai | Pindahkan `conn.close()` ke setelah loop |
| **#1** | Tutup Kasir tidak filter `store_id` | Tambahkan filter `store_id` di query |
| **#3** | Kas/Dompet tidak filter `store_id` | Tambahkan filter `store_id` di semua query kas |
| **#4** | Stok log tidak filter `store_id` | Tambahkan filter `store_id` dengan JOIN ke produk |
| **#5** | Laporan top produk tidak filter `store_id` | Tambahkan filter `store_id` di query |

### High Priority Fixes

| Bug | Deskripsi | Fix |
|-----|-----------|-----|
| **#16** | Typo alias di `laporan_keuangan()` - `DATE(waktu)` seharusnya `DATE(t.waktu)` | Perbaiki typo |
| **#7 & #8** | SQLite syntax `datetime('now','localtime')` hardcoded | Gunakan `CURRENT_TIMESTAMP` untuk PostgreSQL |
| **#9** | GROUP BY hilang di `get_pelanggan()` saat tanpa filter | Pindahkan GROUP BY ke luar blok if |
| **#12** | `tambah_pengguna()` tidak sync ke tabel `users` | Tambahkan insert ke `users` dan `user_stores` |
| **#11** | Filter `OR IS NULL` tidak efektif di `laporan_stok()` | Hapus `OR IS NULL`, gunakan filter langsung |

### Data Integrity Fixes

| Bug | Deskripsi | Fix |
|-----|-----------|-----|
| **#2** | `user_stores` kosong setelah migrasi | Tambahkan auto-assign karyawan ke toko di `migrate_multi_tenant()` |
| **Pelanggan** | Pelanggan tidak terfilter `store_id` | Tambahkan `store_id` ke semua query pelanggan |
| **Import CSV** | Import tidak filter `store_id` | Tambahkan filter dan insert dengan `store_id` |

### Additional Fixes (v2.1.1 Update)

| Bug | Deskripsi | Fix |
|-----|-----------|-----|
| **#3 (complete)** | Kas INSERT tanpa store_id | Tambahkan store_id ke INSERT kas di `buat_transaksi()`, `void_transaksi()`, `restore_transaksi()` |
| **#10 (complete)** | Export PDF conn.close() indentasi | Pindahkan conn.close() ke setelah detail_data selesai dibuat |
| **#13** | `restore_transaksi()` validasi stok | Cek stok tersedia sebelum restore, warning jika stok tidak cukup |
| **#14** | `no_trx` duplikat | Tambah suffix counter jika no_trx sudah ada |
| **#15** | Race condition `bayar_piutang()` | Gunakan `SELECT FOR UPDATE` (PostgreSQL) untuk row locking |
| **#17** | Double `@app.before_request` | Merge `require_login()` dan `ensure_db()` jadi satu handler |
| **#18 (complete)** | `hapus_pengguna` & `reset_password` tidak sync | Sync ke tabel `users` saat hapus/reset password |
| **#19** | `laporan_stok()` hitung di Python | Pindahkan perhitungan statistik ke SQL SUM |
| **#20** | Pengaturan tidak terisolasi per store | Tambah kolom `store_id` ke tabel pengaturan |

### Query yang Diperbarui dengan `store_id` Filter

```python
# Contoh pattern yang diterapkan ke semua endpoint:
def get_example():
    store_id = get_current_store_id()  # Ambil store aktif dari session
    conn = get_db()
    rows = db_execute(conn, 
        "SELECT * FROM tabel WHERE store_id = ?", 
        (store_id,)
    ).fetchall()
    conn.close()
    return jsonify(rows)
```

---

## 📞 15. DEFAULT LOGIN

| Username | Password | Role | Akses |
|----------|----------|------|-------|
| `superadmin` | `superadmin123` | Superadmin | Semua toko |
| `pemilik` | `pemilik123` | Pemilik | Toko sendiri |
| `karyawan` | `karyawan123` | Karyawan | Kasir only |

---

## 📄 16. LICENSE

MIT License - Bebas digunakan untuk personal maupun komersial.

---

**Dibuat dengan ❤️ untuk UMKM Indonesia**

*Dokumen ini terakhir diperbarui: 21 Maret 2026*

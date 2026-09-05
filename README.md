# 🏪 KasirToko

Aplikasi kasir (POS) untuk UMKM berbasis web — Python + Flask + SQLite/PostgreSQL.
Berjalan di Desktop, Tablet, dan HP (satu jaringan WiFi).

[![Version](https://img.shields.io/badge/version-v2.3.0-blue.svg)]()
[![Python](https://img.shields.io/badge/python-3.9+-green.svg)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-orange.svg)]()

> 📖 Dokumentasi teknis (arsitektur, database, API): **[TEKNIS.md](TEKNIS.md)**
> 📝 Riwayat perubahan: **[CHANGELOG.md](CHANGELOG.md)**

---

## ✨ Fitur

| Area | Isi |
|---|---|
| 🛒 Kasir | Keranjang, diskon persen/nominal, tunai/transfer/QRIS/piutang, kembalian otomatis, struk thermal 58/80mm |
| 📷 Barcode | Scan via kamera HP, generate + cetak label sheet PDF |
| 🗑️ Void & Restore | Batalkan transaksi dengan stok kembali otomatis (alasan wajib) |
| ⏳ Piutang | Cicilan anti-double-bayar (idempotency key) + pengingat jatuh tempo |
| 🔒 Tutup Kasir | Alur kasir → pending → konfirmasi pemilik → jurnal kas |
| 💰 Dompet | Pemasukan/pengeluaran manual, reset via jurnal penyeimbang (riwayat utuh) |
| 🧹 Reset Transaksi | Hapus riwayat + dompet per toko, produk & pelanggan aman, backup CSV otomatis |
| 📊 Laporan | Harian, grafik (Chart.js), top produk, stok, keuangan (laba kotor), export PDF/CSV |
| 👥 Multi-user & multi-toko | Superadmin, pemilik, karyawan; ghost mode read-only; audit log |

## 🛠️ Tech Stack

| Komponen | Teknologi |
|---|---|
| Backend | Flask 3.0, paket `kasirtoko/` (factory + 10 blueprint) |
| Database | SQLite (dev) / PostgreSQL (prod, auto-switch via env) |
| Frontend | Jinja2 + `static/css/app.css` + 6 modul `static/js/` + ikon Lucide (self-host, offline) |
| Test | pytest — `tests/` (16 test, lihat TEKNIS) |

## 🚀 Quick Start

```bash
pip install -r requirements.txt
python app.py
# Buka http://localhost:5000
# Dari HP (satu WiFi): pakai IP yang tampil di terminal
```

### 🔐 Login awal

| Username | Password | Peran |
|---|---|---|
| `superadmin` | `superadmin123` | Kelola toko & pemilik |
| `pemilik` | `pemilik123` | Akses penuh tokonya |
| `karyawan` | `karyawan123` | Kasir saja |

> ⚠️ Ganti password default setelah login pertama. Aplikasi memberi peringatan di log bila masih dipakai.

## 📁 Struktur

```
kasirtoko/
├── app.py                 # Pintu masuk: create_app() + run
├── api/index.py           # Entrypoint Vercel
├── kasirtoko/             # Backend: config, db, auth, models_init, routes/ (10 blueprint)
├── static/                # css/app.css, js/ (6 modul), vendor/lucide, sw.js, manifest, icons
├── templates/             # index.html, login.html, offline.html
├── tests/                 # pytest regression
├── deploy/                # deploy-vps.sh, nginx.conf
├── setup_postgres_schema.py | migrate_to_postgres.py
└── backups/               # Backup otomatis (reset transaksi, import mode ganti)
```

## 🧭 Panduan singkat

- **Jualan**: klik produk → atur qty → diskon (opsional) → metode bayar → BAYAR.
- **Salah input**: Riwayat → transaksi → ⋮ → Void (isi alasan) → stok kembali sendiri.
- **Hutang**: bayar pakai metode Piutang → lunasi via menu Piutang (bisa dicicil).
- **Tutup hari**: Tutup Kasir (kasir) → konfirmasi (pemilik) → masuk jurnal dompet.
- **Mulai data baru**: Riwayat → 🗑 Reset (pemilik) → ketik `RESET TRANSAKSI`. Produk & pelanggan tidak ikut terhapus; backup tersimpan di `backups/`.

## 🌐 Deploy

```bash
# Environment (salin dari .env.example)
SECRET_KEY=<min-32-karakter-acak>   # wajib di production
DATABASE_URL=postgresql://...       # wajib di Vercel/serverless
APP_URL=https://toko-anda.com       # untuk CORS
```

| Target | Cara |
|---|---|
| VPS Ubuntu | `bash deploy/deploy-vps.sh domain-anda.com` (Gunicorn + Nginx) |
| Vercel | `vercel --prod` (butuh Postgres — tanpa itu aplikasi menolak start) |
| Docker | — (belum disediakan; lihat TEKNIS bila ingin menambahkan) |

## ✅ Kesehatan

- `GET /api/health` → `{"ok": true, "db": "sqlite"/"postgres", "version": "2.3.0"}`
- Test: `python -m pytest tests/ -q` (16 test mencakup transaksi, void/restore, isolasi toko, piutang, kas, ghost mode, export, reset)

## 📄 Lisensi

MIT — bebas dipakai personal maupun komersial.

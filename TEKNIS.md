# 🔧 TEKNIS — KasirToko v2.3.0

Referensi teknis untuk developer: arsitektur, database, API, logika bisnis, testing, deploy.
Untuk pemakaian sehari-hari lihat [README.md](README.md). Riwayat versi: [CHANGELOG.md](CHANGELOG.md).

---

## 1. Arsitektur

Monolit Flask dengan application factory. `app.py` (38 baris) hanya memanggil `create_app()` —
seluruh logika tinggal di paket `kasirtoko/`. Frontend: 1 template + 1 CSS + 6 file JS global
(tanpa module system; urutan load: `api → pendukung → kasir → produk → transaksi → laporan`).

### Backend (`kasirtoko/`)

| File | Baris | Isi |
|---|---|---|
| `__init__.py` | 59 | `create_app()`: Flask + CORS + error handler + 10 blueprint + `init_db()` |
| `config.py` | 25 | Env (`SECRET_KEY`, `APP_URL`, DB URL), `DB_PATH`, `BACKUP_DIR`, batas upload 2 MB |
| `db.py` | 179 | Koneksi dual-DB, `CursorWrapper` (`?`→`%s` otomatis), `db_execute*`, `begin_tx`, `server_error` |
| `auth.py` | 205 | `get_current_user`, decorator (`login_required`, `pemilik_required`, `superadmin_required`, `require_store_access`, `no_ghost_write`), helper permission, rate-limit login |
| `models_init.py` | 807 | `init_db` (CREATE semua tabel + index), `migrate_multi_tenant`, seed, backfill `user_stores` |
| `routes/pages.py` | 267 | `/`, `/login`, `/logout`, `/sw.js`, `/offline`, `/api/health`, `require_login`, pengaturan toko |
| `routes/admin.py` | 424 | Superadmin (toko, pemilik, ghost mode, audit), assignment karyawan, switch toko |
| `routes/produk.py` | 580 | CRUD produk, scan, stok-rendah, adjust-stok, stok-history/log, import/export CSV |
| `routes/transaksi.py` | 607 | Buat/list/detail, void, restore, reset transaksi |
| `routes/piutang.py` | 274 | List, bayar cicilan (idempoten), history, reminder |
| `routes/kas.py` | 290 | Dompet, reset saldo, **tutup kasir** (preview, proses, riwayat, konfirmasi) |
| `routes/laporan.py` | 782 | Produk-terjual/top-produk, hari-ini/rentang/chart/stok/keuangan, export PDF/CSV |
| `routes/pelanggan.py` | 140 | CRUD + statistik belanja; hapus ditolak bila piutang aktif |
| `routes/pengguna.py` | 165 | Kelola tim (dual-tabel `pengguna`+`users`), reset & ganti password |
| `routes/struk.py` | 413 | Struk PNG, generate barcode, print-sheet PDF |

### Frontend (`static/` + `templates/index.html` 1.666 baris markup)

| File | Baris | Isi |
|---|---|---|
| `css/app.css` | 693 | Seluruh style incl. dark/light theme + media query mobile |
| `js/api.js` | 77 | Helper `api()`, state global, `init()`, jam |
| `js/pendukung.js` | 1.175 | Pengaturan, modal/toast, tema, nav, pelanggan, piutang, pengguna, superadmin, password |
| `js/kasir.js` | 1.062 | Cart, summary, metode bayar, proses transaksi, struk, share, print, scanner-call |
| `js/produk.js` | 1.044 | Tambah/edit/kelola, html5-qrcode scanner, import/export, barcode, stok-log, adjust |
| `js/transaksi.js` | 747 | Riwayat (lunas/belum), void/restore/reset, detail |
| `js/laporan.js` | 886 | Laporan, Chart.js, stok, keuangan, dompet, tutup kasir; `init()` dipanggil di akhir file |
| `vendor/lucide.min.js` | v0.469.0 | Ikon SVG self-host (offline-safe), render via `lucide.createIcons()` |

Catatan: `init()` sengaja dipanggil di akhir `laporan.js` (script terakhir) agar semua definisi sudah terparse.
Fungsi lintas-modul (`api`, `showToast`, `openM`, `fRp`, `showLoading`) adalah global window-scope.

---

## 2. Database

Dual-DB: SQLite (file `kasirtoko.db`, WAL + FK ON) untuk dev, PostgreSQL untuk production.
Deteksi via `POSTGRES_URL`/`DATABASE_URL`/`POSTGRES_PRISMA_URL`. Placeholder selalu ditulis `?`
(otomatis jadi `%s` di Postgres). Total **75 endpoint**, **14 tabel**:

| Tabel | Kunci |
|---|---|
| `produk` | id, nama, harga, stok, emoji, kategori, aktif, harga_modal, stok_min, diskon, barcode, store_id (+dibuat/diubah) |
| `transaksi` | id, no_trx UNIQUE, waktu, subtotal, diskon, diskon_val, diskon_tipe, total, bayar, kembalian, kasir, pelanggan_id, metode_bayar (tunai/transfer/qris/piutang), tutup_kasir_id, status (aktif/void), void_reason/by/at, is_lunas, terbayar, sisa_piutang, store_id |
| `transaksi_item` | transaksi_id→transaksi, produk_id, snapshot nama/emoji/harga, qty, subtotal |
| `pelanggan` | nama, telepon, alamat, catatan, store_id |
| `kas` | tipe (pemasukan/pengeluaran), jumlah, keterangan, metode, waktu, store_id |
| `tutup_kasir` | total + breakdown tunai/transfer/qris, jumlah_trx, status (pending/confirmed), dibuat_oleh, dikonfirmasi_oleh, store_id |
| `stok_log` | produk_id, tipe (masuk/keluar), jumlah, stok_sebelum/sesudah, alasan, transaksi_id, dibuat_oleh, store_id |
| `piutang_bayar` | transaksi_id, nominal, metode_bayar, catatan, dibuat_oleh, store_id, **idempotency_key** (UNIQUE per transaksi) |
| `users` / `pengguna` | Dual-tabel (modern + legacy, disinkron by username). `users`: role superadmin/pemilik/karyawan + is_superadmin |
| `stores` | name, slug UNIQUE, address, phone, email, owner_id→users, is_active |
| `user_stores` | user_id + store_id UNIQUE, role admin/kasir |
| `pengaturan` | PK komposit (kunci, store_id); store 0 = global |
| `admin_logs` | Jejak aksi superadmin (admin_id, store_id, action, target, old/new JSON, IP) |

Index: `produk(store_id,aktif)`, `produk(kategori)`, `transaksi(store_id,waktu)`, `transaksi(status)`,
`transaksi_item(transaksi_id)`, `stok_log(produk_id,waktu)`, `kas(store_id,waktu)`,
`piutang_bayar(transaksi_id)`, `pengaturan(store_id)`.

Skrip DB: `setup_postgres_schema.py` (schema penuh 14 tabel, idempoten — untuk DB fresh maupun lama),
`migrate_to_postgres.py` (pindah data SQLite→Postgres, toleran kolom baru, `ON CONFLICT DO NOTHING`).

---

## 3. API Reference (75 endpoint)

Format respons: sukses `{"ok": true, ...}` atau objek langsung; list `{"rows": [...], "stats": {...}}`;
error `{"error": "..."}` (500 selalu generik — detail hanya di log server).
Semua endpoint toko-scope memakai `store_id` dari session (`get_current_store_id()`).

| Modul | Endpoint | Akses |
|---|---|---|
| pages | `GET /`, `GET/POST /login`, `GET /logout`, `GET /sw.js`, `GET /offline`, `GET /api/health` | publik/health |
| pages | `GET /api/pengaturan`, `POST /api/pengaturan` | login / pemilik |
| admin | `GET+POST /api/admin/stores`, `PUT /api/admin/stores/<id>` | superadmin |
| admin | `GET+POST /api/admin/owners`, `POST /api/admin/owners/<id>/reset-password` | superadmin |
| admin | `POST /api/admin/enter-store/<id>` (ghost read-only), `POST /api/admin/exit-store`, `GET /api/admin/logs` | superadmin |
| admin | `GET+POST /api/stores/<id>/users`, `DELETE /api/stores/<id>/users/<uid>`, `GET /api/my-stores`, `POST /api/switch-store/<id>` | pemilik / login |
| produk | `GET+POST /api/produk`, `PUT+DELETE /api/produk/<id>`, `GET /api/produk/scan/<barcode>`, `GET /api/produk/stok-rendah`, `GET /api/produk/kategori` | login / pemilik(tulis) |
| produk | `POST /api/produk/<id>/adjust-stok`, `GET /api/produk/<id>/stok-history`, `GET /api/stok-log` | pemilik |
| produk | `GET /api/produk/export-csv` (+kolom barcode), `POST /api/produk/import-csv` (mode tambah/timpa/ganti; ganti wajib konfirmasi + auto-backup), `GET /api/produk/template-csv` | pemilik |
| transaksi | `POST /api/transaksi` (hitung ulang server), `GET /api/transaksi` (`dari/ke/status/limit/offset`), `GET /api/transaksi/<id>` | login |
| transaksi | `POST /api/transaksi/<id>/void` (alasan wajib), `POST /api/transaksi/<id>/restore` | pemilik |
| transaksi | `POST /api/transaksi/reset` (konfirmasi `RESET TRANSAKSI`; scope toko aktif; backup CSV otomatis) | pemilik |
| piutang | `GET /api/piutang`, `POST /api/piutang/<id>/bayar` (`idempotency_key`; 409 bila duplikat/overpay), `GET /api/piutang/<id>/history`, `GET /api/piutang/reminder` | login |
| kas | `GET+POST /api/kas`, `DELETE /api/kas/<id>`, `POST /api/kas/reset` (konfirmasi `Reset Saldo`; via jurnal penyeimbang) | pemilik |
| kas | `GET /api/tutup-kasir/preview`, `POST /api/tutup-kasir` (pending), `GET /api/tutup-kasir`, `POST /api/tutup-kasir/<id>/konfirmasi` | login buat / pemilik konfirmasi |
| laporan | `GET /api/laporan/produk-terjual`, `GET /api/laporan/top-produk`, `GET /api/laporan/hari-ini`, `GET /api/laporan/rentang`, `GET /api/laporan/chart` (harian/mingguan/bulanan), `GET /api/laporan/stok`, `GET /api/laporan/keuangan`, `GET /api/export/pdf`, `GET /api/export/csv` | pemilik |
| pelanggan | `GET+POST /api/pelanggan` (409 + daftar kandidat bila nama duplikat; `force:true` untuk paksa), `GET+PUT+DELETE /api/pelanggan/<id>` (hapus ditolak bila piutang aktif) | login |
| pengguna | `GET+POST /api/pengguna`, `DELETE /api/pengguna/<id>`, `POST /api/pengguna/<id>/reset-password`, `POST /api/pengguna/ganti-password` (sync kedua tabel) | pemilik / sendiri |
| struk | `GET /api/struk/<id>/image` (PNG 800px), `POST /api/barcode/generate`, `POST /api/barcode/print-sheet` | login / pemilik |

Bentuk objek (ringkas):

```json
// Transaksi
{"id":123,"no_trx":"TRX260321143052","waktu":"2026-03-21 14:30:52","subtotal":50000,
 "diskon":5000,"diskon_tipe":"persen","total":45000,"bayar":50000,"kembalian":5000,
 "kasir":"Kasir 1","metode_bayar":"tunai","status":"aktif","is_lunas":1,
 "items":[{"produk_id":5,"nama_produk":"Indomie Goreng","harga":3500,"qty":2,"subtotal":7000}]}
// Produk
{"id":5,"nama":"Indomie Goreng","harga":3500,"stok":100,"emoji":"🍜","kategori":"Makanan",
 "harga_modal":2500,"stok_min":10,"diskon":0,"barcode":"8999999999999"}
```

---

## 4. Logika Bisnis

- **Transaksi (`buat_transaksi`)**: subtotal/diskon/total/kembalian **dihitung ulang di server** dari harga DB
  (input client diabaikan); tolak produk beda toko, stok kurang, pelanggan beda toko, uang kurang;
  `kasir` = nama user; `no_trx` retry anti-duplikat; tulis `stok_log` keluar per item; `BEGIN IMMEDIATE`
  di SQLite. Piutang: `is_lunas=0`, `terbayar` = DP (dibatasi ≤ total), tanpa kembalian.
- **Kas single-source**: pemasukan kas **hanya** dicatat saat tutup kasir dikonfirmasi
  (bukan saat transaksi) — mencegah double-count di laporan keuangan. Pengecualian: pelunasan
  piutang dicatat saat bayar; void/restore menulis offset pengeluaran/pemasukan.
- **Void**: alasan wajib; tolak bila closing sudah confirmed; stok kembali + `stok_log` masuk.
  **Restore**: cek stok + cek closing confirmed; stok berkurang lagi.
- **Tutup kasir**: preview (belum bertutup) → proses (pending, `BEGIN IMMEDIATE` anti double-submit)
  → konfirmasi pemilik (jurnal kas per metode). Void/restore menolak transaksi yang closing-nya confirmed.
- **Piutang**: bayar dicek terhadap sisa (`nominal > sisa` → 400); `idempotency_key` UNIQUE per
  transaksi (double-klik → 409); frontend kirim key per klik + disable-after-click semantics.
- **Ghost mode**: superadmin `enter-store` → session `is_ghost_mode`; decorator `no_ghost_write`
  memblokir 7 endpoint tulis (403). Batasan kasir-superadmin juga ditegakkan di backend, bukan cuma UI.
- **Reset transaksi**: hapus transaksi/item/piutang-bayar/tutup-kasir/kas **satu toko**;
  produk, stok, pelanggan, pengguna utuh; backup 5 CSV ke `backups/reset-store{id}-{ts}-*.csv` dulu.
- **Pelanggan**: tambah nama kembar → 409 + kandidat (kasir pilih pakai yang ada atau `force:true`).

### Permission matrix

| Fitur | Superadmin | Pemilik | Karyawan |
|---|---|---|---|
| Kasir/transaksi, piutang bayar | ✗ (ghost read-only) | ✓ | ✓ |
| Kelola produk, adjust stok, stok-log | ✗ | ✓ | ✗ |
| Laporan, dompet, tutup-kasir konfirmasi, kelola tim | ✗ | ✓ | ✗ |
| Buat tutup-kasir (pending) | ✗ | ✓ | ✓ |
| Panel superadmin (toko, pemilik, audit) | ✓ | ✗ | ✗ |

### Keamanan

- Password `pbkdf2:sha256`; login dual-tabel (`users` dulu, fallback `pengguna`); ganti password sync by username.
- `SECRET_KEY` fail-fast di production; CORS dibatasi `APP_URL`; sesi permanen 30 hari; rate-limit login 10x/menit/IP (in-memory; reset tiap restart bila multi-worker — pertimbangkan Redis bila scale).
- Upload CSV ≤ 2 MB (413 JSON); error 500 generik; startup warning bila password default masih aktif.

---

## 5. Testing

```bash
python -m pytest tests/ -q   # 16 test: transaksi, validasi server, void/restore,
                              # isolasi toko, piutang idempoten, kas, pelanggan,
                              # ghost mode, export, reset transaksi
```

Test memakai DB lokal langsung (buat data dummy) — backup dulu bila produksi:
`copy kasirtoko.db kasirtoko.db.bak`, lalu bersihkan artefak dengan skrip cleanup internal
(hapus transaksi/kas/pelanggan/user pola-test, kembalikan stok, cek integrity).
Rate-limit di-reset per test via fixture (`kasirtoko.auth._login_attempts`).

## 6. Deploy & Operasional

```bash
SECRET_KEY=<32+ char acak>     # WAJIB production (fail-fast bila kosong)
DATABASE_URL=postgresql://...  # WAJIB di Vercel (SQLite ephemeral → ditolak start)
APP_URL=https://toko-anda.com  # origin CORS
FLASK_ENV=production
```

- **VPS**: `bash deploy/deploy-vps.sh domain` (Gunicorn + Nginx, lihat `deploy/`).
- **Vercel**: `vercel --prod`; `api/index.py` = `from app import app` (single source of truth).
- **Postgres fresh**: `DATABASE_URL=... python setup_postgres_schema.py` (14 tabel + index, idempoten);
  lalu `python migrate_to_postgres.py` untuk pindah data SQLite.
- **Health**: `GET /api/health` → db backend + versi (dipakai diagnosa).
- **PWA**: `sw.js` (bump `CACHE_NAME` tiap deploy frontend!), `manifest.json`, `offline.html`.
- **Backup**: folder `backups/` (reset transaksi, import mode `ganti`); DB SQLite WAL — backup saat idle.

## 7. Troubleshooting

| Gejala | Penyebab umum → aksi |
|---|---|
| 500 saat void/restore lama | Versi < v2.2.0 (`store_id` NameError) → update |
| Toko A lihat data toko B | Ada endpoint tanpa filter (v2.2.0 sudah menutup 11 endpoint) → cek `store_id` session |
| Omzet ganda di laporan | Kas dicatat 2x (bug pra-v2.2.0) → pastikan alur konfirmasi tutup-kasir tunggal |
| Password baru tak bisa login | Dual-tabel tak sinkron (v2.2.0 sudah sync by username) |
| 409 saat bayar piutang | Duplikat idempotency (klik ganda tertangani) atau nominal > sisa → refresh data |
| Import CSV ditolak | Cek header (nama,kategori,harga,stok), ukuran ≤ 2 MB, mode `ganti` butuh konfirmasi |
| Vercel error SQLite | `DATABASE_URL` belum diset → set Postgres URL |
| HP dapat UI basi | `CACHE_NAME` di `sw.js` belum di-bump saat deploy |

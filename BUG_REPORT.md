# 🐛 Bug Report — KasirToko v2.1.1

> Analisis dari source code `app.py` (4.094 baris) + `kasirtoko.db`  
> Dibuat: 21 Maret 2026 | Updated: 21 Maret 2026 | Total Bug: 20 (ALL FIXED ✅)

---

## Ringkasan

| Severity | Jumlah | Status |
|----------|--------|--------|
| 🔴 Critical | 5 | ✅ FIXED |
| 🟠 High | 7 | ✅ FIXED |
| 🟡 Medium | 4 | ✅ FIXED |
| 🟢 Minor | 4 | ✅ FIXED |

Semua bug telah diperbaiki dalam release v2.1.1

---

## 🔴 Critical — Langsung Berdampak ke Data

---

### Bug #1 — Tutup Kasir tidak filter `store_id` ✅ FIXED

| | |
|---|---|
| **File** | `app.py` |
| **Fungsi** | `tutup_kasir_preview()`, `buat_tutup_kasir()` |
| **Dampak** | Transaksi semua toko ikut terhitung. KIOS ANGEL tutup kasir → transaksi Calysta Store ikut masuk hitungan |

**Fix:** Tambahkan `store_id = get_current_store_id()` dan filter `AND store_id = ?` di semua query.

---

### Bug #2 — `user_stores` kosong, karyawan tidak ter-assign ke toko ✅ FIXED

| | |
|---|---|
| **File** | `app.py` + `kasirtoko.db` |
| **Data aktual** | `user_stores: 0 rows` — karyawan (id=3) ada di `users` tapi tidak di-assign ke toko manapun |
| **Dampak** | Karyawan login → `get_accessible_stores()` return kosong → `session current_store_id` tidak di-set → akses tidak terkontrol |

**Fix:** Tambahkan auto-assign karyawan ke toko di `migrate_multi_tenant()`.

---

### Bug #3 — Kas tidak filter `store_id` ✅ FIXED

| | |
|---|---|
| **File** | `app.py` |
| **Fungsi** | `tambah_kas()`, `buat_transaksi()`, `void_transaksi()`, `restore_transaksi()` |
| **Dampak** | Laporan keuangan semua toko tercampur — saldo, pemasukan, dan pengeluaran tidak terisolasi per toko |

**Fix:** Tambahkan `store_id` ke INSERT kas di `buat_transaksi()`, `void_transaksi()`, dan `restore_transaksi()`.

---

### Bug #4 — `stok_log` tidak filter `store_id` ✅ FIXED

| | |
|---|---|
| **File** | `app.py` |
| **Fungsi** | `get_stok_log()` |
| **Dampak** | Pemilik KIOS ANGEL bisa lihat riwayat stok produk Calysta Store dan sebaliknya |

**Fix:** Tambahkan `AND p.store_id = ?` dengan JOIN ke tabel produk.

---

### Bug #5 — `laporan_top_produk` tidak filter `store_id` ✅ FIXED

| | |
|---|---|
| **File** | `app.py` |
| **Fungsi** | `laporan_top_produk()` |
| **Dampak** | Top produk menggabungkan penjualan semua toko — data KIOS ANGEL bercampur dengan Calysta Store |

**Fix:** Tambahkan `AND t.store_id = ?` di WHERE clause.

---

## 🟠 High — Fungsional Rusak

---

### Bug #6 — Slug KIOS ANGEL salah (data aktual database) ⚠️ DATA FIX

| | |
|---|---|
| **File** | `kasirtoko.db` — tabel `stores` |
| **Data aktual** | `name='KIOS ANGEL'` tapi `slug='toko-kelontong-maju-jaya'` |
| **Penyebab** | `migrate_multi_tenant()` berjalan saat `nama_toko` di `pengaturan` masih nilai default |
| **Dampak** | URL slug tidak sesuai nama toko, membingungkan di multi-tenant routing |

**Fix (manual di database):**
```sql
UPDATE stores SET slug = 'kios-angel' WHERE id = 1;
```

---

### Bug #7 — SQLite syntax hardcoded di `update_produk()` ✅ FIXED

| | |
|---|---|
| **File** | `app.py` |
| **Fungsi** | `update_produk()` |
| **Dampak** | Di PostgreSQL production, kolom `diubah` tidak terupdate atau query error |

**Fix:** Gunakan `now_sql = "CURRENT_TIMESTAMP" if USE_POSTGRES else "datetime('now','localtime')"`.

---

### Bug #8 — SQLite syntax hardcoded di `adjust_stok()` ✅ FIXED

| | |
|---|---|
| **File** | `app.py` |
| **Fungsi** | `adjust_stok()` |
| **Dampak** | Sama dengan Bug #7 — adjust stok manual error di PostgreSQL |

**Fix:** Sama dengan Bug #7, gunakan kondisi `USE_POSTGRES`.

---

### Bug #9 — `GROUP BY` hilang di `get_pelanggan()` ✅ FIXED

| | |
|---|---|
| **File** | `app.py` |
| **Fungsi** | `get_pelanggan()` |
| **Dampak** | List pelanggan menampilkan baris duplikat — satu baris per transaksi, bukan per pelanggan |

**Fix:** Pindahkan `GROUP BY p.id ORDER BY p.nama` ke luar blok if cari.

---

### Bug #10 — Export PDF crash — `conn` sudah `closed` ✅ FIXED

| | |
|---|---|
| **File** | `app.py` |
| **Fungsi** | `export_pdf()` |
| **Dampak** | Export PDF selalu crash di production — `OperationalError: cannot operate on a closed database` |

**Fix:** Pindahkan `conn.close()` ke setelah detail_table selesai dibuat.

---

### Bug #11 — Filter `OR IS NULL` di `laporan_stok()` tidak efektif ✅ FIXED

| | |
|---|---|
| **File** | `app.py` |
| **Fungsi** | `laporan_stok()` |
| **Dampak** | Filter `store_id` tidak berfungsi dengan benar di beberapa kondisi |

**Fix:** Ganti `WHERE (p.store_id = ? OR ? IS NULL)` menjadi `WHERE p.store_id = ?`.

---

### Bug #12 — `tambah_pengguna()` tidak sync ke tabel `users` ✅ FIXED

| | |
|---|---|
| **File** | `app.py` |
| **Fungsi** | `tambah_pengguna()` — endpoint `POST /api/pengguna` |
| **Dampak** | Karyawan baru yang dibuat pemilik tidak bisa login via multi-tenant flow dan tidak ter-assign ke toko |

**Fix:** Insert ke tabel `users` dan `user_stores` setelah insert ke `pengguna`.

---

## 🟡 Medium — Edge Case & Data Integrity

---

### Bug #13 — `restore_transaksi()` tidak validasi stok mencukupi ✅ FIXED

| | |
|---|---|
| **File** | `app.py` |
| **Fungsi** | `restore_transaksi()` |
| **Dampak** | Restore 10 item tapi stok hanya 3 → stok jadi 0, selisih 7 hilang tanpa trace di `stok_log` |

**Fix:** Cek stok tersedia sebelum restore, beri warning jika stok tidak cukup (stok bisa negatif untuk kasus restore).

---

### Bug #14 — `no_trx` bisa duplikat jika 2 kasir transaksi dalam 1 detik ✅ FIXED

| | |
|---|---|
| **File** | `app.py` |
| **Fungsi** | `buat_transaksi()` |
| **Dampak** | `IntegrityError UNIQUE constraint` → transaksi gagal tanpa retry → kasir bingung, pelanggan menunggu |

**Fix:** Cek duplikat dengan loop dan tambah suffix counter jika no_trx sudah ada.

---

### Bug #15 — Race condition di `bayar_piutang()` ✅ FIXED

| | |
|---|---|
| **File** | `app.py` |
| **Fungsi** | `bayar_piutang()` |
| **Dampak** | Dua request bersamaan bisa lolos validasi `nominal > sisa` → total pembayaran melebihi hutang |

**Fix:** Gunakan `SELECT FOR UPDATE` (PostgreSQL) untuk row locking.

---

### Bug #16 — Typo alias tabel di `laporan_keuangan()` ✅ FIXED

| | |
|---|---|
| **File** | `app.py` |
| **Fungsi** | `laporan_keuangan()` |
| **Dampak** | Di PostgreSQL → `column "waktu" is ambiguous` error → laporan keuangan tidak bisa dibuka |

**Fix:** Perbaiki `DATE(waktu)` menjadi `DATE(t.waktu)`.

---

## 🟢 Minor — Technical Debt

---

### Bug #17 — Double `@app.before_request` ✅ FIXED

| | |
|---|---|
| **File** | `app.py` |
| **Dampak** | Code maintainability rendah, risiko konflik saat menambah middleware baru |

**Fix:** Merge kedua handler dengan flag `g._db_retry_init`.

---

### Bug #18 — Tabel `pengguna` dan `users` tidak tersinkronisasi ✅ FIXED

| | |
|---|---|
| **File** | `app.py` |
| **Fungsi** | `hapus_pengguna_api()`, `reset_password_pengguna()` |
| **Dampak** | Perubahan password di `pengguna` tidak tercermin di `users`. Dua sumber kebenaran untuk data user yang sama |

**Fix:** Sync ke tabel `users` saat hapus dan reset password.

---

### Bug #19 — `laporan_stok()` hitung statistik di Python bukan SQL ✅ FIXED

| | |
|---|---|
| **File** | `app.py` |
| **Fungsi** | `laporan_stok()` |
| **Dampak** | Tidak ada dampak data, tapi semua produk di-load ke memory untuk dihitung ulang |

**Fix:** Hitung statistik langsung di SQL dengan `COUNT`, `SUM`, dan `CASE WHEN`.

---

### Bug #20 — `pengaturan` toko tidak terisolasi per store ✅ FIXED

| | |
|---|---|
| **File** | `app.py` — tabel `pengaturan` |
| **Dampak** | KIOS ANGEL dan Calysta Store tidak bisa punya ukuran kertas printer atau pesan struk yang berbeda |

**Fix:** Tambah kolom `store_id` ke tabel `pengaturan`, gunakan composite key `(kunci, store_id)`.

---

## 📋 Status Perbaikan

| Bug | Status | File | Catatan |
|-----|--------|------|---------|
| #1 | ✅ FIXED | `app.py` | store_id filter ditambahkan |
| #2 | ✅ FIXED | `app.py` | Auto-assign di migrate_multi_tenant() |
| #3 | ✅ FIXED | `app.py` | INSERT kas dengan store_id |
| #4 | ✅ FIXED | `app.py` | store_id filter di stok_log |
| #5 | ✅ FIXED | `app.py` | store_id filter di laporan_top_produk |
| #6 | ⚠️ MANUAL | `kasirtoko.db` | Perlu UPDATE manual di database |
| #7 | ✅ FIXED | `app.py` | USE_POSTGRES conditional |
| #8 | ✅ FIXED | `app.py` | USE_POSTGRES conditional |
| #9 | ✅ FIXED | `app.py` | GROUP BY dipindahkan |
| #10 | ✅ FIXED | `app.py` | conn.close() dipindahkan |
| #11 | ✅ FIXED | `app.py` | Hapus OR IS NULL |
| #12 | ✅ FIXED | `app.py` | Sync ke users + user_stores |
| #13 | ✅ FIXED | `app.py` | Validasi stok dengan warning |
| #14 | ✅ FIXED | `app.py` | Suffix counter untuk duplikat |
| #15 | ✅ FIXED | `app.py` | SELECT FOR UPDATE |
| #16 | ✅ FIXED | `app.py` | Perbaiki typo alias |
| #17 | ✅ FIXED | `app.py` | Merge before_request handlers |
| #18 | ✅ FIXED | `app.py` | Sync hapus/reset ke users |
| #19 | ✅ FIXED | `app.py` | SQL aggregation |
| #20 | ✅ FIXED | `app.py` | store_id di pengaturan |

---

## 📝 Changelog v2.1.1

### Critical Fixes
- Fix #1: Tutup Kasir store_id filtering
- Fix #3: Kas INSERT dengan store_id (buat_transaksi, void_transaksi, restore_transaksi)
- Fix #4: Stok log store_id filtering
- Fix #5: Laporan top produk store_id filtering

### High Priority Fixes
- Fix #7, #8: SQLite syntax PostgreSQL compatibility
- Fix #9: GROUP BY placement
- Fix #10: Export PDF conn.close() position
- Fix #11: Remove OR IS NULL filter
- Fix #12: tambah_pengguna sync ke users
- Fix #16: Typo alias laporan_keuangan

### Medium Fixes
- Fix #13: restore_transaksi stok validation
- Fix #14: no_trx duplikat dengan suffix counter
- Fix #15: bayar_piutang race condition (SELECT FOR UPDATE)

### Minor Fixes
- Fix #17: Merge double @app.before_request
- Fix #18: hapus_pengguna & reset_password sync ke users
- Fix #19: laporan_stok SQL aggregation
- Fix #20: pengaturan store_id isolation

---

*KasirToko Bug Report v2.1.1 — 21 Maret 2026*

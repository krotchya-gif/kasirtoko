#!/usr/bin/env python3
"""
Setup schema LENGKAP PostgreSQL untuk KasirToko (P3-2).
Bisa dijalankan di database fresh maupun existing (idempoten:
CREATE IF NOT EXISTS + ADD COLUMN IF NOT EXISTS).

Run:  DATABASE_URL=postgresql://... python3 setup_postgres_schema.py
"""

import os
import sys

POSTGRES_URL = (
    os.environ.get('DATABASE_URL')
    or os.environ.get('POSTGRES_URL')
    or os.environ.get('POSTGRES_PRISMA_URL')
)


def get_connection():
    if not POSTGRES_URL:
        print("DATABASE_URL/POSTGRES_URL tidak ditemukan!")
        return None
    try:
        import psycopg2
        return psycopg2.connect(POSTGRES_URL)
    except Exception as e:
        print(f"Koneksi gagal: {e}")
        return None


TABLES = [
    ("users", """
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username TEXT NOT NULL UNIQUE,
            nama TEXT NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'karyawan' CHECK(role IN ('superadmin','pemilik','karyawan')),
            is_superadmin INTEGER NOT NULL DEFAULT 0,
            aktif INTEGER NOT NULL DEFAULT 1,
            dibuat TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """),
    ("pengguna", """
        CREATE TABLE IF NOT EXISTS pengguna (
            id SERIAL PRIMARY KEY,
            username TEXT NOT NULL UNIQUE,
            nama TEXT NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'karyawan' CHECK(role IN ('pemilik','karyawan')),
            aktif INTEGER NOT NULL DEFAULT 1,
            dibuat TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """),
    ("stores", """
        CREATE TABLE IF NOT EXISTS stores (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            slug TEXT NOT NULL UNIQUE,
            address TEXT,
            phone TEXT,
            email TEXT,
            owner_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            is_active INTEGER NOT NULL DEFAULT 1,
            dibuat TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """),
    ("user_stores", """
        CREATE TABLE IF NOT EXISTS user_stores (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            store_id INTEGER NOT NULL REFERENCES stores(id) ON DELETE CASCADE,
            role TEXT NOT NULL CHECK(role IN ('admin','kasir')),
            dibuat TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, store_id)
        )
    """),
    ("produk", """
        CREATE TABLE IF NOT EXISTS produk (
            id SERIAL PRIMARY KEY,
            nama TEXT NOT NULL,
            harga INTEGER NOT NULL DEFAULT 0,
            stok INTEGER NOT NULL DEFAULT 0,
            emoji TEXT NOT NULL DEFAULT '[BOX]',
            kategori TEXT NOT NULL DEFAULT 'Umum',
            aktif INTEGER NOT NULL DEFAULT 1,
            dibuat TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            diubah TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            harga_modal INTEGER DEFAULT 0,
            stok_min INTEGER DEFAULT 0,
            diskon INTEGER DEFAULT 0,
            barcode TEXT DEFAULT '',
            store_id INTEGER DEFAULT 1
        )
    """),
    ("pelanggan", """
        CREATE TABLE IF NOT EXISTS pelanggan (
            id SERIAL PRIMARY KEY,
            nama TEXT NOT NULL,
            telepon TEXT DEFAULT '',
            alamat TEXT DEFAULT '',
            catatan TEXT DEFAULT '',
            dibuat TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            store_id INTEGER DEFAULT 1
        )
    """),
    ("transaksi", """
        CREATE TABLE IF NOT EXISTS transaksi (
            id SERIAL PRIMARY KEY,
            no_trx TEXT NOT NULL UNIQUE,
            waktu TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            subtotal INTEGER NOT NULL DEFAULT 0,
            diskon INTEGER NOT NULL DEFAULT 0,
            diskon_val REAL NOT NULL DEFAULT 0,
            diskon_tipe TEXT NOT NULL DEFAULT 'persen',
            total INTEGER NOT NULL DEFAULT 0,
            bayar INTEGER NOT NULL DEFAULT 0,
            kembalian INTEGER NOT NULL DEFAULT 0,
            kasir TEXT DEFAULT 'Kasir 1',
            pelanggan_id INTEGER,
            metode_bayar TEXT DEFAULT 'tunai',
            tutup_kasir_id INTEGER DEFAULT NULL,
            status TEXT DEFAULT 'aktif',
            void_reason TEXT DEFAULT '',
            void_by TEXT DEFAULT '',
            void_at TEXT DEFAULT '',
            is_lunas INTEGER DEFAULT 1,
            terbayar INTEGER DEFAULT 0,
            sisa_piutang INTEGER DEFAULT 0,
            store_id INTEGER DEFAULT 1
        )
    """),
    ("transaksi_item", """
        CREATE TABLE IF NOT EXISTS transaksi_item (
            id SERIAL PRIMARY KEY,
            transaksi_id INTEGER NOT NULL REFERENCES transaksi(id) ON DELETE CASCADE,
            produk_id INTEGER NOT NULL,
            nama_produk TEXT NOT NULL,
            emoji TEXT DEFAULT '[BOX]',
            harga INTEGER NOT NULL,
            qty INTEGER NOT NULL,
            subtotal INTEGER NOT NULL
        )
    """),
    ("kas", """
        CREATE TABLE IF NOT EXISTS kas (
            id SERIAL PRIMARY KEY,
            tipe TEXT NOT NULL CHECK(tipe IN ('pemasukan','pengeluaran')),
            jumlah INTEGER NOT NULL,
            keterangan TEXT DEFAULT '',
            waktu TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            metode TEXT DEFAULT 'tunai',
            store_id INTEGER DEFAULT 1
        )
    """),
    ("tutup_kasir", """
        CREATE TABLE IF NOT EXISTS tutup_kasir (
            id SERIAL PRIMARY KEY,
            waktu TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            total INTEGER NOT NULL DEFAULT 0,
            total_tunai INTEGER NOT NULL DEFAULT 0,
            total_transfer INTEGER NOT NULL DEFAULT 0,
            total_qris INTEGER NOT NULL DEFAULT 0,
            jumlah_trx INTEGER NOT NULL DEFAULT 0,
            keterangan TEXT DEFAULT '',
            status TEXT DEFAULT 'pending' CHECK(status IN ('pending','confirmed')),
            dibuat_oleh TEXT DEFAULT '',
            dikonfirmasi_oleh TEXT DEFAULT '',
            waktu_konfirmasi TEXT DEFAULT '',
            store_id INTEGER DEFAULT 1
        )
    """),
    ("stok_log", """
        CREATE TABLE IF NOT EXISTS stok_log (
            id SERIAL PRIMARY KEY,
            produk_id INTEGER NOT NULL REFERENCES produk(id) ON DELETE CASCADE,
            tipe TEXT NOT NULL CHECK(tipe IN ('masuk','keluar','adjust')),
            jumlah INTEGER NOT NULL,
            stok_sebelum INTEGER NOT NULL,
            stok_sesudah INTEGER NOT NULL,
            alasan TEXT DEFAULT '',
            keterangan TEXT DEFAULT '',
            transaksi_id INTEGER DEFAULT NULL,
            dibuat_oleh TEXT DEFAULT '',
            waktu TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            store_id INTEGER DEFAULT 1
        )
    """),
    ("piutang_bayar", """
        CREATE TABLE IF NOT EXISTS piutang_bayar (
            id SERIAL PRIMARY KEY,
            transaksi_id INTEGER NOT NULL REFERENCES transaksi(id) ON DELETE CASCADE,
            nominal INTEGER NOT NULL DEFAULT 0,
            metode_bayar TEXT NOT NULL DEFAULT 'tunai',
            catatan TEXT DEFAULT '',
            dibuat_oleh TEXT DEFAULT '',
            waktu TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            store_id INTEGER DEFAULT 1,
            idempotency_key TEXT DEFAULT ''
        )
    """),
    ("pengaturan", """
        CREATE TABLE IF NOT EXISTS pengaturan (
            kunci TEXT NOT NULL,
            nilai TEXT NOT NULL,
            store_id INTEGER REFERENCES stores(id) ON DELETE CASCADE,
            PRIMARY KEY (kunci, COALESCE(store_id, 0))
        )
    """),
    ("admin_logs", """
        CREATE TABLE IF NOT EXISTS admin_logs (
            id SERIAL PRIMARY KEY,
            admin_id INTEGER NOT NULL REFERENCES users(id),
            store_id INTEGER REFERENCES stores(id),
            action_type TEXT NOT NULL,
            target_table TEXT,
            target_id INTEGER,
            old_value TEXT,
            new_value TEXT,
            ip_address TEXT,
            dibuat TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """),
]

# Kolom yang mungkin belum ada di DB lama (migrasi dari versi awal).
# Format: (tabel, kolom, definisi)
EXTRA_COLUMNS = [
    ("produk", "harga_modal", "INTEGER DEFAULT 0"),
    ("produk", "stok_min", "INTEGER DEFAULT 0"),
    ("produk", "diskon", "INTEGER DEFAULT 0"),
    ("produk", "barcode", "TEXT DEFAULT ''"),
    ("produk", "store_id", "INTEGER DEFAULT 1"),
    ("transaksi", "pelanggan_id", "INTEGER"),
    ("transaksi", "metode_bayar", "TEXT DEFAULT 'tunai'"),
    ("transaksi", "tutup_kasir_id", "INTEGER DEFAULT NULL"),
    ("transaksi", "status", "TEXT DEFAULT 'aktif'"),
    ("transaksi", "void_reason", "TEXT DEFAULT ''"),
    ("transaksi", "void_by", "TEXT DEFAULT ''"),
    ("transaksi", "void_at", "TEXT DEFAULT ''"),
    ("transaksi", "is_lunas", "INTEGER DEFAULT 1"),
    ("transaksi", "terbayar", "INTEGER DEFAULT 0"),
    ("transaksi", "sisa_piutang", "INTEGER DEFAULT 0"),
    ("transaksi", "store_id", "INTEGER DEFAULT 1"),
    ("kas", "metode", "TEXT DEFAULT 'tunai'"),
    ("kas", "store_id", "INTEGER DEFAULT 1"),
    ("pelanggan", "store_id", "INTEGER DEFAULT 1"),
    ("tutup_kasir", "store_id", "INTEGER DEFAULT 1"),
    ("stok_log", "store_id", "INTEGER DEFAULT 1"),
    ("piutang_bayar", "store_id", "INTEGER DEFAULT 1"),
    ("piutang_bayar", "idempotency_key", "TEXT DEFAULT ''"),
]

INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_produk_store_aktif ON produk(store_id, aktif)",
    "CREATE INDEX IF NOT EXISTS idx_produk_kategori ON produk(kategori)",
    "CREATE INDEX IF NOT EXISTS idx_produk_aktif ON produk(aktif)",
    "CREATE INDEX IF NOT EXISTS idx_transaksi_store_waktu ON transaksi(store_id, waktu)",
    "CREATE INDEX IF NOT EXISTS idx_transaksi_waktu ON transaksi(waktu)",
    "CREATE INDEX IF NOT EXISTS idx_transaksi_status ON transaksi(status)",
    "CREATE INDEX IF NOT EXISTS idx_transaksi_item_trxid ON transaksi_item(transaksi_id)",
    "CREATE INDEX IF NOT EXISTS idx_stoklog_produk_waktu ON stok_log(produk_id, waktu)",
    "CREATE INDEX IF NOT EXISTS idx_kas_store_waktu ON kas(store_id, waktu)",
    "CREATE INDEX IF NOT EXISTS idx_piutang_bayar_trxid ON piutang_bayar(transaksi_id)",
    "CREATE INDEX IF NOT EXISTS idx_piutang_bayar_store ON piutang_bayar(store_id)",
    "CREATE UNIQUE INDEX IF NOT EXISTS idx_piutang_bayar_idem ON piutang_bayar(transaksi_id, idempotency_key) WHERE idempotency_key <> ''",
    "CREATE INDEX IF NOT EXISTS idx_pengaturan_store ON pengaturan(store_id)",
]


def main():
    conn = get_connection()
    if not conn:
        return
    cur = conn.cursor()
    try:
        print("Setting up PostgreSQL schema (full)...")
        for name, ddl in TABLES:
            cur.execute(ddl)
            print(f"  [OK] table: {name}")

        print("\nMigrasi kolom (DB lama)...")
        for table, col, defi in EXTRA_COLUMNS:
            try:
                cur.execute(
                    f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {col} {defi}"
                )
            except Exception as e:
                print(f"  [WARN] {table}.{col}: {e}")

        print("\nIndex...")
        for stmt in INDEXES:
            try:
                cur.execute(stmt)
            except Exception as e:
                print(f"  [WARN] index: {e}")
        print("  [OK] indexes")

        conn.commit()
        print("\n" + "=" * 50)
        print("Schema setup completed!")
        print("=" * 50)
    except Exception as e:
        conn.rollback()
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()


if __name__ == '__main__':
    main()

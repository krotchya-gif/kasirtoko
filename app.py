"""
KasirToko — Backend Flask + SQLite/PostgreSQL
Jalankan: python app.py
Buka browser: http://localhost:5000
"""

import functools
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from flask import Flask, request, jsonify, render_template, send_file, session, redirect
from flask_cors import CORS
import os
import json
import csv
import io

# Database configuration - PostgreSQL for Vercel, SQLite for local
POSTGRES_URL = os.environ.get('POSTGRES_URL') or os.environ.get('DATABASE_URL') or os.environ.get('POSTGRES_PRISMA_URL')
USE_POSTGRES = bool(POSTGRES_URL)

if USE_POSTGRES:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    print(f"Using PostgreSQL database")
else:
    import sqlite3
    print(f"Using SQLite database")


app = Flask(__name__)
CORS(app)

# Session — ganti SECRET_KEY di environment saat production
app.secret_key = os.environ.get('SECRET_KEY', 'kasirtoko-dev-secret-2024-change-in-prod')
app.permanent_session_lifetime = timedelta(days=30)

DB_PATH = os.path.join(os.path.dirname(__file__), 'kasirtoko.db')

def get_db_connection():
    """Get database connection based on environment"""
    if USE_POSTGRES:
        conn = psycopg2.connect(POSTGRES_URL)
        return conn
    else:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

def get_db_cursor(conn):
    """Get cursor with proper configuration for database type"""
    if USE_POSTGRES:
        cur = conn.cursor(cursor_factory=RealDictCursor)
    else:
        cur = conn.cursor()
    return CursorWrapper(cur)

def qmark(sql):
    """Convert SQL placeholders for current database type.
    SQLite uses ?, PostgreSQL uses %s"""
    if USE_POSTGRES:
        # Replace ? with %s
        return sql.replace('?', '%s')
    return sql

class CursorWrapper:
    """Wrapper untuk cursor yang otomatis konversi placeholder"""
    def __init__(self, cursor):
        self.cursor = cursor
    
    def execute(self, sql, params=None):
        sql = qmark(sql)
        if params is None:
            return self.cursor.execute(sql)
        return self.cursor.execute(sql, params)
    
    def executemany(self, sql, params_list):
        sql = qmark(sql)
        return self.cursor.executemany(sql, params_list)
    
    def fetchone(self):
        row = self.cursor.fetchone()
        if row is None:
            return None
        if USE_POSTGRES:
            return dict(row) if hasattr(row, 'keys') else row
        return dict(row)
    
    def fetchall(self):
        rows = self.cursor.fetchall()
        if USE_POSTGRES:
            return [dict(r) if hasattr(r, 'keys') else r for r in rows]
        return [dict(r) for r in rows]
    
    def __getattr__(self, name):
        return getattr(self.cursor, name)


def db_execute(conn, sql, params=None):
    """Execute SQL and return a cursor wrapper for fetching"""
    c = get_db_cursor(conn)
    c.execute(sql, params)
    return c


def db_execute_many(conn, sql, params_list):
    """Execute many SQL statements"""
    c = get_db_cursor(conn)
    c.executemany(sql, params_list)
    return c


def db_execute_insert(conn, sql, params=None):
    """Execute INSERT and return lastrowid (works for both SQLite and PostgreSQL)"""
    c = get_db_cursor(conn)
    
    if USE_POSTGRES:
        # Add RETURNING id if not present
        if 'RETURNING' not in sql.upper():
            sql = sql.rstrip(';') + ' RETURNING id'
        c.execute(sql, params)
        row = c.fetchone()
        c.lastrowid = row['id'] if row else None
        return c
    else:
        c.execute(sql, params)
        return c

# ─────────────────────────────────────
#  DATABASE INIT
# ─────────────────────────────────────
def get_db():
    return get_db_connection()

def init_db():
    conn = get_db()
    c = get_db_cursor(conn)

    # Tabel produk
    if USE_POSTGRES:
        c.execute("""
            CREATE TABLE IF NOT EXISTS produk (
                id        SERIAL PRIMARY KEY,
                nama      TEXT    NOT NULL,
                harga     INTEGER NOT NULL DEFAULT 0,
                stok      INTEGER NOT NULL DEFAULT 0,
                emoji     TEXT    NOT NULL DEFAULT '[BOX]',
                kategori  TEXT    NOT NULL DEFAULT 'Umum',
                aktif     INTEGER NOT NULL DEFAULT 1,
                dibuat    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                diubah    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    else:
        c.execute("""
            CREATE TABLE IF NOT EXISTS produk (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                nama      TEXT    NOT NULL,
                harga     INTEGER NOT NULL DEFAULT 0,
                stok      INTEGER NOT NULL DEFAULT 0,
                emoji     TEXT    NOT NULL DEFAULT '[BOX]',
                kategori  TEXT    NOT NULL DEFAULT 'Umum',
                aktif     INTEGER NOT NULL DEFAULT 1,
                dibuat    TEXT    DEFAULT (datetime('now','localtime')),
                diubah    TEXT    DEFAULT (datetime('now','localtime'))
            )
        """)

    # Tabel transaksi header
    if USE_POSTGRES:
        c.execute("""
            CREATE TABLE IF NOT EXISTS transaksi (
                id         SERIAL PRIMARY KEY,
                no_trx     TEXT    NOT NULL UNIQUE,
                waktu      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                subtotal   INTEGER NOT NULL DEFAULT 0,
                diskon     INTEGER NOT NULL DEFAULT 0,
                diskon_val REAL    NOT NULL DEFAULT 0,
                diskon_tipe TEXT   NOT NULL DEFAULT 'persen',
                total      INTEGER NOT NULL DEFAULT 0,
                bayar      INTEGER NOT NULL DEFAULT 0,
                kembalian  INTEGER NOT NULL DEFAULT 0,
                kasir      TEXT    DEFAULT 'Kasir 1'
            )
        """)
    else:
        c.execute("""
            CREATE TABLE IF NOT EXISTS transaksi (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                no_trx     TEXT    NOT NULL UNIQUE,
                waktu      TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
                subtotal   INTEGER NOT NULL DEFAULT 0,
                diskon     INTEGER NOT NULL DEFAULT 0,
                diskon_val REAL    NOT NULL DEFAULT 0,
                diskon_tipe TEXT   NOT NULL DEFAULT 'persen',
                total      INTEGER NOT NULL DEFAULT 0,
                bayar      INTEGER NOT NULL DEFAULT 0,
                kembalian  INTEGER NOT NULL DEFAULT 0,
                kasir      TEXT    DEFAULT 'Kasir 1'
            )
        """)

    # Tabel detail transaksi
    if USE_POSTGRES:
        c.execute("""
            CREATE TABLE IF NOT EXISTS transaksi_item (
                id           SERIAL PRIMARY KEY,
                transaksi_id INTEGER NOT NULL,
                produk_id    INTEGER NOT NULL,
                nama_produk  TEXT    NOT NULL,
                emoji        TEXT    DEFAULT '[BOX]',
                harga        INTEGER NOT NULL,
                qty          INTEGER NOT NULL,
                subtotal     INTEGER NOT NULL,
                FOREIGN KEY (transaksi_id) REFERENCES transaksi(id) ON DELETE CASCADE
            )
        """)
    else:
        c.execute("""
            CREATE TABLE IF NOT EXISTS transaksi_item (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                transaksi_id INTEGER NOT NULL,
                produk_id    INTEGER NOT NULL,
                nama_produk  TEXT    NOT NULL,
                emoji        TEXT    DEFAULT '[BOX]',
                harga        INTEGER NOT NULL,
                qty          INTEGER NOT NULL,
                subtotal     INTEGER NOT NULL,
                FOREIGN KEY (transaksi_id) REFERENCES transaksi(id) ON DELETE CASCADE
            )
        """)

    # Tabel kas (dompet / arus kas manual)
    if USE_POSTGRES:
        c.execute("""
            CREATE TABLE IF NOT EXISTS kas (
                id         SERIAL PRIMARY KEY,
                tipe       TEXT    NOT NULL CHECK(tipe IN ('pemasukan','pengeluaran')),
                jumlah     INTEGER NOT NULL,
                keterangan TEXT    DEFAULT '',
                waktu      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    else:
        c.execute("""
            CREATE TABLE IF NOT EXISTS kas (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                tipe       TEXT    NOT NULL CHECK(tipe IN ('pemasukan','pengeluaran')),
                jumlah     INTEGER NOT NULL,
                keterangan TEXT    DEFAULT '',
                waktu      TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
            )
        """)

    # Tabel pelanggan
    if USE_POSTGRES:
        c.execute("""
            CREATE TABLE IF NOT EXISTS pelanggan (
                id       SERIAL PRIMARY KEY,
                nama     TEXT    NOT NULL,
                telepon  TEXT    DEFAULT '',
                alamat   TEXT    DEFAULT '',
                catatan  TEXT    DEFAULT '',
                dibuat   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    else:
        c.execute("""
            CREATE TABLE IF NOT EXISTS pelanggan (
                id       INTEGER PRIMARY KEY AUTOINCREMENT,
                nama     TEXT    NOT NULL,
                telepon  TEXT    DEFAULT '',
                alamat   TEXT    DEFAULT '',
                catatan  TEXT    DEFAULT '',
                dibuat   TEXT    DEFAULT (datetime('now','localtime'))
            )
        """)

    # Tambah kolom lanjutan ke produk (backward-compatible)
    for col_sql in [
        "ALTER TABLE produk ADD COLUMN harga_modal INTEGER DEFAULT 0",
        "ALTER TABLE produk ADD COLUMN stok_min    INTEGER DEFAULT 0",
        "ALTER TABLE produk ADD COLUMN diskon      INTEGER DEFAULT 0",
        "ALTER TABLE produk ADD COLUMN barcode     TEXT    DEFAULT ''",
    ]:
        try:
            c.execute(col_sql)
        except Exception:
            pass

    # Tambah metode ke kas (backward-compatible)
    try:
        c.execute("ALTER TABLE kas ADD COLUMN metode TEXT DEFAULT 'tunai'")
    except Exception:
        pass  # kolom sudah ada

    # Tambah pelanggan_id ke transaksi (backward-compatible)
    try:
        c.execute("ALTER TABLE transaksi ADD COLUMN pelanggan_id INTEGER")
    except Exception:
        pass  # kolom sudah ada

    # Tambah metode_bayar & tutup_kasir_id ke transaksi (backward-compatible)
    for col_sql in [
        "ALTER TABLE transaksi ADD COLUMN metode_bayar TEXT DEFAULT 'tunai'",
        "ALTER TABLE transaksi ADD COLUMN tutup_kasir_id INTEGER DEFAULT NULL",
    ]:
        try:
            c.execute(col_sql)
        except Exception:
            pass

    # Tambah kolom status void ke transaksi (backward-compatible)
    for col_sql in [
        "ALTER TABLE transaksi ADD COLUMN status TEXT DEFAULT 'aktif'",
        "ALTER TABLE transaksi ADD COLUMN void_reason TEXT DEFAULT ''",
        "ALTER TABLE transaksi ADD COLUMN void_by TEXT DEFAULT ''",
        "ALTER TABLE transaksi ADD COLUMN void_at TEXT DEFAULT ''",
    ]:
        try:
            c.execute(col_sql)
        except Exception:
            pass

    # Tambah kolom piutang ke transaksi (backward-compatible)
    for col_sql in [
        "ALTER TABLE transaksi ADD COLUMN is_lunas INTEGER DEFAULT 1",  # 1=lunas, 0=belum/belum lunas
        "ALTER TABLE transaksi ADD COLUMN terbayar INTEGER DEFAULT 0",  # jumlah sudah dibayar
        "ALTER TABLE transaksi ADD COLUMN sisa_piutang INTEGER DEFAULT 0",  # sisa yang harus dibayar
    ]:
        try:
            c.execute(col_sql)
        except Exception:
            pass

    # Tabel stok_log untuk riwayat perubahan stok
    if USE_POSTGRES:
        c.execute("""
            CREATE TABLE IF NOT EXISTS stok_log (
                id           SERIAL PRIMARY KEY,
                produk_id    INTEGER NOT NULL,
                tipe         TEXT    NOT NULL CHECK(tipe IN ('masuk','keluar','adjust')),
                jumlah       INTEGER NOT NULL,
                stok_sebelum INTEGER NOT NULL,
                stok_sesudah INTEGER NOT NULL,
                alasan       TEXT    DEFAULT '',
                keterangan   TEXT    DEFAULT '',
                transaksi_id INTEGER DEFAULT NULL,
                dibuat_oleh  TEXT    DEFAULT '',
                waktu        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (produk_id) REFERENCES produk(id) ON DELETE CASCADE
            )
        """)
    else:
        c.execute("""
            CREATE TABLE IF NOT EXISTS stok_log (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                produk_id    INTEGER NOT NULL,
                tipe         TEXT    NOT NULL CHECK(tipe IN ('masuk','keluar','adjust')),
                jumlah       INTEGER NOT NULL,
                stok_sebelum INTEGER NOT NULL,
                stok_sesudah INTEGER NOT NULL,
                alasan       TEXT    DEFAULT '',
                keterangan   TEXT    DEFAULT '',
                transaksi_id INTEGER DEFAULT NULL,
                dibuat_oleh  TEXT    DEFAULT '',
                waktu        TEXT    DEFAULT (datetime('now','localtime')),
                FOREIGN KEY (produk_id) REFERENCES produk(id) ON DELETE CASCADE
            )
        """)

    # Tabel tutup_kasir (end-of-day closing)
    if USE_POSTGRES:
        c.execute("""
            CREATE TABLE IF NOT EXISTS tutup_kasir (
                id                SERIAL PRIMARY KEY,
                waktu             TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                total             INTEGER NOT NULL DEFAULT 0,
                total_tunai       INTEGER NOT NULL DEFAULT 0,
                total_transfer    INTEGER NOT NULL DEFAULT 0,
                total_qris        INTEGER NOT NULL DEFAULT 0,
                jumlah_trx        INTEGER NOT NULL DEFAULT 0,
                keterangan        TEXT    DEFAULT '',
                status            TEXT    DEFAULT 'pending' CHECK(status IN ('pending','confirmed')),
                dibuat_oleh       TEXT    DEFAULT '',
                dikonfirmasi_oleh TEXT    DEFAULT '',
                waktu_konfirmasi  TEXT    DEFAULT ''
            )
        """)
    else:
        c.execute("""
            CREATE TABLE IF NOT EXISTS tutup_kasir (
                id                INTEGER PRIMARY KEY AUTOINCREMENT,
                waktu             TEXT    DEFAULT (datetime('now','localtime')),
                total             INTEGER NOT NULL DEFAULT 0,
                total_tunai       INTEGER NOT NULL DEFAULT 0,
                total_transfer    INTEGER NOT NULL DEFAULT 0,
                total_qris        INTEGER NOT NULL DEFAULT 0,
                jumlah_trx        INTEGER NOT NULL DEFAULT 0,
                keterangan        TEXT    DEFAULT '',
                status            TEXT    DEFAULT 'pending' CHECK(status IN ('pending','confirmed')),
                dibuat_oleh       TEXT    DEFAULT '',
                dikonfirmasi_oleh TEXT    DEFAULT '',
                waktu_konfirmasi  TEXT    DEFAULT ''
            )
        """)

    # ═════════════════════════════════════
    #  MULTI-TENANT TABLES
    # ═════════════════════════════════════
    
    # Tabel users (multi-role: superadmin, pemilik, karyawan)
    if USE_POSTGRES:
        c.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id            SERIAL PRIMARY KEY,
                username      TEXT    NOT NULL UNIQUE,
                nama          TEXT    NOT NULL,
                password      TEXT    NOT NULL,
                role          TEXT    NOT NULL DEFAULT 'karyawan' CHECK(role IN ('superadmin','pemilik','karyawan')),
                is_superadmin INTEGER NOT NULL DEFAULT 0,
                aktif         INTEGER NOT NULL DEFAULT 1,
                dibuat        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    else:
        c.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                username      TEXT    NOT NULL UNIQUE COLLATE NOCASE,
                nama          TEXT    NOT NULL,
                password      TEXT    NOT NULL,
                role          TEXT    NOT NULL DEFAULT 'karyawan' CHECK(role IN ('superadmin','pemilik','karyawan')),
                is_superadmin INTEGER NOT NULL DEFAULT 0,
                aktif         INTEGER NOT NULL DEFAULT 1,
                dibuat        TEXT    DEFAULT (datetime('now','localtime'))
            )
        """)

    # Tabel stores (toko/cabang)
    if USE_POSTGRES:
        c.execute("""
            CREATE TABLE IF NOT EXISTS stores (
                id          SERIAL PRIMARY KEY,
                name        TEXT    NOT NULL,
                slug        TEXT    NOT NULL UNIQUE,
                address     TEXT,
                phone       TEXT,
                email       TEXT,
                owner_id    INTEGER NOT NULL,
                is_active   INTEGER NOT NULL DEFAULT 1,
                dibuat      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)
    else:
        c.execute("""
            CREATE TABLE IF NOT EXISTS stores (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT    NOT NULL,
                slug        TEXT    NOT NULL UNIQUE COLLATE NOCASE,
                address     TEXT,
                phone       TEXT,
                email       TEXT,
                owner_id    INTEGER NOT NULL,
                is_active   INTEGER NOT NULL DEFAULT 1,
                dibuat      TEXT    DEFAULT (datetime('now','localtime')),
                FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)

    # Tabel user_stores (relasi karyawan ke toko)
    if USE_POSTGRES:
        c.execute("""
            CREATE TABLE IF NOT EXISTS user_stores (
                id          SERIAL PRIMARY KEY,
                user_id     INTEGER NOT NULL,
                store_id    INTEGER NOT NULL,
                role        TEXT    NOT NULL CHECK(role IN ('admin','kasir')),
                dibuat      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (store_id) REFERENCES stores(id) ON DELETE CASCADE,
                UNIQUE(user_id, store_id)
            )
        """)
    else:
        c.execute("""
            CREATE TABLE IF NOT EXISTS user_stores (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL,
                store_id    INTEGER NOT NULL,
                role        TEXT    NOT NULL CHECK(role IN ('admin','kasir')),
                dibuat      TEXT    DEFAULT (datetime('now','localtime')),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (store_id) REFERENCES stores(id) ON DELETE CASCADE,
                UNIQUE(user_id, store_id)
            )
        """)

    # Tabel admin_logs (audit trail superadmin)
    if USE_POSTGRES:
        c.execute("""
            CREATE TABLE IF NOT EXISTS admin_logs (
                id           SERIAL PRIMARY KEY,
                admin_id     INTEGER NOT NULL,
                store_id     INTEGER,
                action_type  TEXT    NOT NULL,
                target_table TEXT,
                target_id    INTEGER,
                old_value    TEXT,
                new_value    TEXT,
                ip_address   TEXT,
                dibuat       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (admin_id) REFERENCES users(id),
                FOREIGN KEY (store_id) REFERENCES stores(id)
            )
        """)
    else:
        c.execute("""
            CREATE TABLE IF NOT EXISTS admin_logs (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                admin_id     INTEGER NOT NULL,
                store_id     INTEGER,
                action_type  TEXT    NOT NULL,
                target_table TEXT,
                target_id    INTEGER,
                old_value    TEXT,
                new_value    TEXT,
                ip_address   TEXT,
                dibuat       TEXT    DEFAULT (datetime('now','localtime')),
                FOREIGN KEY (admin_id) REFERENCES users(id),
                FOREIGN KEY (store_id) REFERENCES stores(id)
            )
        """)

    # Tabel pengguna (LEGACY - backward compatibility)
    if USE_POSTGRES:
        c.execute("""
            CREATE TABLE IF NOT EXISTS pengguna (
                id       SERIAL PRIMARY KEY,
                username TEXT    NOT NULL UNIQUE,
                nama     TEXT    NOT NULL,
                password TEXT    NOT NULL,
                role     TEXT    NOT NULL DEFAULT 'karyawan' CHECK(role IN ('pemilik','karyawan')),
                aktif    INTEGER NOT NULL DEFAULT 1,
                dibuat   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    else:
        c.execute("""
            CREATE TABLE IF NOT EXISTS pengguna (
                id       INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT    NOT NULL UNIQUE COLLATE NOCASE,
                nama     TEXT    NOT NULL,
                password TEXT    NOT NULL,
                role     TEXT    NOT NULL DEFAULT 'karyawan' CHECK(role IN ('pemilik','karyawan')),
                aktif    INTEGER NOT NULL DEFAULT 1,
                dibuat   TEXT    DEFAULT (datetime('now','localtime'))
            )
        """)

    # Seed akun default jika tabel pengguna masih kosong
    c.execute("SELECT COUNT(*) as count FROM pengguna")
    result = c.fetchone()
    count = result['count'] if result else 0
    if count == 0:
        # Gunakan pbkdf2:sha256 agar kompatibel dengan Python 3.9 / OpenSSL lama
        _hash = lambda pw: generate_password_hash(pw, method='pbkdf2:sha256')
        c.executemany(
            "INSERT INTO pengguna (username, nama, password, role) VALUES (?,?,?,?)",
            [
                ('pemilik',  'Pemilik Toko', _hash('pemilik123'),  'pemilik'),
                ('karyawan', 'Karyawan',     _hash('karyawan123'), 'karyawan'),
            ]
        )
        print("[OK] Akun default dibuat: pemilik/pemilik123  dan  karyawan/karyawan123")

    # Tabel pengaturan toko (key-value) dengan store_id isolation
    if USE_POSTGRES:
        c.execute("""
            CREATE TABLE IF NOT EXISTS pengaturan (
                kunci TEXT NOT NULL,
                nilai TEXT NOT NULL,
                store_id INTEGER REFERENCES stores(id) ON DELETE CASCADE,
                PRIMARY KEY (kunci, COALESCE(store_id, 0))
            )
        """)
    else:
        c.execute("""
            CREATE TABLE IF NOT EXISTS pengaturan (
                kunci TEXT NOT NULL,
                nilai TEXT NOT NULL,
                store_id INTEGER REFERENCES stores(id) ON DELETE CASCADE,
                PRIMARY KEY (kunci)
            )
        """)
        # Tambahkan index untuk SQLite
        c.execute("CREATE INDEX IF NOT EXISTS idx_pengaturan_store ON pengaturan(store_id)")
    
    # Create indexes for PostgreSQL performance
    if USE_POSTGRES:
        c.execute("CREATE INDEX IF NOT EXISTS idx_produk_kategori ON produk(kategori)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_produk_aktif ON produk(aktif)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_transaksi_waktu ON transaksi(waktu)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_transaksi_item_trxid ON transaksi_item(transaksi_id)")

    # Insert default pengaturan jika belum ada (global settings, store_id=NULL)
    defaults = [
        ('nama_toko',  'TOKO KELONTONG MAJU JAYA'),
        ('alamat',     'Jl. Raya No. 1'),
        ('telp',       '0812-xxxx-xxxx'),
        ('pesan_struk','Terima kasih sudah berbelanja!'),
        ('ukuran_kertas', '58'),
        ('printer_app_scheme', 'rawbt'),
        ('printer_app_name', 'RawBT'),
    ]
    for k, v in defaults:
        if USE_POSTGRES:
            c.execute("INSERT INTO pengaturan (kunci, nilai, store_id) VALUES (?, ?, NULL) ON CONFLICT (kunci) DO NOTHING", (k, v))
        else:
            c.execute("INSERT OR IGNORE INTO pengaturan (kunci, nilai, store_id) VALUES (?, ?, NULL)", (k, v))

    # Insert produk default jika tabel kosong
    c.execute("SELECT COUNT(*) as count FROM produk")
    result = c.fetchone()
    count = result['count'] if result else 0
    if count == 0:
        produk_default = [
            ('Aqua 600ml',       4000,  50, '💧', 'Minuman'),
            ('Teh Botol Sosro',  5500,  30, '🧋', 'Minuman'),
            ('Coca-Cola 330ml',  7000,  24, '🥤', 'Minuman'),
            ('Indomilk 250ml',   5000,  15, '🥛', 'Minuman'),
            ('Kopi Sachet',      2500, 100, '☕', 'Minuman'),
            ('Indomie Goreng',   3500,  80, '🍜', 'Makanan'),
            ('Roti Tawar',      12000,  10, '🍞', 'Makanan'),
            ('Biscuit Roma',     8000,  40, '🍪', 'Makanan'),
            ('Wafer Tango',      5000,  35, '🧇', 'Makanan'),
            ('Keripik Kentang', 10000,  20, '🥔', 'Makanan'),
            ('Gula 1kg',        14000,  25, '🍬', 'Sembako'),
            ('Minyak Goreng 1L',18000,  18, '🫙', 'Sembako'),
            ('Beras 1kg',       13000,  60, '🌾', 'Sembako'),
            ('Tepung Terigu 1kg',10000, 30, '🌾', 'Sembako'),
            ('Garam 250gr',      3000,  50, '🧂', 'Sembako'),
            ('Sabun Lifebuoy',   5000,  30, '🧼', 'Kebersihan'),
            ('Sampo Sachet',     1500,  60, '🧴', 'Kebersihan'),
            ('Pasta Gigi 75gr',  9000,  25, '🪥', 'Kebersihan'),
            ('Tisu 1 Pack',      8000,  40, '🧻', 'Kebersihan'),
        ]
        c.executemany(
            "INSERT INTO produk (nama, harga, stok, emoji, kategori) VALUES (?,?,?,?,?)",
            produk_default
        )

    # ═════════════════════════════════════
    #  MULTI-TENANT MIGRATION
    # ═════════════════════════════════════
    migrate_multi_tenant(c, USE_POSTGRES)

    # ═════════════════════════════════════
    #  TABEL PIUTANG BAYAR (CICILAN)
    # ═════════════════════════════════════
    if USE_POSTGRES:
        c.execute("""
            CREATE TABLE IF NOT EXISTS piutang_bayar (
                id             SERIAL PRIMARY KEY,
                transaksi_id   INTEGER NOT NULL,
                nominal        INTEGER NOT NULL DEFAULT 0,
                metode_bayar   TEXT    NOT NULL DEFAULT 'tunai',
                catatan        TEXT    DEFAULT '',
                dibuat_oleh    TEXT    DEFAULT '',
                waktu          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                store_id       INTEGER DEFAULT 1,
                FOREIGN KEY (transaksi_id) REFERENCES transaksi(id) ON DELETE CASCADE
            )
        """)
    else:
        c.execute("""
            CREATE TABLE IF NOT EXISTS piutang_bayar (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                transaksi_id   INTEGER NOT NULL,
                nominal        INTEGER NOT NULL DEFAULT 0,
                metode_bayar   TEXT    NOT NULL DEFAULT 'tunai',
                catatan        TEXT    DEFAULT '',
                dibuat_oleh    TEXT    DEFAULT '',
                waktu          TEXT    DEFAULT (datetime('now','localtime')),
                store_id       INTEGER DEFAULT 1,
                FOREIGN KEY (transaksi_id) REFERENCES transaksi(id) ON DELETE CASCADE
            )
        """)
    
    # Index untuk performa
    c.execute("CREATE INDEX IF NOT EXISTS idx_piutang_bayar_trxid ON piutang_bayar(transaksi_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_piutang_bayar_store ON piutang_bayar(store_id)")

    conn.commit()
    conn.close()
    print(f"[OK] Database siap: {DB_PATH}")


def migrate_multi_tenant(c, use_postgres):
    """Migrasi data existing ke multi-tenant schema"""
    
    # 1. Cek apakah sudah ada superadmin
    c.execute("SELECT COUNT(*) as count FROM users WHERE is_superadmin = 1")
    has_superadmin = c.fetchone()['count'] > 0
    
    if not has_superadmin:
        # Buat superadmin default
        _hash = lambda pw: generate_password_hash(pw, method='pbkdf2:sha256')
        c.execute(
            "INSERT INTO users (username, nama, password, role, is_superadmin) VALUES (?,?,?,?,?)",
            ('superadmin', 'Super Administrator', _hash('superadmin123'), 'superadmin', 1)
        )
        print("[OK] Superadmin dibuat: superadmin/superadmin123")
    
    # 2. Migrasi pengguna lama ke users (jika belum)
    c.execute("SELECT COUNT(*) as count FROM users WHERE role = 'pemilik'")
    has_pemilik = c.fetchone()['count'] > 0
    
    if not has_pemilik:
        # Copy data dari pengguna ke users
        c.execute("SELECT * FROM pengguna WHERE role = 'pemilik'")
        pemilik_rows = c.fetchall()
        for row in pemilik_rows:
            try:
                c.execute(
                    "INSERT INTO users (username, nama, password, role, is_superadmin) VALUES (?,?,?,?,?)",
                    (row['username'], row['nama'], row['password'], 'pemilik', 0)
                )
            except Exception:
                pass  # Skip jika username sudah ada
        
        # Copy karyawan
        c.execute("SELECT * FROM pengguna WHERE role = 'karyawan'")
        karyawan_rows = c.fetchall()
        for row in karyawan_rows:
            try:
                c.execute(
                    "INSERT INTO users (username, nama, password, role, is_superadmin) VALUES (?,?,?,?,?)",
                    (row['username'], row['nama'], row['password'], 'karyawan', 0)
                )
            except Exception:
                pass
        print("[OK] Data pengguna dimigrasi ke users")
    
    # 3. Buat toko dari pengaturan (jika belum ada toko)
    c.execute("SELECT COUNT(*) as count FROM stores")
    has_stores = c.fetchone()['count'] > 0
    
    if not has_stores:
        # Ambil data pengaturan
        c.execute("SELECT nilai FROM pengaturan WHERE kunci = 'nama_toko'")
        result = c.fetchone()
        nama_toko = result['nilai'] if result else 'Toko Saya'
        
        c.execute("SELECT nilai FROM pengaturan WHERE kunci = 'alamat'")
        result = c.fetchone()
        alamat = result['nilai'] if result else ''
        
        c.execute("SELECT nilai FROM pengaturan WHERE kunci = 'telp'")
        result = c.fetchone()
        telp = result['nilai'] if result else ''
        
        # Buat slug dari nama toko
        import re
        slug = re.sub(r'[^\w\s-]', '', nama_toko).strip().lower()
        slug = re.sub(r'[-\s]+', '-', slug)[:50]
        if not slug:
            slug = 'toko-saya'
        
        # Ambil pemilik pertama
        c.execute("SELECT id FROM users WHERE role = 'pemilik' ORDER BY id LIMIT 1")
        pemilik = c.fetchone()
        owner_id = pemilik['id'] if pemilik else 1
        
        try:
            c.execute(
                "INSERT INTO stores (name, slug, address, phone, owner_id) VALUES (?,?,?,?,?)",
                (nama_toko, slug, alamat, telp, owner_id)
            )
            print(f"[OK] Toko '{nama_toko}' dibuat dengan slug '{slug}'")
        except Exception as e:
            # Jika slug sudah ada, tambahkan angka
            slug = f"{slug}-1"
            c.execute(
                "INSERT INTO stores (name, slug, address, phone, owner_id) VALUES (?,?,?,?,?)",
                (nama_toko, slug, alamat, telp, owner_id)
            )
            print(f"[OK] Toko '{nama_toko}' dibuat dengan slug '{slug}'")
    
    # 4. Tambah kolom store_id ke tabel existing (jika belum)
    tables_to_update = ['produk', 'transaksi', 'kas', 'pelanggan', 'stok_log', 'tutup_kasir']
    
    for table in tables_to_update:
        try:
            if use_postgres:
                c.execute(f"ALTER TABLE {table} ADD COLUMN store_id INTEGER DEFAULT 1")
            else:
                c.execute(f"ALTER TABLE {table} ADD COLUMN store_id INTEGER DEFAULT 1")
        except Exception:
            pass  # Kolom sudah ada
    
    # 5. Update semua data existing dengan store_id = 1
    for table in tables_to_update:
        try:
            c.execute(f"UPDATE {table} SET store_id = 1 WHERE store_id IS NULL")
        except Exception:
            pass
    
    # 5b. Migrasi tabel pengaturan - tambah store_id jika belum ada
    try:
        if use_postgres:
            c.execute("ALTER TABLE pengaturan ADD COLUMN store_id INTEGER REFERENCES stores(id) ON DELETE CASCADE")
            # Buat ulang primary key untuk support composite
            c.execute("ALTER TABLE pengaturan DROP CONSTRAINT IF EXISTS pengaturan_pkey")
            c.execute("ALTER TABLE pengaturan ADD PRIMARY KEY (kunci, COALESCE(store_id, 0))")
        else:
            c.execute("ALTER TABLE pengaturan ADD COLUMN store_id INTEGER REFERENCES stores(id) ON DELETE CASCADE")
            c.execute("CREATE INDEX IF NOT EXISTS idx_pengaturan_store ON pengaturan(store_id)")
    except Exception:
        pass  # Kolom sudah ada atau error lain
    
    # 6. Assign karyawan ke toko (jika belum ada di user_stores)
    c.execute("SELECT COUNT(*) as count FROM user_stores")
    has_user_stores = c.fetchone()['count'] > 0
    
    if not has_user_stores:
        # Assign semua karyawan ke toko 1
        c.execute("""
            INSERT INTO user_stores (user_id, store_id, role)
            SELECT id, 1, 'kasir' FROM users
            WHERE role = 'karyawan'
            ON CONFLICT (user_id, store_id) DO NOTHING
        """)
        print("[OK] Karyawan di-assign ke toko")
    
    print("[OK] Data existing diupdate dengan store_id = 1")


# ─────────────────────────────────────
#  HELPER
# ─────────────────────────────────────
def row_to_dict(row):
    if row is None:
        return None
    if USE_POSTGRES:
        return dict(row) if hasattr(row, 'keys') else row
    return dict(row)

def rows_to_list(rows):
    if rows is None:
        return []
    if USE_POSTGRES:
        return [dict(r) if hasattr(r, 'keys') else r for r in rows]
    return [dict(r) for r in rows]

def fetchone_as_dict(cursor):
    """Fetch one row and convert to dict"""
    if USE_POSTGRES:
        row = cursor.fetchone()
        if row is None:
            return None
        return {desc[0]: val for desc, val in zip(cursor.description, row)}
    else:
        row = cursor.fetchone()
        return dict(row) if row else None

def fetchall_as_list(cursor):
    """Fetch all rows and convert to list of dicts"""
    if USE_POSTGRES:
        rows = cursor.fetchall()
        if not rows:
            return []
        cols = [desc[0] for desc in cursor.description]
        return [dict(zip(cols, row)) for row in rows]
    else:
        rows = cursor.fetchall()
        return [dict(r) for r in rows]


# ─────────────────────────────────────
#  AUTH
# ─────────────────────────────────────
def get_current_user():
    """Ambil data user dari session. Return None jika tidak login atau sesi invalid."""
    uid = session.get('user_id')
    if not uid:
        return None
    conn = get_db()
    # Coba dari tabel users (new) dulu
    user = db_execute(conn, 
        "SELECT id, username, nama, role, is_superadmin FROM users WHERE id=? AND aktif=1", (uid,)
    ).fetchone()
    # Fallback ke pengguna (legacy)
    if not user:
        user = db_execute(conn, 
            "SELECT id, username, nama, role, 0 as is_superadmin FROM pengguna WHERE id=? AND aktif=1", (uid,)
        ).fetchone()
    conn.close()
    return row_to_dict(user) if user else None


def login_required(f):
    """Decorator untuk endpoint yang memerlukan login."""
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        if not get_current_user():
            return jsonify({'error': 'Unauthorized - Silakan login terlebih dahulu'}), 401
        return f(*args, **kwargs)
    return decorated_function


def get_current_store_id():
    """Ambil store_id aktif dari session. Default 1 untuk backward compatibility."""
    return session.get('current_store_id', 1)


# ═════════════════════════════════════
#  PERMISSION HELPERS (MULTI-TENANT)
# ═════════════════════════════════════
def is_superadmin(user_id=None):
    """Cek apakah user adalah superadmin."""
    if user_id is None:
        user = get_current_user()
        if not user:
            return False
        user_id = user['id']
    conn = get_db()
    result = db_execute(conn, 
        "SELECT is_superadmin FROM users WHERE id = ?", (user_id,)
    ).fetchone()
    conn.close()
    return result and result['is_superadmin'] == 1


def is_store_owner(user_id, store_id):
    """Cek apakah user adalah owner dari toko tertentu."""
    conn = get_db()
    result = db_execute(conn,
        "SELECT 1 FROM stores WHERE id = ? AND owner_id = ?",
        (store_id, user_id)
    ).fetchone()
    conn.close()
    return result is not None


def can_access_store(user_id, store_id):
    """Cek apakah user bisa akses toko (superadmin, owner, atau assigned)."""
    if is_superadmin(user_id):
        return True
    if is_store_owner(user_id, store_id):
        return True
    
    conn = get_db()
    result = db_execute(conn,
        "SELECT 1 FROM user_stores WHERE user_id = ? AND store_id = ?",
        (user_id, store_id)
    ).fetchone()
    conn.close()
    return result is not None


def can_manage_products(user_id, store_id):
    """Cek apakah user bisa manage produk (superadmin, owner, atau admin)."""
    if is_superadmin(user_id):
        return True
    if is_store_owner(user_id, store_id):
        return True
    
    conn = get_db()
    result = db_execute(conn,
        "SELECT role FROM user_stores WHERE user_id = ? AND store_id = ?",
        (user_id, store_id)
    ).fetchone()
    conn.close()
    return result and result['role'] == 'admin'


def get_accessible_stores(user_id):
    """List semua toko yang bisa diakses user."""
    conn = get_db()
    if is_superadmin(user_id):
        stores = rows_to_list(db_execute(conn, 
            "SELECT * FROM stores WHERE is_active = 1 ORDER BY name"
        ).fetchall())
    else:
        stores = rows_to_list(db_execute(conn,"""
            SELECT DISTINCT s.* FROM stores s
            LEFT JOIN user_stores us ON s.id = us.store_id
            WHERE s.is_active = 1 
              AND (s.owner_id = ? OR us.user_id = ?)
            ORDER BY s.name
        """, (user_id, user_id)).fetchall())
    conn.close()
    return stores


def log_admin_action(admin_id, store_id, action_type, target_table=None, target_id=None, old_value=None, new_value=None):
    """Catat action superadmin untuk audit trail."""
    conn = get_db()
    try:
        db_execute(conn, """
            INSERT INTO admin_logs (admin_id, store_id, action_type, target_table, target_id, old_value, new_value, ip_address)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (admin_id, store_id, action_type, target_table, target_id, 
              json.dumps(old_value) if old_value else None,
              json.dumps(new_value) if new_value else None,
              request.remote_addr))
        conn.commit()
    except Exception:
        pass
    conn.close()


# ═════════════════════════════════════
#  DECORATORS
# ═════════════════════════════════════
def pemilik_required(f):
    """Decorator: hanya pemilik atau superadmin yang bisa akses."""
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        user = get_current_user()
        if not user:
            return jsonify({'error': 'Sesi berakhir. Silakan login kembali.'}), 401
        if user.get('is_superadmin') == 1 or user.get('role') in ('superadmin', 'pemilik'):
            return f(*args, **kwargs)
        return jsonify({'error': 'Akses ditolak — hanya untuk Pemilik Toko'}), 403
    return decorated


def superadmin_required(f):
    """Decorator: hanya superadmin yang bisa akses."""
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        user = get_current_user()
        if not user or user.get('is_superadmin') != 1:
            return jsonify({'error': 'Akses ditolak — hanya untuk Superadmin'}), 403
        return f(*args, **kwargs)
    return decorated


def require_store_access(f):
    """Decorator: cek apakah user bisa akses store_id di session."""
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        user = get_current_user()
        if not user:
            return jsonify({'error': 'Sesi berakhir. Silakan login kembali.'}), 401
        store_id = session.get('current_store_id', 1)
        if not can_access_store(user['id'], store_id):
            return jsonify({'error': 'Akses ditolak — Anda tidak memiliki akses ke toko ini'}), 403
        return f(*args, **kwargs)
    return decorated


@app.before_request
def require_login():
    """Semua route wajib login + ensure_db retry. Kecuali /login, /logout, /offline, /static/, /sw.js"""
    # 1. Ensure DB init retry jika sebelumnya gagal
    if '_db_init_error' in globals():
        try:
            init_db()
            print("[OK] Database initialized (retry)")
            del globals()['_db_init_error']
        except Exception as e:
            print(f"[ERR] Database init failed again: {e}")
    
    # 2. Login check
    public_paths = {'/login', '/logout', '/offline', '/sw.js'}
    if request.path in public_paths or request.path.startswith('/static/'):
        return None
    if not session.get('user_id'):
        if request.path.startswith('/api/'):
            return jsonify({'error': 'Sesi berakhir. Silakan login kembali.', 'needLogin': True}), 401
        return redirect('/login')


# ─────────────────────────────────────
#  HALAMAN UTAMA & PWA
# ─────────────────────────────────────
@app.route('/')
def index():
    user = get_current_user()
    # Get user's stores for the switcher
    stores = []
    if user:
        stores = get_accessible_stores(user['id'])
    return render_template('index.html', user=user, stores=stores)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('user_id') and get_current_user():
        return redirect('/')
    error = None
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        conn = get_db()
        # Coba login ke tabel users (new) dulu
        if USE_POSTGRES:
            user = db_execute(conn, 
                "SELECT * FROM users WHERE username ILIKE %s AND aktif=1",
                (username,)
            ).fetchone()
        else:
            user = db_execute(conn, 
                "SELECT * FROM users WHERE username=? COLLATE NOCASE AND aktif=1",
                (username,)
            ).fetchone()
        # Fallback ke pengguna (legacy)
        if not user:
            if USE_POSTGRES:
                user = db_execute(conn, 
                    "SELECT * FROM pengguna WHERE username ILIKE %s AND aktif=1",
                    (username,)
                ).fetchone()
            else:
                user = db_execute(conn, 
                    "SELECT * FROM pengguna WHERE username=? COLLATE NOCASE AND aktif=1",
                    (username,)
                ).fetchone()
        conn.close()
        if user and check_password_hash(user['password'], password):
            session.clear()
            session['user_id'] = user['id']
            session.permanent = True
            # Set default store untuk pemilik/karyawan
            if user.get('is_superadmin') != 1 and user.get('role') != 'superadmin':
                conn = get_db()
                # Ambil toko pertama yang bisa diakses
                stores = get_accessible_stores(user['id'])
                if stores:
                    session['current_store_id'] = stores[0]['id']
                conn.close()
            return redirect('/')
        error = 'Username atau password salah.'
    return render_template('login.html', error=error)


@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

@app.route('/sw.js')
def service_worker():
    """Service worker harus diakses dari root agar scope-nya '/'"""
    from flask import send_from_directory
    return send_from_directory('static', 'sw.js',
                               mimetype='application/javascript')

@app.route('/offline')
def offline():
    return render_template('offline.html')


# ═════════════════════════════════════
#  API: SUPERADMIN (MULTI-TENANT)
# ═════════════════════════════════════

@app.route('/api/admin/stores', methods=['GET'])
@superadmin_required
def admin_list_stores():
    """List semua toko untuk superadmin."""
    conn = get_db()
    stores = rows_to_list(db_execute(conn, """
        SELECT s.*, u.nama as owner_name, u.username as owner_username,
               (SELECT COUNT(*) FROM produk WHERE store_id = s.id) as product_count,
               (SELECT COUNT(*) FROM transaksi WHERE store_id = s.id) as transaction_count
        FROM stores s
        LEFT JOIN users u ON s.owner_id = u.id
        ORDER BY s.dibuat DESC
    """).fetchall())
    conn.close()
    return jsonify(stores)


@app.route('/api/admin/stores', methods=['POST'])
@superadmin_required
def admin_create_store():
    """Buat toko baru dan assign pemilik."""
    data = request.json
    name = data.get('name', '').strip()
    owner_id = data.get('owner_id')
    address = data.get('address', '').strip()
    phone = data.get('phone', '').strip()
    
    if not name:
        return jsonify({'error': 'Nama toko wajib diisi'}), 400
    if not owner_id:
        return jsonify({'error': 'Pemilik toko wajib dipilih'}), 400
    
    # Buat slug
    import re
    slug = re.sub(r'[^\w\s-]', '', name).strip().lower()
    slug = re.sub(r'[-\s]+', '-', slug)[:50]
    
    conn = get_db()
    try:
        # Cek apakah owner valid
        owner = db_execute(conn, "SELECT id FROM users WHERE id = ? AND role = 'pemilik'", (owner_id,)).fetchone()
        if not owner:
            conn.close()
            return jsonify({'error': 'Pemilik tidak valid'}), 400
        
        # Insert toko
        cur = db_execute_insert(conn,
            "INSERT INTO stores (name, slug, address, phone, owner_id) VALUES (?,?,?,?,?)",
            (name, slug, address, phone, owner_id)
        )
        store_id = cur.lastrowid
        
        # Log action
        log_admin_action(session['user_id'], store_id, 'create_store', 'stores', store_id, None, {'name': name, 'owner_id': owner_id})
        
        conn.commit()
        conn.close()
        return jsonify({'ok': True, 'store_id': store_id, 'slug': slug}), 201
    except Exception as e:
        conn.rollback()
        conn.close()
        return jsonify({'error': str(e)}), 500


@app.route('/api/admin/owners', methods=['POST'])
@superadmin_required
def admin_create_owner():
    """Buat akun pemilik baru."""
    data = request.json
    username = data.get('username', '').strip().lower()
    nama = data.get('nama', '').strip()
    password = data.get('password', '')
    
    if not username or not nama or not password:
        return jsonify({'error': 'Username, nama, dan password wajib diisi'}), 400
    
    if len(password) < 6:
        return jsonify({'error': 'Password minimal 6 karakter'}), 400
    
    conn = get_db()
    try:
        # Cek username sudah ada
        existing = db_execute(conn, "SELECT 1 FROM users WHERE username = ?", (username,)).fetchone()
        if existing:
            conn.close()
            return jsonify({'error': 'Username sudah digunakan'}), 400
        
        # Insert pemilik
        _hash = generate_password_hash(password, method='pbkdf2:sha256')
        cur = db_execute_insert(conn,
            "INSERT INTO users (username, nama, password, role, is_superadmin) VALUES (?,?,?,?,?)",
            (username, nama, _hash, 'pemilik', 0)
        )
        user_id = cur.lastrowid
        
        # Log action
        log_admin_action(session['user_id'], None, 'create_owner', 'users', user_id, None, {'username': username, 'nama': nama})
        
        conn.commit()
        conn.close()
        return jsonify({'ok': True, 'user_id': user_id}), 201
    except Exception as e:
        conn.rollback()
        conn.close()
        return jsonify({'error': str(e)}), 500


@app.route('/api/admin/owners', methods=['GET'])
@superadmin_required
def admin_list_owners():
    """List semua pemilik yang belum punya toko atau semua pemilik."""
    conn = get_db()
    owners = rows_to_list(db_execute(conn, """
        SELECT u.*, 
               (SELECT COUNT(*) FROM stores WHERE owner_id = u.id) as store_count
        FROM users u
        WHERE u.role = 'pemilik'
        ORDER BY u.dibuat DESC
    """).fetchall())
    conn.close()
    return jsonify(owners)


@app.route('/api/admin/enter-store/<int:store_id>', methods=['POST'])
@superadmin_required
def admin_enter_store(store_id):
    """Superadmin masuk ke toko tertentu (ghost mode)."""
    conn = get_db()
    store = db_execute(conn, "SELECT * FROM stores WHERE id = ? AND is_active = 1", (store_id,)).fetchone()
    conn.close()
    
    if not store:
        return jsonify({'error': 'Toko tidak ditemukan'}), 404
    
    session['current_store_id'] = store_id
    session['is_ghost_mode'] = True
    
    # Log action
    log_admin_action(session['user_id'], store_id, 'enter_store', None, None, None, {'ghost_mode': True})
    
    return jsonify({'ok': True, 'store': row_to_dict(store)})


@app.route('/api/admin/exit-store', methods=['POST'])
@superadmin_required
def admin_exit_store():
    """Superadmin keluar dari ghost mode."""
    store_id = session.get('current_store_id')
    session.pop('current_store_id', None)
    session.pop('is_ghost_mode', None)
    
    if store_id:
        log_admin_action(session['user_id'], store_id, 'exit_store', None, None, None, None)
    
    return jsonify({'ok': True})


@app.route('/api/admin/logs', methods=['GET'])
@superadmin_required
def admin_get_logs():
    """Get audit logs."""
    conn = get_db()
    logs = rows_to_list(db_execute(conn, """
        SELECT al.*, u.nama as admin_name, s.name as store_name
        FROM admin_logs al
        LEFT JOIN users u ON al.admin_id = u.id
        LEFT JOIN stores s ON al.store_id = s.id
        ORDER BY al.dibuat DESC
        LIMIT 100
    """).fetchall())
    conn.close()
    return jsonify(logs)


@app.route('/api/admin/stores/<int:store_id>', methods=['PUT'])
@superadmin_required
def admin_update_store(store_id):
    """Superadmin update data toko (termasuk slug dan owner)."""
    import re
    data = request.json
    name = data.get('name', '').strip()
    slug = data.get('slug', '').strip().lower()
    address = data.get('address', '').strip()
    phone = data.get('phone', '').strip()
    email = data.get('email', '').strip()
    is_active = data.get('is_active', 1)
    owner_id = data.get('owner_id')
    
    if not name:
        return jsonify({'error': 'Nama toko wajib diisi'}), 400
    
    # Generate slug dari name kalau tidak diisi
    if not slug:
        slug = re.sub(r'[^\w\s-]', '', name).strip().lower()
        slug = re.sub(r'[-\s]+', '-', slug)[:50]
    else:
        # Validasi slug format
        slug = re.sub(r'[^a-z0-9-]', '-', slug)[:50]
        slug = slug.strip('-')
    
    if not slug:
        slug = 'toko-' + str(store_id)
    
    conn = get_db()
    try:
        # Cek toko exists
        store = db_execute(conn, "SELECT * FROM stores WHERE id = ?", (store_id,)).fetchone()
        if not store:
            conn.close()
            return jsonify({'error': 'Toko tidak ditemukan'}), 404
        
        # Cek slug unik (kecuali untuk toko ini sendiri)
        existing = db_execute(conn, "SELECT id FROM stores WHERE slug = ? AND id != ?", (slug, store_id)).fetchone()
        if existing:
            # Tambahkan angka ke slug jika duplikat
            base_slug = slug
            counter = 1
            while existing:
                slug = f"{base_slug}-{counter}"
                existing = db_execute(conn, "SELECT id FROM stores WHERE slug = ? AND id != ?", (slug, store_id)).fetchone()
                counter += 1
        
        # Cek owner_id valid kalau diisi
        if owner_id:
            owner = db_execute(conn, "SELECT id FROM users WHERE id = ? AND role = 'pemilik'", (owner_id,)).fetchone()
            if not owner:
                conn.close()
                return jsonify({'error': 'Pemilik tidak valid'}), 400
        
        # Build update query dinamis
        fields = ['name = ?', 'slug = ?', 'address = ?', 'phone = ?', 'email = ?', 'is_active = ?']
        params = [name, slug, address, phone, email, is_active]
        
        if owner_id:
            fields.append('owner_id = ?')
            params.append(owner_id)
        
        params.append(store_id)
        
        db_execute(conn, f"""
            UPDATE stores 
            SET {', '.join(fields)}
            WHERE id = ?
        """, tuple(params))
        
        conn.commit()
        conn.close()
        
        # Log action
        log_admin_action(session['user_id'], store_id, 'update_store', 'stores', store_id, None, 
                        {'name': name, 'slug': slug, 'owner_id': owner_id})
        
        return jsonify({'ok': True, 'message': 'Toko berhasil diupdate', 'slug': slug})
    except Exception as e:
        conn.close()
        return jsonify({'error': str(e)}), 500


# ═════════════════════════════════════
#  API: USER STORES (KARYAWAN ASSIGNMENT)
# ═════════════════════════════════════

@app.route('/api/stores/<int:store_id>/users', methods=['GET'])
@pemilik_required
def list_store_users(store_id):
    """List semua karyawan di toko ini."""
    user = get_current_user()
    if not can_access_store(user['id'], store_id):
        return jsonify({'error': 'Akses ditolak'}), 403
    
    conn = get_db()
    users = rows_to_list(db_execute(conn, """
        SELECT us.*, u.username, u.nama, u.aktif
        FROM user_stores us
        JOIN users u ON us.user_id = u.id
        WHERE us.store_id = ?
        ORDER BY u.nama
    """, (store_id,)).fetchall())
    conn.close()
    return jsonify(users)


@app.route('/api/stores/<int:store_id>/users', methods=['POST'])
@pemilik_required
def add_store_user(store_id):
    """Tambah karyawan ke toko."""
    user = get_current_user()
    if not is_store_owner(user['id'], store_id):
        return jsonify({'error': 'Hanya pemilik yang bisa menambah karyawan'}), 403
    
    data = request.json
    username = data.get('username', '').strip().lower()
    nama = data.get('nama', '').strip()
    password = data.get('password', '')
    role = data.get('role', 'kasir')  # admin atau kasir
    
    if not username or not nama or not password:
        return jsonify({'error': 'Semua field wajib diisi'}), 400
    
    conn = get_db()
    try:
        # Cek apakah user sudah ada
        existing = db_execute(conn, "SELECT id FROM users WHERE username = ?", (username,)).fetchone()
        if existing:
            conn.close()
            return jsonify({'error': 'Username sudah digunakan'}), 400
        
        # Buat user karyawan
        _hash = generate_password_hash(password, method='pbkdf2:sha256')
        cur = db_execute_insert(conn,
            "INSERT INTO users (username, nama, password, role, is_superadmin) VALUES (?,?,?,?,?)",
            (username, nama, _hash, 'karyawan', 0)
        )
        user_id = cur.lastrowid
        
        # Assign ke toko
        db_execute(conn,
            "INSERT INTO user_stores (user_id, store_id, role) VALUES (?,?,?)",
            (user_id, store_id, role)
        )
        
        conn.commit()
        conn.close()
        return jsonify({'ok': True, 'user_id': user_id}), 201
    except Exception as e:
        conn.rollback()
        conn.close()
        return jsonify({'error': str(e)}), 500


@app.route('/api/stores/<int:store_id>/users/<int:user_id>', methods=['DELETE'])
@pemilik_required
def remove_store_user(store_id, user_id):
    """Hapus karyawan dari toko."""
    user = get_current_user()
    if not is_store_owner(user['id'], store_id):
        return jsonify({'error': 'Hanya pemilik yang bisa menghapus karyawan'}), 403
    
    conn = get_db()
    db_execute(conn, "DELETE FROM user_stores WHERE user_id = ? AND store_id = ?", (user_id, store_id))
    conn.commit()
    conn.close()
    return jsonify({'ok': True})


@app.route('/api/my-stores', methods=['GET'])
def my_stores():
    """Get semua toko yang bisa diakses user saat ini."""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401
    
    stores = get_accessible_stores(user['id'])
    return jsonify(stores)


@app.route('/api/switch-store/<int:store_id>', methods=['POST'])
def switch_store(store_id):
    """Switch ke toko lain."""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401
    
    if not can_access_store(user['id'], store_id):
        return jsonify({'error': 'Akses ditolak'}), 403
    
    session['current_store_id'] = store_id
    return jsonify({'ok': True})


# ─────────────────────────────────────
#  API: PENGATURAN TOKO
# ─────────────────────────────────────
@app.route('/api/pengaturan', methods=['GET'])
def get_pengaturan():
    """Get pengaturan toko. Jika multi-tenant, ambil nama toko dari tabel stores."""
    conn = get_db()
    store_id = session.get('current_store_id')
    
    # Get pengaturan dasar - filter by store_id jika ada
    if store_id:
        # Ambil pengaturan global (store_id IS NULL) dan override dengan pengaturan store-specific
        if USE_POSTGRES:
            rows = db_execute(conn, 
                "SELECT kunci, nilai FROM pengaturan WHERE store_id = ? OR store_id IS NULL ORDER BY store_id NULLS LAST",
                (store_id,)
            ).fetchall()
        else:
            # SQLite: gunakan UNION untuk ordering
            rows = db_execute(conn, 
                """SELECT kunci, nilai FROM pengaturan WHERE store_id = ?
                   UNION ALL
                   SELECT kunci, nilai FROM pengaturan 
                   WHERE store_id IS NULL 
                     AND kunci NOT IN (SELECT kunci FROM pengaturan WHERE store_id = ?)""",
                (store_id, store_id)
            ).fetchall()
        # Store-specific menang (override global)
        result = {}
        for r in rows:
            result[r['kunci']] = r['nilai']
    else:
        # Fallback: ambil semua pengaturan global
        rows = db_execute(conn, "SELECT kunci, nilai FROM pengaturan WHERE store_id IS NULL").fetchall()
        result = {r['kunci']: r['nilai'] for r in rows}
    
    # Jika ada store_id di session, ambil info toko dari tabel stores
    if store_id:
        store = db_execute(conn, 
            "SELECT name, address, phone, email FROM stores WHERE id = ?", 
            (store_id,)
        ).fetchone()
        if store:
            # Override dengan data dari stores table
            result['nama_toko'] = store['name']
            if store['address']:
                result['alamat'] = store['address']
            if store['phone']:
                result['telp'] = store['phone']
            if store['email']:
                result['email'] = store['email']
    
    conn.close()
    return jsonify(result)

@app.route('/api/pengaturan', methods=['POST'])
@pemilik_required
def save_pengaturan():
    data = request.json
    conn = get_db()
    store_id = session.get('current_store_id')
    
    # Simpan ke tabel pengaturan dengan store_id isolation
    for k, v in data.items():
        # Skip field yang di-handle oleh tabel stores
        if k in ('nama_toko', 'alamat', 'telp'):
            continue
            
        if USE_POSTGRES:
            db_execute(conn, 
                """INSERT INTO pengaturan (kunci, nilai, store_id) 
                   VALUES (%s, %s, %s) 
                   ON CONFLICT(kunci, COALESCE(store_id, 0)) DO UPDATE SET nilai=EXCLUDED.nilai""",
                (k, str(v), store_id)
            )
        else:
            # SQLite: delete dulu lalu insert (upsert workaround untuk partial unique index)
            db_execute(conn, 
                "DELETE FROM pengaturan WHERE kunci = ? AND (store_id = ? OR (store_id IS NULL AND ? IS NULL))",
                (k, store_id, store_id)
            )
            db_execute(conn, 
                "INSERT INTO pengaturan (kunci, nilai, store_id) VALUES (?,?,?)",
                (k, str(v), store_id)
            )
    
    # Jika multi-tenant, update juga tabel stores
    store_id = session.get('current_store_id')
    if store_id:
        # Cek apakah user adalah pemilik toko ini atau superadmin
        user = get_current_user()
        can_edit = False
        if user.get('is_superadmin') == 1:
            can_edit = True
        else:
            # Cek ownership
            store = db_execute(conn, "SELECT owner_id FROM stores WHERE id = ?", (store_id,)).fetchone()
            if store and store['owner_id'] == user['id']:
                can_edit = True
        
        if can_edit:
            # Update stores table
            name = data.get('nama_toko')
            address = data.get('alamat')
            phone = data.get('telp')
            
            if name or address or phone:
                db_execute(conn, 
                    "UPDATE stores SET name = COALESCE(?, name), address = COALESCE(?, address), phone = COALESCE(?, phone) WHERE id = ?",
                    (name, address, phone, store_id)
                )
    
    conn.commit()
    conn.close()
    return jsonify({'ok': True})


# ─────────────────────────────────────
#  API: PRODUK
# ─────────────────────────────────────
@app.route('/api/produk', methods=['GET'])
def get_produk():
    kategori = request.args.get('kategori', '')
    cari     = request.args.get('cari', '')
    barcode  = request.args.get('barcode', '')
    limit    = int(request.args.get('limit', 500))
    store_id = get_current_store_id()
    conn = get_db()
    
    # Jika ada barcode, cari exact match
    if barcode:
        row = db_execute(conn, 
            "SELECT * FROM produk WHERE barcode=? AND store_id=? AND aktif=1", (barcode, store_id)
        ).fetchone()
        conn.close()
        if row:
            return jsonify(dict(row))
        return jsonify({'error': 'Produk tidak ditemukan'}), 404
    
    sql = "SELECT * FROM produk WHERE store_id=? AND aktif=1"
    params = [store_id]
    if kategori and kategori != 'Semua':
        sql += " AND kategori=?"
        params.append(kategori)
    if cari:
        if USE_POSTGRES:
            sql += " AND nama ILIKE %s"
        else:
            sql += " AND nama LIKE ?"
        params.append(f'%{cari}%')
    sql += " ORDER BY kategori, nama LIMIT ?"
    params.append(limit)
    rows = db_execute(conn, sql, params).fetchall()
    conn.close()
    return jsonify(rows_to_list(rows))

@app.route('/api/produk', methods=['POST'])
@pemilik_required
def tambah_produk():
    d = request.json
    store_id = get_current_store_id()
    conn = get_db()
    cur = db_execute(conn, 
        "INSERT INTO produk (nama, harga, stok, emoji, kategori, harga_modal, stok_min, diskon, barcode, store_id) VALUES (?,?,?,?,?,?,?,?,?,?)",
        (d['nama'], d['harga'], d['stok'], d.get('emoji','[BOX]'), d['kategori'],
         d.get('harga_modal',0), d.get('stok_min',0), d.get('diskon',0), d.get('barcode',''), store_id)
    )
    produk_id = cur.lastrowid
    conn.commit()
    row = db_execute(conn, "SELECT * FROM produk WHERE id=?", (produk_id,)).fetchone()
    conn.close()
    return jsonify(row_to_dict(row)), 201

@app.route('/api/produk/<int:pid>', methods=['PUT'])
@pemilik_required
def update_produk(pid):
    d = request.json
    store_id = get_current_store_id()
    conn = get_db()
    # Cek apakah produk milik toko ini
    existing = db_execute(conn, "SELECT 1 FROM produk WHERE id=? AND store_id=?", (pid, store_id)).fetchone()
    if not existing:
        conn.close()
        return jsonify({'error': 'Produk tidak ditemukan atau bukan milik toko ini'}), 404
    
    now_sql = "CURRENT_TIMESTAMP" if USE_POSTGRES else "datetime('now','localtime')"
    db_execute(conn, 
        f"""UPDATE produk SET nama=?, harga=?, stok=?, emoji=?, kategori=?,
           harga_modal=?, stok_min=?, diskon=?, barcode=?,
           diubah={now_sql} WHERE id=? AND store_id=?""",
        (d['nama'], d['harga'], d['stok'], d.get('emoji','[BOX]'), d['kategori'],
         d.get('harga_modal',0), d.get('stok_min',0), d.get('diskon',0), d.get('barcode',''), pid, store_id)
    )
    conn.commit()
    row = db_execute(conn, "SELECT * FROM produk WHERE id=?", (pid,)).fetchone()
    conn.close()
    return jsonify(row_to_dict(row))

@app.route('/api/produk/<int:pid>', methods=['DELETE'])
@pemilik_required
def hapus_produk(pid):
    store_id = get_current_store_id()
    conn = get_db()
    # Soft delete — hanya untuk toko ini
    db_execute(conn, "UPDATE produk SET aktif=0 WHERE id=? AND store_id=?", (pid, store_id))
    conn.commit()
    conn.close()
    return jsonify({'ok': True})

@app.route('/api/produk/scan/<barcode>', methods=['GET'])
def scan_produk(barcode):
    """Scan barcode untuk mencari produk (untuk kasir)"""
    store_id = get_current_store_id()
    conn = get_db()
    row = db_execute(conn, 
        "SELECT * FROM produk WHERE barcode=? AND store_id=? AND aktif=1", (barcode, store_id)
    ).fetchone()
    conn.close()
    if row:
        return jsonify(dict(row))
    return jsonify({'error': 'Produk tidak ditemukan'}), 404

@app.route('/api/produk/stok-rendah', methods=['GET'])
@pemilik_required
def produk_stok_rendah():
    """Produk yang stoknya di bawah atau sama dengan stok_min (jika stok_min > 0)
       atau stok <= 5 jika stok_min belum diset."""
    store_id = get_current_store_id()
    conn = get_db()
    rows = db_execute(conn, """
        SELECT * FROM produk
        WHERE aktif = 1
          AND store_id = ?
          AND (
              (stok_min > 0 AND stok <= stok_min)
              OR
              (stok_min = 0 AND stok <= 5 AND stok > 0)
          )
        ORDER BY stok ASC, nama
    """, (store_id,)).fetchall()
    conn.close()
    return jsonify(rows_to_list(rows))


@app.route('/api/laporan/top-produk', methods=['GET'])
@pemilik_required
def laporan_top_produk():
    dari  = request.args.get('dari', '')
    ke    = request.args.get('ke', '')
    limit = int(request.args.get('limit', 10))
    store_id = get_current_store_id()

    conn       = get_db()
    # Filter: hanya transaksi aktif (exclude void)
    sql_filter = "WHERE COALESCE(t.status, 'aktif') = 'aktif' AND t.store_id = ?"
    params     = [store_id]
    if dari:
        sql_filter += " AND DATE(t.waktu) >= ?"
        params.append(dari)
    if ke:
        sql_filter += " AND DATE(t.waktu) <= ?"
        params.append(ke)

    top = db_execute(conn, f"""
        SELECT ti.produk_id, ti.nama_produk AS nama, ti.emoji,
               SUM(ti.qty)      AS total_qty,
               SUM(ti.subtotal) AS total_nilai,
               COALESCE(p.harga_modal, 0) AS harga_modal
        FROM transaksi_item ti
        JOIN transaksi t ON t.id = ti.transaksi_id
        LEFT JOIN produk p ON p.id = ti.produk_id
        {sql_filter}
        GROUP BY ti.produk_id, ti.nama_produk
        ORDER BY total_qty DESC
        LIMIT ?
    """, params + [limit]).fetchall()
    conn.close()
    return jsonify(rows_to_list(top))


@app.route('/api/produk/kategori', methods=['GET'])
def get_kategori():
    conn = get_db()
    rows = db_execute(conn, "SELECT DISTINCT kategori FROM produk WHERE aktif=1 ORDER BY kategori").fetchall()
    conn.close()
    return jsonify([r['kategori'] for r in rows])


# ─────────────────────────────────────
#  API: TRANSAKSI
# ─────────────────────────────────────
@app.route('/api/transaksi', methods=['POST'])
@login_required
def buat_transaksi():
    d = request.json
    items        = d.get('items', [])
    subtotal     = d.get('subtotal', 0)
    diskon       = d.get('diskon', 0)
    diskon_val   = d.get('diskon_val', 0)
    diskon_tipe  = d.get('diskon_tipe', 'persen')
    total        = d.get('total', 0)
    bayar        = d.get('bayar', 0)
    kembalian    = bayar - total
    pelanggan_id = d.get('pelanggan_id') or None
    metode_bayar = d.get('metode_bayar', 'tunai')
    store_id     = get_current_store_id()
    
    # Handle piutang/hutang
    is_piutang = metode_bayar == 'piutang'
    if is_piutang:
        is_lunas = 0
        terbayar = max(0, bayar)  # Pembayaran awal (bisa 0)
        sisa_piutang = total - terbayar
        kembalian = 0  # Piutang tidak ada kembalian
    else:
        if metode_bayar not in ('tunai', 'transfer', 'qris'):
            metode_bayar = 'tunai'
        is_lunas = 1
        terbayar = total
        sisa_piutang = 0

    # Generate no_trx unik dengan suffix counter untuk menghindari duplikat
    base_no_trx = 'TRX' + datetime.now().strftime('%y%m%d%H%M%S')
    no_trx = base_no_trx
    
    # Cek duplikat dan tambah suffix jika perlu
    counter = 1
    conn_check = get_db()
    while True:
        existing = db_execute(conn_check, 
            "SELECT 1 FROM transaksi WHERE no_trx = ?", (no_trx,)
        ).fetchone()
        if not existing:
            break
        no_trx = f"{base_no_trx}-{counter:03d}"
        counter += 1
    conn_check.close()

    conn = get_db()
    try:
        # Insert header transaksi
        cur = db_execute_insert(conn, 
            """INSERT INTO transaksi
               (no_trx, subtotal, diskon, diskon_val, diskon_tipe, total, bayar, kembalian, 
                pelanggan_id, metode_bayar, is_lunas, terbayar, sisa_piutang, store_id)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (no_trx, subtotal, diskon, diskon_val, diskon_tipe, total, bayar, kembalian, 
             pelanggan_id, metode_bayar, is_lunas, terbayar, sisa_piutang, store_id)
        )
        trx_id = cur.lastrowid

        # Insert item & kurangi stok
        for item in items:
            db_execute(conn, 
                """INSERT INTO transaksi_item
                   (transaksi_id, produk_id, nama_produk, emoji, harga, qty, subtotal)
                   VALUES (?,?,?,?,?,?,?)""",
                (trx_id, item['id'], item['nama'], item.get('emoji','[BOX]'),
                 item['harga'], item['qty'], item['harga'] * item['qty'])
            )
            db_execute(conn, 
                "UPDATE produk SET stok = stok - ? WHERE id=?",
                (item['qty'], item['id'])
            )

        # Jika bukan piutang, masukkan ke kas/dompet
        if not is_piutang and total > 0:
            db_execute(conn,
                "INSERT INTO kas (tipe, jumlah, keterangan, metode, store_id) VALUES (?,?,?,?,?)",
                ('pemasukan', total, f'Penjualan {no_trx}', metode_bayar, store_id)
            )

        conn.commit()

        # Return transaksi lengkap
        trx = row_to_dict(db_execute(conn, "SELECT * FROM transaksi WHERE id=?", (trx_id,)).fetchone())
        trx['items'] = rows_to_list(db_execute(conn, 
            "SELECT * FROM transaksi_item WHERE transaksi_id=?", (trx_id,)
        ).fetchall())

        conn.close()
        return jsonify(trx), 201

    except Exception as e:
        conn.rollback()
        conn.close()
        return jsonify({'error': str(e)}), 500

@app.route('/api/transaksi', methods=['GET'])
def get_transaksi():
    tgl_dari = request.args.get('dari', '')
    tgl_ke   = request.args.get('ke', '')
    status   = request.args.get('status', '')  # aktif, void, atau kosong (semua)
    limit    = int(request.args.get('limit', 100))

    conn = get_db()
    sql = """
        SELECT t.*, COALESCE(p.nama, '') AS pelanggan_nama
        FROM transaksi t
        LEFT JOIN pelanggan p ON p.id = t.pelanggan_id
        WHERE 1=1
    """
    params = []
    if tgl_dari:
        sql += " AND DATE(t.waktu) >= ?"
        params.append(tgl_dari)
    if tgl_ke:
        sql += " AND DATE(t.waktu) <= ?"
        params.append(tgl_ke)
    if status:
        sql += " AND COALESCE(t.status, 'aktif') = ?"
        params.append(status)
    sql += " ORDER BY t.waktu DESC LIMIT ?"
    params.append(limit)

    rows = db_execute(conn, sql, params).fetchall()
    result = []
    for r in rows:
        trx = row_to_dict(r)
        trx['items'] = rows_to_list(db_execute(conn, 
            "SELECT * FROM transaksi_item WHERE transaksi_id=?", (r['id'],)
        ).fetchall())
        result.append(trx)
    conn.close()
    return jsonify(result)

@app.route('/api/transaksi/<int:tid>', methods=['GET'])
def get_transaksi_by_id(tid):
    conn = get_db()
    trx = db_execute(conn, """
        SELECT t.*, COALESCE(p.nama, '') AS pelanggan_nama
        FROM transaksi t
        LEFT JOIN pelanggan p ON p.id = t.pelanggan_id
        WHERE t.id=?
    """, (tid,)).fetchone()
    if not trx:
        conn.close()
        return jsonify({'error': 'Tidak ditemukan'}), 404
    result = row_to_dict(trx)
    result['items'] = rows_to_list(db_execute(conn, 
        "SELECT * FROM transaksi_item WHERE transaksi_id=?", (tid,)
    ).fetchall())
    conn.close()
    return jsonify(result)


# ─────────────────────────────────────
#  API: KAS / DOMPET
# ─────────────────────────────────────
@app.route('/api/kas', methods=['GET'])
@pemilik_required
def get_kas():
    dari  = request.args.get('dari', '')
    ke    = request.args.get('ke', '')
    store_id = get_current_store_id()
    conn  = get_db()
    sql   = "SELECT * FROM kas WHERE store_id = ?"
    params = [store_id]
    if dari:
        sql += " AND DATE(waktu) >= ?"
        params.append(dari)
    if ke:
        sql += " AND DATE(waktu) <= ?"
        params.append(ke)
    sql += " ORDER BY waktu DESC LIMIT 200"
    rows = rows_to_list(db_execute(conn, sql, params).fetchall())

    # Statistik periode
    sql_stat = """
        SELECT
            COALESCE(SUM(CASE WHEN tipe='pemasukan'   THEN jumlah ELSE 0 END), 0) AS total_masuk,
            COALESCE(SUM(CASE WHEN tipe='pengeluaran' THEN jumlah ELSE 0 END), 0) AS total_keluar
        FROM kas WHERE store_id = ?
    """
    stat_params = [store_id]
    if dari:
        sql_stat += " AND DATE(waktu) >= ?"
        stat_params.append(dari)
    if ke:
        sql_stat += " AND DATE(waktu) <= ?"
        stat_params.append(ke)
    stat = row_to_dict(db_execute(conn, sql_stat, stat_params).fetchone())

    # Saldo keseluruhan (all time) + breakdown per metode
    saldo_row = db_execute(conn, """
        SELECT
            COALESCE(SUM(CASE WHEN tipe='pemasukan' THEN jumlah ELSE -jumlah END), 0) AS saldo,
            COALESCE(SUM(CASE WHEN COALESCE(metode,'tunai')='tunai'
                                   AND tipe='pemasukan'  THEN  jumlah
                              WHEN COALESCE(metode,'tunai')='tunai'
                                   AND tipe='pengeluaran' THEN -jumlah
                              ELSE 0 END), 0) AS saldo_tunai,
            COALESCE(SUM(CASE WHEN COALESCE(metode,'tunai')!='tunai'
                                   AND tipe='pemasukan'  THEN  jumlah
                              WHEN COALESCE(metode,'tunai')!='tunai'
                                   AND tipe='pengeluaran' THEN -jumlah
                              ELSE 0 END), 0) AS saldo_nontunai
        FROM kas WHERE store_id = ?
    """, (store_id,)).fetchone()
    stat['saldo']         = saldo_row['saldo']
    stat['saldo_tunai']   = saldo_row['saldo_tunai']
    stat['saldo_nontunai']= saldo_row['saldo_nontunai']
    conn.close()
    return jsonify({'rows': rows, 'stats': stat})


@app.route('/api/kas', methods=['POST'])
@pemilik_required
def tambah_kas():
    d = request.json
    tipe       = d.get('tipe')
    jumlah     = int(d.get('jumlah', 0))
    keterangan = d.get('keterangan', '').strip()
    metode     = d.get('metode', 'tunai')
    store_id   = get_current_store_id()
    if metode not in ('tunai', 'transfer', 'qris'):
        metode = 'tunai'
    if tipe not in ('pemasukan', 'pengeluaran') or jumlah <= 0:
        return jsonify({'error': 'Data tidak valid'}), 400
    conn = get_db()
    cur = db_execute(conn, 
        "INSERT INTO kas (tipe, jumlah, keterangan, metode, store_id) VALUES (?,?,?,?,?)",
        (tipe, jumlah, keterangan, metode, store_id)
    )
    kid = cur.lastrowid
    conn.commit()
    row = row_to_dict(db_execute(conn, "SELECT * FROM kas WHERE id=?", (kid,)).fetchone())
    conn.close()
    return jsonify(row), 201


@app.route('/api/kas/<int:kid>', methods=['DELETE'])
@pemilik_required
def hapus_kas(kid):
    store_id = get_current_store_id()
    conn = get_db()
    db_execute(conn, "DELETE FROM kas WHERE id=? AND store_id=?", (kid, store_id))
    conn.commit()
    conn.close()
    return jsonify({'ok': True})


@app.route('/api/kas/reset', methods=['POST'])
@pemilik_required
def reset_saldo_kas():
    """Reset saldo dompet ke 0 dengan konfirmasi."""
    d = request.json or {}
    konfirmasi = d.get('konfirmasi', '').strip()
    
    if konfirmasi != 'Reset Saldo':
        return jsonify({'error': 'Konfirmasi tidak valid. Ketik "Reset Saldo" untuk melanjutkan.'}), 400
    
    store_id = get_current_store_id()
    conn = get_db()
    # Hapus semua data kas di toko ini (reset)
    db_execute(conn, "DELETE FROM kas WHERE store_id=?", (store_id,))
    conn.commit()
    conn.close()
    return jsonify({'ok': True, 'message': 'Saldo dompet berhasil direset'})


# ─────────────────────────────────────
#  API: PRODUK TERJUAL (Aggregasi)
# ─────────────────────────────────────
@app.route('/api/laporan/produk-terjual', methods=['GET'])
@pemilik_required
def get_produk_terjual():
    """Aggregasi produk terjual per periode (harian/mingguan/bulanan)."""
    dari = request.args.get('dari', '')
    ke   = request.args.get('ke', '')
    
    if not dari or not ke:
        return jsonify({'error': 'Parameter dari dan ke wajib diisi'}), 400
    
    conn = get_db()
    
    # Query aggregasi produk terjual - hanya transaksi aktif yang lunas atau ada pembayaran
    sql = """
        SELECT 
            p.id,
            p.nama,
            p.emoji,
            p.kategori,
            COALESCE(SUM(ti.qty), 0) as total_terjual,
            COALESCE(SUM(ti.subtotal), 0) as total_omzet,
            COUNT(DISTINCT ti.transaksi_id) as jumlah_transaksi
        FROM produk p
        JOIN transaksi_item ti ON ti.produk_id = p.id
        JOIN transaksi t ON t.id = ti.transaksi_id
        WHERE DATE(t.waktu) >= ?
          AND DATE(t.waktu) <= ?
          AND COALESCE(t.status, 'aktif') = 'aktif'
          AND COALESCE(t.is_lunas, 1) = 1
        GROUP BY p.id, p.nama, p.emoji, p.kategori
        HAVING total_terjual > 0
        ORDER BY total_terjual DESC
    """
    
    rows = rows_to_list(db_execute(conn, sql, (dari, ke)).fetchall())
    
    # Hitung total keseluruhan
    total_stat = db_execute(conn, """
        SELECT 
            COALESCE(SUM(ti.qty), 0) as total_qty,
            COALESCE(SUM(ti.subtotal), 0) as total_omzet
        FROM transaksi_item ti
        JOIN transaksi t ON t.id = ti.transaksi_id
        WHERE DATE(t.waktu) >= ?
          AND DATE(t.waktu) <= ?
          AND COALESCE(t.status, 'aktif') = 'aktif'
          AND COALESCE(t.is_lunas, 1) = 1
    """, (dari, ke)).fetchone()
    
    conn.close()
    
    return jsonify({
        'rows': rows,
        'total_qty': total_stat['total_qty'] if total_stat else 0,
        'total_omzet': total_stat['total_omzet'] if total_stat else 0
    })


# ─────────────────────────────────────
#  API: TUTUP KASIR
# ─────────────────────────────────────
@app.route('/api/tutup-kasir/preview', methods=['GET'])
def tutup_kasir_preview():
    """Hitung transaksi yang belum ditutup (tutup_kasir_id IS NULL)."""
    store_id = get_current_store_id()
    conn = get_db()
    row = db_execute(conn, """
        SELECT
            COUNT(*)                                                  AS jumlah_trx,
            COALESCE(SUM(total), 0)                                   AS total,
            COALESCE(SUM(CASE WHEN COALESCE(metode_bayar,'tunai')='tunai'
                              THEN total ELSE 0 END), 0)              AS total_tunai,
            COALESCE(SUM(CASE WHEN metode_bayar='transfer'
                              THEN total ELSE 0 END), 0)              AS total_transfer,
            COALESCE(SUM(CASE WHEN metode_bayar='qris'
                              THEN total ELSE 0 END), 0)              AS total_qris
        FROM transaksi
        WHERE tutup_kasir_id IS NULL
          AND COALESCE(status, 'aktif') = 'aktif'
          AND store_id = ?
    """, (store_id,)).fetchone()
    conn.close()
    return jsonify(row_to_dict(row))


@app.route('/api/tutup-kasir', methods=['POST'])
def buat_tutup_kasir():
    """Karyawan/pemilik proses tutup kasir → status pending."""
    user = get_current_user()
    d = request.json or {}
    keterangan = d.get('keterangan', '').strip()
    store_id = get_current_store_id()

    conn = get_db()
    # Ambil preview dulu - hanya transaksi aktif yang belum ditutup
    row = db_execute(conn, """
        SELECT
            COUNT(*)                                                  AS jumlah_trx,
            COALESCE(SUM(total), 0)                                   AS total,
            COALESCE(SUM(CASE WHEN COALESCE(metode_bayar,'tunai')='tunai'
                              THEN total ELSE 0 END), 0)              AS total_tunai,
            COALESCE(SUM(CASE WHEN metode_bayar='transfer'
                              THEN total ELSE 0 END), 0)              AS total_transfer,
            COALESCE(SUM(CASE WHEN metode_bayar='qris'
                              THEN total ELSE 0 END), 0)              AS total_qris
        FROM transaksi
        WHERE tutup_kasir_id IS NULL
          AND COALESCE(status, 'aktif') = 'aktif'
          AND store_id = ?
    """, (store_id,)).fetchone()

    if row['jumlah_trx'] == 0:
        conn.close()
        return jsonify({'error': 'Tidak ada transaksi yang belum ditutup'}), 400

    # Buat record tutup_kasir
    cur = db_execute(conn, 
        """INSERT INTO tutup_kasir
           (total, total_tunai, total_transfer, total_qris, jumlah_trx, keterangan, dibuat_oleh, store_id)
           VALUES (?,?,?,?,?,?,?,?)""",
        (row['total'], row['total_tunai'], row['total_transfer'], row['total_qris'],
         row['jumlah_trx'], keterangan, user['nama'], store_id)
    )
    tk_id = cur.lastrowid

    # Tandai semua transaksi belum tutup dengan id ini (hanya yang aktif)
    db_execute(conn, 
        "UPDATE transaksi SET tutup_kasir_id=? WHERE tutup_kasir_id IS NULL AND COALESCE(status, 'aktif') = 'aktif' AND store_id=?",
        (tk_id, store_id)
    )
    conn.commit()

    result = row_to_dict(db_execute(conn, 
        "SELECT * FROM tutup_kasir WHERE id=?", (tk_id,)
    ).fetchone())
    conn.close()
    return jsonify(result), 201


@app.route('/api/tutup-kasir', methods=['GET'])
@pemilik_required
def list_tutup_kasir():
    """Pemilik: ambil riwayat tutup kasir + jumlah pending."""
    store_id = get_current_store_id()
    conn = get_db()
    rows = rows_to_list(db_execute(conn, 
        "SELECT * FROM tutup_kasir WHERE store_id=? ORDER BY waktu DESC LIMIT 50",
        (store_id,)
    ).fetchall())
    pending = db_execute(conn, 
        "SELECT COUNT(*) AS n FROM tutup_kasir WHERE status='pending' AND store_id=?",
        (store_id,)
    ).fetchone()['n']
    conn.close()
    return jsonify({'rows': rows, 'pending': pending})


@app.route('/api/tutup-kasir/<int:tk_id>/konfirmasi', methods=['POST'])
@pemilik_required
def konfirmasi_tutup_kasir(tk_id):
    """Pemilik konfirmasi → buat entri kas pemasukan per metode."""
    user = get_current_user()
    store_id = get_current_store_id()
    conn = get_db()
    tk = db_execute(conn, "SELECT * FROM tutup_kasir WHERE id=? AND store_id=?", (tk_id, store_id)).fetchone()
    if not tk:
        conn.close()
        return jsonify({'error': 'Data tidak ditemukan'}), 404
    if tk['status'] == 'confirmed':
        conn.close()
        return jsonify({'error': 'Sudah dikonfirmasi sebelumnya'}), 400

    tgl = tk['waktu'][:10]  # YYYY-MM-DD
    waktu_now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # Buat entri kas per metode (jika ada nominalnya)
    metode_map = [
        (tk['total_tunai'],    'tunai',    f'Tutup Kasir {tgl} – Tunai'),
        (tk['total_transfer'], 'transfer', f'Tutup Kasir {tgl} – Transfer'),
        (tk['total_qris'],     'qris',     f'Tutup Kasir {tgl} – QRIS'),
    ]
    for jumlah, metode, ket in metode_map:
        if jumlah > 0:
            db_execute(conn, 
                "INSERT INTO kas (tipe, jumlah, keterangan, metode, store_id) VALUES (?,?,?,?,?)",
                ('pemasukan', jumlah, ket, metode, store_id)
            )

    # Update status tutup_kasir
    db_execute(conn, 
        """UPDATE tutup_kasir
           SET status='confirmed', dikonfirmasi_oleh=?, waktu_konfirmasi=?
           WHERE id=?""",
        (user['nama'], waktu_now, tk_id)
    )
    conn.commit()

    result = row_to_dict(db_execute(conn, 
        "SELECT * FROM tutup_kasir WHERE id=?", (tk_id,)
    ).fetchone())
    conn.close()
    return jsonify(result)


# ═════════════════════════════════════
#  API: VOID / CANCEL TRANSAKSI
# ═════════════════════════════════════
@app.route('/api/transaksi/<int:tid>/void', methods=['POST'])
@pemilik_required
def void_transaksi(tid):
    """Void transaksi: kembalikan stok dan tandai transaksi sebagai void."""
    user = get_current_user()
    d = request.json or {}
    reason = d.get('reason', '').strip()
    
    if not reason:
        return jsonify({'error': 'Alasan void wajib diisi'}), 400
    
    conn = get_db()
    conn.execute("BEGIN TRANSACTION")
    
    try:
        # Cek transaksi exists dan belum void
        trx = db_execute(conn, 
            "SELECT * FROM transaksi WHERE id=?", (tid,)
        ).fetchone()
        
        if not trx:
            conn.rollback()
            conn.close()
            return jsonify({'error': 'Transaksi tidak ditemukan'}), 404
        
        if trx.get('status') == 'void':
            conn.rollback()
            conn.close()
            return jsonify({'error': 'Transaksi sudah di-void sebelumnya'}), 400
        
        # Jika transaksi sudah masuk tutup kasir yang confirmed, tidak bisa void
        if trx.get('tutup_kasir_id'):
            tk = db_execute(conn, 
                "SELECT status FROM tutup_kasir WHERE id=?", (trx['tutup_kasir_id'],)
            ).fetchone()
            if tk and tk['status'] == 'confirmed':
                conn.rollback()
                conn.close()
                return jsonify({'error': 'Transaksi sudah ditutup dan dikonfirmasi, tidak bisa di-void'}), 400
        
        waktu_now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Kembalikan stok untuk setiap item
        items = db_execute(conn, 
            "SELECT * FROM transaksi_item WHERE transaksi_id=?", (tid,)
        ).fetchall()
        
        for item in items:
            produk_id = item['produk_id']
            qty = item['qty']
            
            # Get stok saat ini
            prod = db_execute(conn, 
                "SELECT stok FROM produk WHERE id=?", (produk_id,)
            ).fetchone()
            
            if prod:
                stok_sebelum = prod['stok']
                stok_sesudah = stok_sebelum + qty
                
                # Update stok produk
                db_execute(conn, 
                    "UPDATE produk SET stok = stok + ? WHERE id=?",
                    (qty, produk_id)
                )
                
                # Catat di stok_log (void)
                db_execute(conn, 
                    """INSERT INTO stok_log 
                       (produk_id, tipe, jumlah, stok_sebelum, stok_sesudah, 
                        alasan, keterangan, transaksi_id, dibuat_oleh)
                       VALUES (?,?,?,?,?,?,?,?,?)""",
                    (produk_id, 'masuk', qty, stok_sebelum, stok_sesudah,
                     'void_transaksi', f'Pengembalian stok dari void transaksi {trx["no_trx"]}', 
                     tid, user['nama'])
                )
        
        # Update status transaksi menjadi void
        db_execute(conn, 
            """UPDATE transaksi 
               SET status='void', void_reason=?, void_by=?, void_at=?
               WHERE id=?""",
            (reason, user['nama'], waktu_now, tid)
        )
        
        # Jika transaksi sudah lunas (bukan piutang), keluarkan dari kas
        if trx.get('is_lunas', 1) == 1 and trx.get('metode_bayar') != 'piutang':
            db_execute(conn,
                """INSERT INTO kas (tipe, jumlah, keterangan, metode, store_id) 
                   VALUES (?,?,?,?,?)""",
                ('pengeluaran', trx['total'], 
                 f'Void transaksi {trx["no_trx"]}: {reason}',
                 trx.get('metode_bayar', 'tunai'),
                 store_id)
            )
        
        conn.commit()
        
        # Return updated transaksi
        result = row_to_dict(db_execute(conn, 
            "SELECT * FROM transaksi WHERE id=?", (tid,)
        ).fetchone())
        conn.close()
        
        return jsonify({'ok': True, 'transaksi': result})
        
    except Exception as e:
        conn.rollback()
        conn.close()
        return jsonify({'error': str(e)}), 500


@app.route('/api/transaksi/<int:tid>/restore', methods=['POST'])
@pemilik_required
def restore_transaksi(tid):
    """Restore transaksi yang sudah di-void (batalkan void)."""
    user = get_current_user()
    conn = get_db()
    conn.execute("BEGIN TRANSACTION")
    
    try:
        # Cek transaksi exists dan status void
        trx = db_execute(conn, 
            "SELECT * FROM transaksi WHERE id=?", (tid,)
        ).fetchone()
        
        if not trx:
            conn.rollback()
            conn.close()
            return jsonify({'error': 'Transaksi tidak ditemukan'}), 404
        
        if trx.get('status') != 'void':
            conn.rollback()
            conn.close()
            return jsonify({'error': 'Transaksi tidak dalam status void'}), 400
        
        # Kurangi stok kembali (karena transaksi di-restore)
        items = db_execute(conn, 
            "SELECT * FROM transaksi_item WHERE transaksi_id=?", (tid,)
        ).fetchall()
        
        # Validasi stok terlebih dahulu
        stok_tidak_cukup = []
        for item in items:
            produk_id = item['produk_id']
            qty = item['qty']
            
            prod = db_execute(conn, 
                "SELECT nama, stok FROM produk WHERE id=? AND store_id=?", (produk_id, store_id)
            ).fetchone()
            
            if prod and prod['stok'] < qty:
                stok_tidak_cukup.append({
                    'nama': prod['nama'],
                    'stok_tersedia': prod['stok'],
                    'stok_dibutuhkan': qty
                })
        
        # Jika ada stok yang tidak cukup, beri warning tapi tetap lanjutkan (stok jadi negatif)
        if stok_tidak_cukup:
            # Log warning - tetap lanjutkan tapi catat
            print(f"[WARN] Restore transaksi {trx['no_trx']}: Stok tidak cukup untuk {len(stok_tidak_cukup)} produk")
        
        for item in items:
            produk_id = item['produk_id']
            qty = item['qty']
            
            # Get stok saat ini
            prod = db_execute(conn, 
                "SELECT nama, stok FROM produk WHERE id=? AND store_id=?", (produk_id, store_id)
            ).fetchone()
            
            if prod:
                stok_sebelum = prod['stok']
                stok_sesudah = stok_sebelum - qty  # Bisa negatif
                
                # Update stok produk (boleh negatif untuk kasus restore)
                db_execute(conn, 
                    "UPDATE produk SET stok = ? WHERE id=?",
                    (stok_sesudah, produk_id)
                )
                
                # Catat di stok_log (restore)
                db_execute(conn, 
                    """INSERT INTO stok_log 
                       (produk_id, tipe, jumlah, stok_sebelum, stok_sesudah, 
                        alasan, keterangan, transaksi_id, dibuat_oleh, store_id)
                       VALUES (?,?,?,?,?,?,?,?,?,?)""",
                    (produk_id, 'keluar', qty, stok_sebelum, stok_sesudah,
                     'restore_transaksi', f'Pengurangan stok dari restore transaksi {trx["no_trx"]}', 
                     tid, user['nama'], store_id)
                )
        
        # Update status transaksi menjadi aktif
        db_execute(conn, 
            """UPDATE transaksi 
               SET status='aktif', void_reason='', void_by='', void_at=''
               WHERE id=?""",
            (tid,)
        )
        
        # Jika transaksi lunas (bukan piutang), masukkan kembali ke kas
        if trx.get('is_lunas', 1) == 1 and trx.get('metode_bayar') != 'piutang':
            db_execute(conn,
                """INSERT INTO kas (tipe, jumlah, keterangan, metode, store_id) 
                   VALUES (?,?,?,?,?)""",
                ('pemasukan', trx['total'], 
                 f'Restore transaksi {trx["no_trx"]}',
                 trx.get('metode_bayar', 'tunai'),
                 store_id)
            )
        
        conn.commit()
        
        result = row_to_dict(db_execute(conn, 
            "SELECT * FROM transaksi WHERE id=?", (tid,)
        ).fetchone())
        conn.close()
        
        return jsonify({'ok': True, 'transaksi': result})
        
    except Exception as e:
        conn.rollback()
        conn.close()
        return jsonify({'error': str(e)}), 500


# ═════════════════════════════════════
#  API: PIUTANG (PELUNASAN CICILAN)
# ═════════════════════════════════════

@app.route('/api/piutang', methods=['GET'])
@login_required
def get_piutang_list():
    """List semua piutang belum lunas dengan filter."""
    store_id = get_current_store_id()
    cari = request.args.get('cari', '').strip()
    
    conn = get_db()
    
    sql = """
        SELECT t.*, p.nama as pelanggan_nama, p.telepon as pelanggan_telp
        FROM transaksi t
        LEFT JOIN pelanggan p ON p.id = t.pelanggan_id
        WHERE t.metode_bayar = 'piutang' 
          AND COALESCE(t.is_lunas, 0) = 0
          AND COALESCE(t.status, 'aktif') = 'aktif'
          AND (t.store_id = ? OR ? IS NULL)
    """
    params = [store_id, store_id]
    
    if cari:
        sql += " AND (p.nama LIKE ? OR t.no_trx LIKE ?)"
        params.extend([f'%{cari}%', f'%{cari}%'])
    
    sql += " ORDER BY t.waktu DESC"
    
    rows = db_execute(conn, sql, tuple(params)).fetchall()
    
    # Ambil history pembayaran untuk setiap piutang
    result = []
    for row in rows:
        piutang = row_to_dict(row)
        
        # Hitung total sudah dibayar dari piutang_bayar
        history = db_execute(conn, """
            SELECT * FROM piutang_bayar 
            WHERE transaksi_id = ? ORDER BY waktu DESC
        """, (piutang['id'],)).fetchall()
        
        piutang['history_bayar'] = [row_to_dict(h) for h in history]
        piutang['total_bayar'] = sum(h['nominal'] for h in history)
        piutang['sisa_real'] = piutang['total'] - piutang['total_bayar']
        
        result.append(piutang)
    
    conn.close()
    return jsonify(result)


@app.route('/api/piutang/<int:tid>/bayar', methods=['POST'])
@login_required
def bayar_piutang(tid):
    """Bayar cicilan piutang (partial atau full)."""
    d = request.json
    nominal = d.get('nominal', 0)
    metode = d.get('metode_bayar', 'tunai')
    catatan = d.get('catatan', '').strip()
    
    if nominal <= 0:
        return jsonify({'error': 'Nominal pembayaran harus lebih dari 0'}), 400
    
    user = get_current_user()
    store_id = get_current_store_id()
    
    conn = get_db()
    conn.execute("BEGIN TRANSACTION")
    
    try:
        # Cek transaksi exists dan status piutang dengan row locking untuk mencegah race condition
        lock_sql = "FOR UPDATE" if USE_POSTGRES else ""
        trx = db_execute(conn, f"""
            SELECT * FROM transaksi 
            WHERE id=? AND metode_bayar='piutang' 
              AND COALESCE(is_lunas, 0) = 0
              AND COALESCE(status, 'aktif') = 'aktif'
              AND (store_id = ? OR ? IS NULL)
            {lock_sql}
        """, (tid, store_id, store_id)).fetchone()
        
        if not trx:
            conn.rollback()
            conn.close()
            return jsonify({'error': 'Piutang tidak ditemukan atau sudah lunas'}), 404
        
        # Hitung total sudah dibayar
        total_sudah_bayar = db_execute(conn, """
            SELECT COALESCE(SUM(nominal), 0) as total FROM piutang_bayar 
            WHERE transaksi_id=?
        """, (tid,)).fetchone()['total']
        
        sisa_sekarang = trx['total'] - total_sudah_bayar
        
        if nominal > sisa_sekarang:
            conn.rollback()
            conn.close()
            return jsonify({'error': f'Nominal melebihi sisa piutang. Sisa: {sisa_sekarang}'}), 400
        
        # Insert ke piutang_bayar
        cur = db_execute_insert(conn, """
            INSERT INTO piutang_bayar 
            (transaksi_id, nominal, metode_bayar, catatan, dibuat_oleh, store_id)
            VALUES (?,?,?,?,?,?)
        """, (tid, nominal, metode, catatan, user['nama'], store_id))
        
        bayar_id = cur.lastrowid
        
        # Update total terbayar di transaksi
        total_terbayar = total_sudah_bayar + nominal
        sisa_baru = trx['total'] - total_terbayar
        is_lunas = 1 if sisa_baru <= 0 else 0
        
        db_execute(conn, """
            UPDATE transaksi 
            SET terbayar=?, sisa_piutang=?, is_lunas=?
            WHERE id=?
        """, (total_terbayar, max(0, sisa_baru), is_lunas, tid))
        
        # Masukkan ke kas (pemasukan dari pelunasan piutang)
        db_execute(conn,
            "INSERT INTO kas (tipe, jumlah, keterangan, metode, store_id) VALUES (?,?,?,?,?)",
            ('pemasukan', nominal, f'Pelunasan piutang {trx["no_trx"]}', metode, store_id)
        )
        
        conn.commit()
        
        result = row_to_dict(db_execute(conn, 
            "SELECT * FROM piutang_bayar WHERE id=?", (bayar_id,)
        ).fetchone())
        
        conn.close()
        
        return jsonify({
            'ok': True, 
            'pembayaran': result,
            'is_lunas': is_lunas,
            'sisa_piutang': max(0, sisa_baru)
        })
        
    except Exception as e:
        conn.rollback()
        conn.close()
        return jsonify({'error': str(e)}), 500


@app.route('/api/piutang/<int:tid>/history', methods=['GET'])
@login_required
def get_piutang_history(tid):
    """History pembayaran per piutang."""
    store_id = get_current_store_id()
    
    conn = get_db()
    
    # Cek transaksi exists dan milik store ini
    trx = db_execute(conn, """
        SELECT * FROM transaksi 
        WHERE id=? AND metode_bayar='piutang'
          AND (store_id = ? OR ? IS NULL)
    """, (tid, store_id, store_id)).fetchone()
    
    if not trx:
        conn.close()
        return jsonify({'error': 'Piutang tidak ditemukan'}), 404
    
    history = db_execute(conn, """
        SELECT * FROM piutang_bayar 
        WHERE transaksi_id = ? ORDER BY waktu DESC
    """, (tid,)).fetchall()
    
    conn.close()
    
    return jsonify({
        'transaksi': row_to_dict(trx),
        'history': [row_to_dict(h) for h in history],
        'total_bayar': sum(h['nominal'] for h in history)
    })


@app.route('/api/piutang/reminder', methods=['GET'])
@login_required
def get_piutang_reminder():
    """List piutang jatuh tempo (>30 hari)."""
    store_id = get_current_store_id()
    hari = request.args.get('hari', 30, type=int)
    
    conn = get_db()
    
    if USE_POSTGRES:
        sql = """
            SELECT t.*, p.nama as pelanggan_nama, p.telepon as pelanggan_telp
            FROM transaksi t
            LEFT JOIN pelanggan p ON p.id = t.pelanggan_id
            WHERE t.metode_bayar = 'piutang' 
              AND COALESCE(t.is_lunas, 0) = 0
              AND COALESCE(t.status, 'aktif') = 'aktif'
              AND (t.store_id = %s OR %s IS NULL)
              AND t.waktu <= CURRENT_TIMESTAMP - INTERVAL '%s days'
            ORDER BY t.waktu ASC
        """
        rows = db_execute(conn, sql, (store_id, store_id, hari)).fetchall()
    else:
        sql = """
            SELECT t.*, p.nama as pelanggan_nama, p.telepon as pelanggan_telp
            FROM transaksi t
            LEFT JOIN pelanggan p ON p.id = t.pelanggan_id
            WHERE t.metode_bayar = 'piutang' 
              AND COALESCE(t.is_lunas, 0) = 0
              AND COALESCE(t.status, 'aktif') = 'aktif'
              AND (t.store_id = ? OR ? IS NULL)
              AND datetime(t.waktu) <= datetime('now', '-{} days')
            ORDER BY t.waktu ASC
        """.format(hari)
        rows = db_execute(conn, sql, (store_id, store_id)).fetchall()
    
    result = [row_to_dict(r) for r in rows]
    conn.close()
    
    return jsonify({
        'hari_threshold': hari,
        'total_piutang': len(result),
        'total_nominal': sum(r['sisa_piutang'] for r in result),
        'piutang_list': result
    })


# ═════════════════════════════════════
#  API: SHARE STRUK DIGITAL
# ═════════════════════════════════════
@app.route('/api/struk/<int:tid>/image', methods=['GET'])
def generate_struk_image(tid):
    """Generate struk transaksi sebagai gambar PNG untuk share."""
    try:
        from PIL import Image, ImageDraw, ImageFont
        import textwrap
    except ImportError:
        return jsonify({'error': 'Library PIL tidak tersedia'}), 500
    
    conn = get_db()
    
    # Get transaksi
    trx = db_execute(conn, """
        SELECT t.*, COALESCE(p.nama, '') AS pelanggan_nama
        FROM transaksi t
        LEFT JOIN pelanggan p ON p.id = t.pelanggan_id
        WHERE t.id = ?
    """, (tid,)).fetchone()
    
    if not trx:
        conn.close()
        return jsonify({'error': 'Transaksi tidak ditemukan'}), 404
    
    # Get items
    items = db_execute(conn, 
        "SELECT * FROM transaksi_item WHERE transaksi_id=?", (tid,)
    ).fetchall()
    
    # Get pengaturan toko
    pengaturan = db_execute(conn, "SELECT kunci, nilai FROM pengaturan").fetchall()
    toko = {p['kunci']: p['nilai'] for p in pengaturan}
    conn.close()
    
    try:
        # Ukuran kertas thermal (58mm width ~ 220px at 96 DPI)
        WIDTH = 220
        MARGIN = 10
        LINE_HEIGHT = 16
        HEADER_HEIGHT = 80
        FOOTER_HEIGHT = 60
        
        # Hitung total height
        item_height = len(items) * (LINE_HEIGHT * 2 + 4)  # nama + qty x harga
        summary_height = LINE_HEIGHT * 6  # subtotal, diskon, total, bayar, kembalian, metode
        total_height = HEADER_HEIGHT + item_height + summary_height + FOOTER_HEIGHT + 40
        
        # Buat image
        img = Image.new('RGB', (WIDTH, total_height), color='#1a1d27')
        draw = ImageDraw.Draw(img)
        
        # Font (gunakan default jika custom font tidak tersedia)
        try:
            font_title = ImageFont.truetype("arial.ttf", 14)
            font_normal = ImageFont.truetype("arial.ttf", 11)
            font_small = ImageFont.truetype("arial.ttf", 9)
        except:
            font_title = ImageFont.load_default()
            font_normal = ImageFont.load_default()
            font_small = ImageFont.load_default()
        
        y = MARGIN
        
        # Header Toko
        nama_toko = toko.get('nama_toko', 'TOKO')
        draw.text((WIDTH//2, y), nama_toko, fill='#f5a623', font=font_title, anchor='mt')
        y += LINE_HEIGHT + 5
        
        alamat = toko.get('alamat', '')
        if alamat:
            draw.text((WIDTH//2, y), alamat, fill='#8891a8', font=font_small, anchor='mt')
            y += LINE_HEIGHT
        
        telp = toko.get('telp', '')
        if telp:
            draw.text((WIDTH//2, y), f'Telp: {telp}', fill='#8891a8', font=font_small, anchor='mt')
            y += LINE_HEIGHT
        
        y += 10
        draw.line([(MARGIN, y), (WIDTH-MARGIN, y)], fill='#2e3244', width=1)
        y += 10
        
        # Info Transaksi
        waktu = datetime.strptime(trx['waktu'], '%Y-%m-%d %H:%M:%S').strftime('%d/%m/%Y %H:%M')
        draw.text((MARGIN, y), f"No: {trx['no_trx']}", fill='#f0f0f8', font=font_small)
        y += LINE_HEIGHT
        draw.text((MARGIN, y), f"Waktu: {waktu}", fill='#f0f0f8', font=font_small)
        y += LINE_HEIGHT
        
        if trx.get('kasir'):
            draw.text((MARGIN, y), f"Kasir: {trx['kasir']}", fill='#f0f0f8', font=font_small)
            y += LINE_HEIGHT
        
        if trx.get('pelanggan_nama'):
            draw.text((MARGIN, y), f"Pelanggan: {trx['pelanggan_nama']}", fill='#f0f0f8', font=font_small)
            y += LINE_HEIGHT
        
        y += 5
        draw.line([(MARGIN, y), (WIDTH-MARGIN, y)], fill='#2e3244', width=1)
        y += 10
        
        # Items
        for item in items:
            # Nama produk (wrap jika terlalu panjang)
            nama = item['nama_produk'][:25]
            draw.text((MARGIN, y), f"{item['emoji']} {nama}", fill='#f0f0f8', font=font_normal)
            y += LINE_HEIGHT
            
            # Qty x Harga = Subtotal
            qty_harga = f"{item['qty']} x {item['harga']:,}".replace(',', '.')
            subtotal = f"{item['subtotal']:,}".replace(',', '.')
            draw.text((MARGIN + 10, y), qty_harga, fill='#8891a8', font=font_small)
            draw.text((WIDTH-MARGIN, y), subtotal, fill='#f0f0f8', font=font_normal, anchor='rt')
            y += LINE_HEIGHT + 4
        
        y += 5
        draw.line([(MARGIN, y), (WIDTH-MARGIN, y)], fill='#2e3244', width=1)
        y += 10
        
        # Summary
        def draw_row(label, value, color='#f0f0f8', bold=False):
            nonlocal y
            font = font_normal if not bold else font_title
            draw.text((MARGIN, y), label, fill='#8891a8', font=font_small)
            draw.text((WIDTH-MARGIN, y), value, fill=color, font=font, anchor='rt')
            y += LINE_HEIGHT
        
        subtotal = f"Rp {trx['subtotal']:,}".replace(',', '.')
        draw_row('Subtotal', subtotal)
        
        if trx['diskon'] > 0:
            diskon = f"- Rp {trx['diskon']:,}".replace(',', '.')
            draw_row('Diskon', diskon, color='#3dffa0')
        
        total = f"Rp {trx['total']:,}".replace(',', '.')
        draw_row('TOTAL', total, color='#f5a623', bold=True)
        
        bayar = f"Rp {trx['bayar']:,}".replace(',', '.')
        draw_row('Bayar', bayar)
        
        kembalian = f"Rp {trx['kembalian']:,}".replace(',', '.')
        draw_row('Kembalian', kembalian, color='#3dffa0')
        
        metode = (trx.get('metode_bayar') or 'tunai').upper()
        draw_row('Metode', metode)
        
        y += 5
        draw.line([(MARGIN, y), (WIDTH-MARGIN, y)], fill='#2e3244', width=1)
        y += 10
        
        # Footer
        pesan = toko.get('pesan_struk', 'Terima kasih!')
        draw.text((WIDTH//2, y), pesan, fill='#8891a8', font=font_small, anchor='mt')
        y += LINE_HEIGHT + 5
        
        draw.text((WIDTH//2, y), '--- KasirToko ---', fill='#f5a623', font=font_small, anchor='mt')
        
        # Save to buffer
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        
        filename = f"struk-{trx['no_trx']}.png"
        return send_file(
            buffer,
            mimetype='image/png',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        import traceback
        print(f"Error generating struk image: {e}")
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500


# ═════════════════════════════════════
#  API: BARCODE GENERATOR
# ═════════════════════════════════════
@app.route('/api/barcode/generate', methods=['POST'])
@pemilik_required
def generate_barcode():
    """Generate barcode image untuk produk."""
    try:
        from barcode import EAN13, Code128
        from barcode.writer import ImageWriter
        from PIL import Image
    except ImportError:
        return jsonify({'error': 'Library barcode tidak tersedia. Install: pip install python-barcode pillow'}), 500
    
    d = request.json
    code = d.get('code', '').strip()
    format_type = d.get('format', 'code128')  # ean13 atau code128
    
    if not code:
        return jsonify({'error': 'Kode barcode wajib diisi'}), 400
    
    try:
        # Buat barcode
        if format_type == 'ean13':
            # EAN13 harus 12-13 digit
            if not code.isdigit():
                return jsonify({'error': 'EAN13 hanya boleh angka'}), 400
            # Pad dengan 0 di depan jika kurang dari 12 digit
            code = code.zfill(12)[:12]
            barcode_obj = EAN13(code, writer=ImageWriter())
        else:
            # Code128 support alphanumeric
            barcode_obj = Code128(code, writer=ImageWriter())
        
        # Simpan ke buffer
        buffer = io.BytesIO()
        barcode_obj.write(buffer, options={
            'module_height': 15,
            'module_width': 0.5,
            'quiet_zone': 6,
            'font_size': 12,
            'text_distance': 5
        })
        buffer.seek(0)
        
        # Konversi ke PNG dengan PIL untuk optimasi
        img = Image.open(buffer)
        output = io.BytesIO()
        img.save(output, format='PNG')
        output.seek(0)
        
        return send_file(
            output,
            mimetype='image/png',
            as_attachment=True,
            download_name=f'barcode-{code}.png'
        )
        
    except Exception as e:
        return jsonify({'error': f'Gagal generate barcode: {str(e)}'}), 500


@app.route('/api/barcode/print-sheet', methods=['POST'])
@pemilik_required
def print_barcode_sheet():
    """Generate sheet barcode untuk multiple produk (printable A4)."""
    try:
        from barcode import Code128
        from barcode.writer import ImageWriter
        from PIL import Image
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image as RLImage
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import cm
    except ImportError:
        return jsonify({'error': 'Library tidak tersedia'}), 500
    
    items = request.json.get('items', [])  # [{id, nama, barcode, harga, qty}]
    
    if not items:
        return jsonify({'error': 'Tidak ada item untuk diprint'}), 400
    
    try:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=1*cm,
            leftMargin=1*cm,
            topMargin=1*cm,
            bottomMargin=1*cm
        )
        
        elements = []
        styles = getSampleStyleSheet()
        
        # Title
        elements.append(Paragraph("LABEL BARCODE", styles['Heading1']))
        elements.append(Spacer(1, 20))
        
        # Buat grid barcode (5 kolom x 11 baris = 55 per halaman)
        from reportlab.lib.utils import ImageReader
        
        row_data = []
        table_data = []
        
        for item in items:
            code = item.get('barcode', '')
            if not code:
                continue
                
            # Generate barcode image
            barcode_obj = Code128(code, writer=ImageWriter())
            img_buffer = io.BytesIO()
            barcode_obj.write(img_buffer, options={
                'module_height': 10,
                'module_width': 0.4,
                'quiet_zone': 3,
                'font_size': 8,
                'text_distance': 3
            })
            img_buffer.seek(0)
            
            # Buat cell dengan barcode + info produk
            cell_content = [
                RLImage(img_buffer, width=2.8*cm, height=1.2*cm),
                Paragraph(f"<font size='7'>{item['nama'][:20]}</font>", styles['Normal']),
                Paragraph(f"<font size='8'><b>Rp {item['harga']:,}</b></font>".replace(',', '.'), styles['Normal'])
            ]
            
            row_data.append(cell_content)
            
            # 5 kolom per baris
            if len(row_data) == 5:
                table_data.append(row_data)
                row_data = []
        
        # Sisa item yang belum masuk
        if row_data:
            while len(row_data) < 5:
                row_data.append('')
            table_data.append(row_data)
        
        if table_data:
            table = Table(table_data, colWidths=[3.5*cm]*5, rowHeights=[2.5*cm]*len(table_data))
            table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('BOX', (0, 0), (-1, -1), 0.5, colors.grey),
                ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('LEFTPADDING', (0, 0), (-1, -1), 5),
                ('RIGHTPADDING', (0, 0), (-1, -1), 5),
                ('TOPPADDING', (0, 0), (-1, -1), 5),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ]))
            elements.append(table)
        
        doc.build(elements)
        buffer.seek(0)
        
        return send_file(
            buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name='barcode-sheet.pdf'
        )
        
    except Exception as e:
        import traceback
        return jsonify({'error': f'Gagal generate sheet: {str(e)}', 'detail': traceback.format_exc()}), 500


# ═════════════════════════════════════
#  API: STOK LOG / ADJUST STOK
# ═════════════════════════════════════
@app.route('/api/stok-log', methods=['GET'])
@pemilik_required
def get_stok_log():
    """Ambil riwayat perubahan stok dengan filter."""
    dari   = request.args.get('dari', '')
    ke     = request.args.get('ke', '')
    produk_id = request.args.get('produk_id', '')
    tipe   = request.args.get('tipe', '')  # masuk, keluar, adjust
    limit  = int(request.args.get('limit', 100))
    store_id = get_current_store_id()
    
    conn = get_db()
    sql = """
        SELECT sl.*, p.nama as produk_nama, p.emoji as produk_emoji
        FROM stok_log sl
        JOIN produk p ON p.id = sl.produk_id
        WHERE p.store_id = ?
    """
    params = [store_id]
    
    if dari:
        sql += " AND DATE(sl.waktu) >= ?"
        params.append(dari)
    if ke:
        sql += " AND DATE(sl.waktu) <= ?"
        params.append(ke)
    if produk_id:
        sql += " AND sl.produk_id = ?"
        params.append(int(produk_id))
    if tipe:
        sql += " AND sl.tipe = ?"
        params.append(tipe)
    
    sql += " ORDER BY sl.waktu DESC LIMIT ?"
    params.append(limit)
    
    rows = db_execute(conn, sql, params).fetchall()
    conn.close()
    return jsonify(rows_to_list(rows))


@app.route('/api/produk/<int:pid>/adjust-stok', methods=['POST'])
@pemilik_required
def adjust_stok(pid):
    """Adjust stok manual dengan alasan."""
    user = get_current_user()
    d = request.json
    
    stok_baru = int(d.get('stok_baru', 0))
    alasan    = d.get('alasan', '').strip()
    keterangan = d.get('keterangan', '').strip()
    
    if stok_baru < 0:
        return jsonify({'error': 'Stok tidak boleh negatif'}), 400
    if not alasan:
        return jsonify({'error': 'Alasan adjust wajib diisi'}), 400
    
    conn = get_db()
    conn.execute("BEGIN TRANSACTION")
    
    try:
        # Get produk dan stok saat ini
        prod = db_execute(conn, "SELECT * FROM produk WHERE id=? AND aktif=1", (pid,)).fetchone()
        if not prod:
            conn.rollback()
            conn.close()
            return jsonify({'error': 'Produk tidak ditemukan'}), 404
        
        stok_sebelum = prod['stok']
        stok_sesudah = stok_baru
        selisih = stok_sesudah - stok_sebelum
        
        if selisih == 0:
            conn.rollback()
            conn.close()
            return jsonify({'error': 'Tidak ada perubahan stok'}), 400
        
        # Update stok produk
        now_sql = "CURRENT_TIMESTAMP" if USE_POSTGRES else "datetime('now','localtime')"
        db_execute(conn, 
            f"UPDATE produk SET stok = ?, diubah = {now_sql} WHERE id=?",
            (stok_baru, pid)
        )
        
        # Tentukan tipe log
        tipe = 'masuk' if selisih > 0 else 'keluar'
        
        # Catat di stok_log
        db_execute(conn, 
            """INSERT INTO stok_log 
               (produk_id, tipe, jumlah, stok_sebelum, stok_sesudah, 
                alasan, keterangan, dibuat_oleh)
               VALUES (?,?,?,?,?,?,?,?)""",
            (pid, tipe, abs(selisih), stok_sebelum, stok_sesudah,
             alasan, keterangan, user['nama'])
        )
        
        conn.commit()
        
        # Return updated produk
        row = row_to_dict(db_execute(conn, "SELECT * FROM produk WHERE id=?", (pid,)).fetchone())
        conn.close()
        
        return jsonify({'ok': True, 'produk': row})
        
    except Exception as e:
        conn.rollback()
        conn.close()
        return jsonify({'error': str(e)}), 500


@app.route('/api/produk/<int:pid>/stok-history', methods=['GET'])
@pemilik_required
def get_stok_history(pid):
    """Ambil riwayat perubahan stok untuk produk tertentu."""
    limit = int(request.args.get('limit', 50))
    
    conn = get_db()
    rows = db_execute(conn, """
        SELECT sl.*, p.nama as produk_nama, p.emoji as produk_emoji
        FROM stok_log sl
        JOIN produk p ON p.id = sl.produk_id
        WHERE sl.produk_id = ?
        ORDER BY sl.waktu DESC
        LIMIT ?
    """, (pid, limit)).fetchall()
    conn.close()
    return jsonify(rows_to_list(rows))


# ─────────────────────────────────────
#  API: PELANGGAN
# ─────────────────────────────────────
@app.route('/api/pelanggan', methods=['GET'])
def get_pelanggan():
    cari = request.args.get('cari', '').strip()
    store_id = get_current_store_id()
    conn = get_db()
    sql = """
        SELECT p.*,
               COUNT(t.id)                          AS total_trx,
               COALESCE(SUM(t.total), 0)            AS total_belanja
        FROM pelanggan p
        LEFT JOIN transaksi t ON t.pelanggan_id = p.id AND t.store_id = ?
        WHERE p.store_id = ?
    """
    params = [store_id, store_id]
    if cari:
        if USE_POSTGRES:
            sql += " AND (p.nama ILIKE %s OR p.telepon ILIKE %s)"
            params.extend([f'%{cari}%', f'%{cari}%'])
        else:
            sql += " AND (p.nama LIKE ? OR p.telepon LIKE ?)"
            params.extend([f'%{cari}%', f'%{cari}%'])
    
    # GROUP BY selalu ditambahkan di luar blok if
    if USE_POSTGRES:
        sql += " GROUP BY p.id ORDER BY p.nama"
    else:
        sql += " GROUP BY p.id ORDER BY p.nama COLLATE NOCASE"
    
    rows = db_execute(conn, sql, params).fetchall()
    conn.close()
    return jsonify(rows_to_list(rows))


@app.route('/api/pelanggan', methods=['POST'])
def tambah_pelanggan():
    d    = request.json
    nama = d.get('nama', '').strip()
    if not nama:
        return jsonify({'error': 'Nama tidak boleh kosong'}), 400
    store_id = get_current_store_id()
    conn = get_db()
    cur  = db_execute(conn, 
        "INSERT INTO pelanggan (nama, telepon, alamat, catatan, store_id) VALUES (?,?,?,?,?)",
        (nama, d.get('telepon','').strip(), d.get('alamat','').strip(), d.get('catatan','').strip(), store_id)
    )
    pid = cur.lastrowid
    conn.commit()
    row = row_to_dict(db_execute(conn, "SELECT * FROM pelanggan WHERE id=?", (pid,)).fetchone())
    conn.close()
    return jsonify(row), 201


@app.route('/api/pelanggan/<int:pid>', methods=['GET'])
def get_pelanggan_detail(pid):
    store_id = get_current_store_id()
    conn = get_db()
    plg  = db_execute(conn, "SELECT * FROM pelanggan WHERE id=? AND store_id=?", (pid, store_id)).fetchone()
    if not plg:
        conn.close()
        return jsonify({'error': 'Tidak ditemukan'}), 404
    stats = row_to_dict(db_execute(conn, """
        SELECT COUNT(*) AS total_trx,
               COALESCE(SUM(total), 0) AS total_belanja,
               MAX(waktu) AS terakhir_belanja
        FROM transaksi WHERE pelanggan_id=? AND store_id=?
    """, (pid, store_id)).fetchone())
    transaksi = rows_to_list(db_execute(conn, 
        "SELECT * FROM transaksi WHERE pelanggan_id=? AND store_id=? ORDER BY waktu DESC LIMIT 30",
        (pid, store_id)
    ).fetchall())
    conn.close()
    return jsonify({'pelanggan': row_to_dict(plg), 'stats': stats, 'transaksi': transaksi})


@app.route('/api/pelanggan/<int:pid>', methods=['PUT'])
def update_pelanggan(pid):
    d    = request.json
    nama = d.get('nama', '').strip()
    if not nama:
        return jsonify({'error': 'Nama tidak boleh kosong'}), 400
    store_id = get_current_store_id()
    conn = get_db()
    db_execute(conn, 
        "UPDATE pelanggan SET nama=?, telepon=?, alamat=?, catatan=? WHERE id=? AND store_id=?",
        (nama, d.get('telepon','').strip(), d.get('alamat','').strip(), d.get('catatan','').strip(), pid, store_id)
    )
    conn.commit()
    row = row_to_dict(db_execute(conn, "SELECT * FROM pelanggan WHERE id=?", (pid,)).fetchone())
    conn.close()
    return jsonify(row)


@app.route('/api/pelanggan/<int:pid>', methods=['DELETE'])
def hapus_pelanggan(pid):
    store_id = get_current_store_id()
    conn = get_db()
    db_execute(conn, "UPDATE transaksi SET pelanggan_id=NULL WHERE pelanggan_id=? AND store_id=?", (pid, store_id))
    db_execute(conn, "DELETE FROM pelanggan WHERE id=? AND store_id=?", (pid, store_id))
    conn.commit()
    conn.close()
    return jsonify({'ok': True})


# ─────────────────────────────────────
#  API: LAPORAN & STATISTIK
# ─────────────────────────────────────
@app.route('/api/laporan/hari-ini', methods=['GET'])
@pemilik_required
def laporan_hari_ini():
    conn = get_db()
    stats = db_execute(conn, """
        SELECT
            COUNT(*)        AS total_transaksi,
            COALESCE(SUM(total),0)     AS omzet,
            COALESCE(SUM(diskon),0)    AS total_diskon,
            COALESCE(AVG(total),0)     AS rata_rata
        FROM transaksi
        WHERE DATE(waktu) = DATE('now','localtime')
          AND COALESCE(status, 'aktif') = 'aktif'
    """).fetchone()

    top_produk = db_execute(conn, """
        SELECT ti.nama_produk AS nama, ti.emoji,
               SUM(ti.qty) AS total_qty,
               SUM(ti.subtotal) AS total_nilai
        FROM transaksi_item ti
        JOIN transaksi t ON t.id = ti.transaksi_id
        WHERE DATE(t.waktu) = DATE('now','localtime')
          AND COALESCE(t.status, 'aktif') = 'aktif'
        GROUP BY ti.produk_id, ti.nama_produk
        ORDER BY total_nilai DESC
        LIMIT 5
    """).fetchall()

    conn.close()
    return jsonify({
        'stats': row_to_dict(stats),
        'top_produk': rows_to_list(top_produk)
    })

@app.route('/api/laporan/rentang', methods=['GET'])
@pemilik_required
def laporan_rentang():
    dari = request.args.get('dari', '')
    ke   = request.args.get('ke', '')
    conn = get_db()

    # Filter: hanya transaksi aktif (exclude void)
    sql_filter = "WHERE COALESCE(status, 'aktif') = 'aktif'"
    params = []
    if dari:
        sql_filter += " AND DATE(waktu) >= ?"
        params.append(dari)
    if ke:
        sql_filter += " AND DATE(waktu) <= ?"
        params.append(ke)

    stats = db_execute(conn, f"""
        SELECT COUNT(*) AS total_transaksi,
               COALESCE(SUM(total),0) AS omzet,
               COALESCE(SUM(diskon),0) AS total_diskon,
               COALESCE(AVG(total),0) AS rata_rata
        FROM transaksi {sql_filter}
    """, params).fetchone()

    harian = db_execute(conn, f"""
        SELECT DATE(waktu) AS tanggal,
               COUNT(*) AS transaksi,
               SUM(total) AS omzet
        FROM transaksi {sql_filter}
        GROUP BY DATE(waktu)
        ORDER BY tanggal DESC
    """, params).fetchall()

    conn.close()
    return jsonify({
        'stats': row_to_dict(stats),
        'harian': rows_to_list(harian)
    })


# ═════════════════════════════════════
#  API: GRAFIK / CHART DATA
# ═════════════════════════════════════
@app.route('/api/laporan/chart', methods=['GET'])
@pemilik_required
def laporan_chart():
    """Data untuk grafik penjualan (harian/mingguan/bulanan)."""
    tipe = request.args.get('tipe', 'harian')  # harian, mingguan, bulanan
    dari = request.args.get('dari', '')
    ke   = request.args.get('ke', '')
    
    conn = get_db()
    
    if tipe == 'harian':
        # Default: 30 hari terakhir jika tidak ada filter
        if not dari:
            dari = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        if not ke:
            ke = datetime.now().strftime('%Y-%m-%d')
            
        rows = db_execute(conn, """
            SELECT 
                DATE(waktu) as label,
                COUNT(*) as transaksi,
                COALESCE(SUM(total), 0) as omzet,
                COALESCE(SUM(diskon), 0) as diskon
            FROM transaksi
            WHERE DATE(waktu) >= ? AND DATE(waktu) <= ?
              AND COALESCE(status, 'aktif') = 'aktif'
            GROUP BY DATE(waktu)
            ORDER BY DATE(waktu) ASC
        """, (dari, ke)).fetchall()
            
    elif tipe == 'mingguan':
        # Default: 12 minggu terakhir
        if not dari:
            dari = (datetime.now() - timedelta(weeks=12)).strftime('%Y-%m-%d')
        if not ke:
            ke = datetime.now().strftime('%Y-%m-%d')
            
        if USE_POSTGRES:
            rows = db_execute(conn, """
                SELECT 
                    DATE_TRUNC('week', waktu)::date || ' - ' || 
                    (DATE_TRUNC('week', waktu) + interval '6 days')::date as label,
                    EXTRACT(WEEK FROM waktu) as week_num,
                    COUNT(*) as transaksi,
                    COALESCE(SUM(total), 0) as omzet,
                    COALESCE(SUM(diskon), 0) as diskon
                FROM transaksi
                WHERE DATE(waktu) >= ? AND DATE(waktu) <= ?
                  AND COALESCE(status, 'aktif') = 'aktif'
                GROUP BY DATE_TRUNC('week', waktu), EXTRACT(WEEK FROM waktu)
                ORDER BY DATE_TRUNC('week', waktu) ASC
            """, (dari, ke)).fetchall()
        else:
            rows = db_execute(conn, """
                SELECT 
                    strftime('%W', waktu) as week_num,
                    'Minggu ' || strftime('%W', waktu) as label,
                    COUNT(*) as transaksi,
                    COALESCE(SUM(total), 0) as omzet,
                    COALESCE(SUM(diskon), 0) as diskon
                FROM transaksi
                WHERE DATE(waktu) >= ? AND DATE(waktu) <= ?
                  AND COALESCE(status, 'aktif') = 'aktif'
                GROUP BY strftime('%W', waktu)
                ORDER BY strftime('%W', waktu) ASC
            """, (dari, ke)).fetchall()
            
    elif tipe == 'bulanan':
        # Default: 12 bulan terakhir
        if not dari:
            dari = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
        if not ke:
            ke = datetime.now().strftime('%Y-%m-%d')
            
        rows = db_execute(conn, """
            SELECT 
                strftime('%Y-%m', waktu) as label,
                strftime('%m/%Y', waktu) as bulan,
                COUNT(*) as transaksi,
                COALESCE(SUM(total), 0) as omzet,
                COALESCE(SUM(diskon), 0) as diskon
            FROM transaksi
            WHERE DATE(waktu) >= ? AND DATE(waktu) <= ?
              AND COALESCE(status, 'aktif') = 'aktif'
            GROUP BY strftime('%Y-%m', waktu)
            ORDER BY strftime('%Y-%m', waktu) ASC
        """, (dari, ke)).fetchall()
    else:
        conn.close()
        return jsonify({'error': 'Tipe tidak valid'}), 400
    
    # Format data untuk Chart.js
    labels = [r['label'] for r in rows]
    data_transaksi = [r['transaksi'] for r in rows]
    data_omzet = [r['omzet'] for r in rows]
    data_diskon = [r['diskon'] for r in rows]
    
    conn.close()
    return jsonify({
        'tipe': tipe,
        'labels': labels,
        'datasets': {
            'transaksi': data_transaksi,
            'omzet': data_omzet,
            'diskon': data_diskon
        }
    })


# ═════════════════════════════════════
#  API: LAPORAN STOK
# ═════════════════════════════════════
@app.route('/api/laporan/stok', methods=['GET'])
@pemilik_required
def laporan_stok():
    """Laporan stok: hampir habis, opname, dan statistik."""
    mode = request.args.get('mode', 'semua')  # semua, hampir_habis, opname
    store_id = get_current_store_id()
    
    conn = get_db()
    
    # Base query dengan store_id filter - FIX Bug #11: hapus OR IS NULL
    base_where = "WHERE p.store_id = ? AND p.aktif = 1"
    params = [store_id]
    
    if mode == 'hampir_habis':
        # Stok <= stok_min atau stok <= 5 jika stok_min = 0
        sql = f"""
            SELECT p.*, 
                   COALESCE(SUM(CASE WHEN sl.tipe = 'masuk' THEN sl.jumlah ELSE 0 END), 0) as total_masuk,
                   COALESCE(SUM(CASE WHEN sl.tipe = 'keluar' THEN sl.jumlah ELSE 0 END), 0) as total_keluar
            FROM produk p
            LEFT JOIN stok_log sl ON sl.produk_id = p.id
            {base_where}
              AND (p.stok <= p.stok_min OR (p.stok_min = 0 AND p.stok <= 5))
            GROUP BY p.id
            ORDER BY p.stok ASC
        """
    elif mode == 'opname':
        # Semua produk untuk stok opname
        sql = f"""
            SELECT p.*,
                   COALESCE(SUM(CASE WHEN sl.tipe = 'masuk' THEN sl.jumlah ELSE 0 END), 0) as total_masuk,
                   COALESCE(SUM(CASE WHEN sl.tipe = 'keluar' THEN sl.jumlah ELSE 0 END), 0) as total_keluar,
                   COUNT(DISTINCT sl.id) as total_perubahan
            FROM produk p
            LEFT JOIN stok_log sl ON sl.produk_id = p.id
            {base_where}
            GROUP BY p.id
            ORDER BY p.kategori, p.nama
        """
    else:
        # Semua produk aktif
        sql = f"""
            SELECT p.*,
                   COALESCE(SUM(CASE WHEN sl.tipe = 'masuk' THEN sl.jumlah ELSE 0 END), 0) as total_masuk,
                   COALESCE(SUM(CASE WHEN sl.tipe = 'keluar' THEN sl.jumlah ELSE 0 END), 0) as total_keluar
            FROM produk p
            LEFT JOIN stok_log sl ON sl.produk_id = p.id
            {base_where}
            GROUP BY p.id
            ORDER BY p.kategori, p.nama
        """
    
    rows = db_execute(conn, sql, tuple(params)).fetchall()
    
    # Stats - dihitung via SQL untuk performance
    stats_sql = f"""
        SELECT 
            COUNT(*) as total_produk,
            SUM(CASE WHEN p.stok <= p.stok_min OR (p.stok_min = 0 AND p.stok <= 5) THEN 1 ELSE 0 END) as hampir_habis,
            SUM(CASE WHEN p.stok = 0 THEN 1 ELSE 0 END) as stok_nol,
            SUM(p.stok * p.harga_modal) as total_nilai
        FROM produk p
        {base_where}
    """
    stats = db_execute(conn, stats_sql, tuple(params)).fetchone()
    total_produk = stats['total_produk'] if stats else 0
    hampir_habis = stats['hampir_habis'] if stats else 0
    stok_nol = stats['stok_nol'] if stats else 0
    total_nilai = stats['total_nilai'] if stats else 0
    
    conn.close()
    
    return jsonify({
        'mode': mode,
        'stats': {
            'total_produk': total_produk,
            'hampir_habis': hampir_habis,
            'stok_nol': stok_nol,
            'total_nilai_stok': total_nilai
        },
        'produk': [row_to_dict(r) for r in rows]
    })


# ═════════════════════════════════════
#  API: LAPORAN KEUANGAN
# ═════════════════════════════════════
@app.route('/api/laporan/keuangan', methods=['GET'])
@pemilik_required
def laporan_keuangan():
    """Laporan keuangan: arus kas, laba/rugi."""
    dari = request.args.get('dari', '')
    ke   = request.args.get('ke', '')
    store_id = get_current_store_id()
    
    if not dari:
        dari = datetime.now().strftime('%Y-%m-%d')
    if not ke:
        ke = datetime.now().strftime('%Y-%m-%d')
    
    conn = get_db()
    
    # Arus Kas dari tabel kas
    kas_masuk = db_execute(conn, """
        SELECT COALESCE(SUM(jumlah), 0) as total, COUNT(*) as count
        FROM kas
        WHERE tipe = 'pemasukan'
          AND DATE(waktu) >= ? AND DATE(waktu) <= ?
          AND (store_id = ? OR ? IS NULL)
    """, (dari, ke, store_id, store_id)).fetchone()
    
    kas_keluar = db_execute(conn, """
        SELECT COALESCE(SUM(jumlah), 0) as total, COUNT(*) as count
        FROM kas
        WHERE tipe = 'pengeluaran'
          AND DATE(waktu) >= ? AND DATE(waktu) <= ?
          AND (store_id = ? OR ? IS NULL)
    """, (dari, ke, store_id, store_id)).fetchone()
    
    # Pemasukan dari transaksi (penjualan)
    penjualan = db_execute(conn, """
        SELECT 
            COALESCE(SUM(total), 0) as total,
            COALESCE(SUM(diskon), 0) as diskon,
            COUNT(*) as count
        FROM transaksi
        WHERE DATE(waktu) >= ? AND DATE(waktu) <= ?
          AND COALESCE(status, 'aktif') = 'aktif'
          AND (store_id = ? OR ? IS NULL)
    """, (dari, ke, store_id, store_id)).fetchone()
    
    # Laba/Rugi (Omzet - Modal)
    # Hitung laba kotor dari transaksi_item
    laba = db_execute(conn, """
        SELECT COALESCE(SUM(
            (ti.harga - COALESCE(p.harga_modal, 0)) * ti.qty
        ), 0) as laba_kotor
        FROM transaksi_item ti
        JOIN transaksi t ON t.id = ti.transaksi_id
        LEFT JOIN produk p ON p.id = ti.produk_id
        WHERE DATE(t.waktu) >= ? AND DATE(t.waktu) <= ?
          AND COALESCE(t.status, 'aktif') = 'aktif'
          AND (t.store_id = ? OR ? IS NULL)
    """, (dari, ke, store_id, store_id)).fetchone()
    
    # Metode pembayaran breakdown
    metode = db_execute(conn, """
        SELECT metode_bayar, COALESCE(SUM(total), 0) as total, COUNT(*) as count
        FROM transaksi
        WHERE DATE(waktu) >= ? AND DATE(waktu) <= ?
          AND COALESCE(status, 'aktif') = 'aktif'
          AND (store_id = ? OR ? IS NULL)
        GROUP BY metode_bayar
    """, (dari, ke, store_id, store_id)).fetchall()
    
    # Harian breakdown
    harian = db_execute(conn, """
        SELECT 
            DATE(waktu) as tanggal,
            COALESCE(SUM(total), 0) as omzet,
            COALESCE(SUM(diskon), 0) as diskon,
            COUNT(*) as transaksi
        FROM transaksi
        WHERE DATE(waktu) >= ? AND DATE(waktu) <= ?
          AND COALESCE(status, 'aktif') = 'aktif'
          AND (store_id = ? OR ? IS NULL)
        GROUP BY DATE(waktu)
        ORDER BY DATE(waktu) ASC
    """, (dari, ke, store_id, store_id)).fetchall()
    
    conn.close()
    
    return jsonify({
        'periode': {'dari': dari, 'ke': ke},
        'arus_kas': {
            'pemasukan': {'total': kas_masuk['total'], 'count': kas_masuk['count']},
            'pengeluaran': {'total': kas_keluar['total'], 'count': kas_keluar['count']},
            'saldo': kas_masuk['total'] - kas_keluar['total']
        },
        'penjualan': {
            'omzet': penjualan['total'],
            'diskon': penjualan['diskon'],
            'net': penjualan['total'] - penjualan['diskon'],
            'transaksi': penjualan['count']
        },
        'laba_rugi': {
            'laba_kotor': laba['laba_kotor'],
            'estimasi_net': laba['laba_kotor'] - kas_keluar['total']
        },
        'metode_pembayaran': [row_to_dict(m) for m in metode],
        'harian': [row_to_dict(h) for h in harian]
    })


# ─────────────────────────────────────
#  API: EXPORT PDF LAPORAN
# ─────────────────────────────────────
@app.route('/api/export/pdf', methods=['GET'])
@pemilik_required
def export_pdf():
    """Export laporan transaksi ke PDF."""
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
    except ImportError:
        return jsonify({'error': 'Library reportlab tidak tersedia'}), 500
    
    dari = request.args.get('dari', '')
    ke   = request.args.get('ke', '')
    
    conn = get_db()
    
    # Get transaksi data
    sql = """
        SELECT t.*, COALESCE(p.nama, '') AS pelanggan_nama
        FROM transaksi t
        LEFT JOIN pelanggan p ON p.id = t.pelanggan_id
        WHERE COALESCE(t.status, 'aktif') = 'aktif'
    """
    params = []
    if dari:
        sql += " AND DATE(t.waktu) >= ?"
        params.append(dari)
    if ke:
        sql += " AND DATE(t.waktu) <= ?"
        params.append(ke)
    sql += " ORDER BY t.waktu DESC LIMIT 500"
    
    transaksi = db_execute(conn, sql, params).fetchall()
    
    # Get summary stats
    stats = db_execute(conn, f"""
        SELECT 
            COUNT(*) as total_transaksi,
            COALESCE(SUM(total), 0) as total_omzet,
            COALESCE(SUM(diskon), 0) as total_diskon,
            COALESCE(AVG(total), 0) as rata_rata
        FROM transaksi
        WHERE COALESCE(status, 'aktif') = 'aktif'
        {' AND DATE(waktu) >= ?' if dari else ''}
        {' AND DATE(waktu) <= ?' if ke else ''}
    """, [p for p in [dari, ke] if p]).fetchone()
    
    # Create PDF
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=1.5*cm,
        leftMargin=1.5*cm,
        topMargin=1.5*cm,
        bottomMargin=1.5*cm
    )
    
    elements = []
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#f5a623'),
        spaceAfter=20,
        alignment=1  # Center
    )
    
    # Title
    periode = f"Periode: {dari or 'Awal'} s/d {ke or 'Sekarang'}"
    elements.append(Paragraph("LAPORAN PENJUALAN", title_style))
    elements.append(Paragraph(periode, styles['Normal']))
    elements.append(Spacer(1, 20))
    
    # Summary table
    summary_data = [
        ['Ringkasan', ''],
        ['Total Transaksi', str(stats['total_transaksi'])],
        ['Total Omzet', f"Rp {stats['total_omzet']:,.0f}".replace(',', '.')],
        ['Total Diskon', f"Rp {stats['total_diskon']:,.0f}".replace(',', '.')],
        ['Rata-rata per Transaksi', f"Rp {stats['rata_rata']:,.0f}".replace(',', '.')]
    ]
    
    summary_table = Table(summary_data, colWidths=[doc.width/2]*2)
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f5a623')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#1a1d27')),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.white),
        ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#2e3244')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 30))
    
    # Transaksi detail
    if transaksi:
        elements.append(Paragraph("Detail Transaksi", styles['Heading2']))
        elements.append(Spacer(1, 10))
        
        detail_data = [['No', 'Waktu', 'No. Trx', 'Pelanggan', 'Item', 'Total', 'Metode']]
        for i, t in enumerate(transaksi[:100], 1):  # Limit 100 for PDF
            item_count = db_execute(conn, 
                "SELECT COUNT(*) as c FROM transaksi_item WHERE transaksi_id=?", (t['id'],)
            ).fetchone()['c']
            detail_data.append([
                str(i),
                t['waktu'][:16],
                t['no_trx'],
                t['pelanggan_nama'] or '-',
                f"{item_count} item",
                f"Rp {t['total']:,.0f}".replace(',', '.'),
                t.get('metode_bayar', 'tunai').upper()
            ])
        
        # Build detail table setelah loop selesai dan data terkumpul
        detail_table = Table(detail_data, colWidths=[0.6*cm, 2.8*cm, 2.5*cm, 2.5*cm, 1.5*cm, 2.2*cm, 1.5*cm])
        detail_table = Table(detail_data, colWidths=[0.6*cm, 2.8*cm, 2.5*cm, 2.5*cm, 1.5*cm, 2.2*cm, 1.5*cm])
        detail_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2e3244')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#f5a623')),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#1a1d27')),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.white),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#2e3244')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 5),
            ('RIGHTPADDING', (0, 0), (-1, -1), 5),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#1a1d27'), colors.HexColor('#242736')])
        ]))
        elements.append(detail_table)
    
    # Footer
    elements.append(Spacer(1, 30))
    footer_text = f"Dibuat pada: {datetime.now().strftime('%d %B %Y %H:%M')} oleh {get_current_user()['nama']}"
    elements.append(Paragraph(footer_text, styles['Normal']))
    
    # Tutup koneksi database setelah semua data diambil
    conn.close()
    
    doc.build(elements)
    buffer.seek(0)
    
    filename = f"laporan-penjualan-{dari or 'semua'}-{ke or 'semua'}.pdf"
    return send_file(
        buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=filename
    )


# ─────────────────────────────────────
#  API: EXPORT CSV
# ─────────────────────────────────────
@app.route('/api/export/csv', methods=['GET'])
@pemilik_required
def export_csv():
    dari = request.args.get('dari', '')
    ke   = request.args.get('ke', '')

    conn = get_db()
    sql = """
        SELECT t.no_trx, t.waktu, ti.nama_produk, ti.emoji,
               ti.qty, ti.harga, ti.subtotal,
               t.diskon, t.total, t.bayar, t.kembalian
        FROM transaksi_item ti
        JOIN transaksi t ON t.id = ti.transaksi_id
        WHERE 1=1
    """
    params = []
    if dari:
        sql += " AND DATE(t.waktu) >= ?"
        params.append(dari)
    if ke:
        sql += " AND DATE(t.waktu) <= ?"
        params.append(ke)
    sql += " ORDER BY t.waktu DESC"

    rows = db_execute(conn, sql, params).fetchall()
    conn.close()

    output = io.StringIO()
    output.write('\ufeff')  # BOM untuk Excel
    writer = csv.writer(output)
    writer.writerow(['No Transaksi','Waktu','Produk','Qty',
                     'Harga Satuan','Subtotal Item','Diskon Trx',
                     'Total','Bayar','Kembalian'])
    for r in rows:
        writer.writerow([r['no_trx'], r['waktu'], r['nama_produk'],
                         r['qty'], r['harga'], r['subtotal'],
                         r['diskon'], r['total'], r['bayar'], r['kembalian']])

    output.seek(0)
    tanggal = datetime.now().strftime('%Y-%m-%d')
    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8-sig')),
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'laporan-kasir-{tanggal}.csv'
    )


# ─────────────────────────────────────
#  API: EXPORT / IMPORT PRODUK CSV
# ─────────────────────────────────────

@app.route('/api/produk/export-csv', methods=['GET'])
@pemilik_required
def export_produk_csv():
    """Export semua produk aktif ke CSV — siap diedit di Excel lalu di-import kembali."""
    store_id = get_current_store_id()
    conn = get_db()
    rows = db_execute(conn, 
        "SELECT nama, kategori, harga, stok, emoji, harga_modal, stok_min, diskon FROM produk WHERE aktif=1 AND store_id=? ORDER BY kategori, nama",
        (store_id,)
    ).fetchall()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['nama', 'kategori', 'harga', 'stok', 'emoji', 'harga_modal', 'stok_min', 'diskon'])
    for r in rows:
        writer.writerow([r['nama'], r['kategori'], r['harga'], r['stok'], r['emoji'],
                         r['harga_modal'] or 0, r['stok_min'] or 0, r['diskon'] or 0])

    tanggal = datetime.now().strftime('%Y-%m-%d')
    return send_file(
        io.BytesIO(('\ufeff' + output.getvalue()).encode('utf-8-sig')),
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'produk-kasirtoko-{tanggal}.csv'
    )


@app.route('/api/produk/import-csv', methods=['POST'])
@pemilik_required
def import_produk_csv():
    """
    Import produk dari CSV.
    Mode: 'tambah'  → hanya tambah produk baru (skip yang sudah ada berdasarkan nama)
          'timpa'   → update stok+harga produk yang sudah ada, tambah yang baru
          'ganti'   → nonaktifkan semua produk lama, masukkan semua dari CSV (fresh)
    """
    if 'file' not in request.files:
        return jsonify({'error': 'File tidak ditemukan'}), 400

    file   = request.files['file']
    mode   = request.form.get('mode', 'tambah')   # tambah | timpa | ganti

    if not file.filename.endswith('.csv'):
        return jsonify({'error': 'Hanya file .csv yang diterima'}), 400

    # Baca isi file — coba beberapa encoding umum
    raw = file.read()
    for enc in ['utf-8-sig', 'utf-8', 'latin-1', 'cp1252']:
        try:
            content = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        return jsonify({'error': 'Encoding file tidak dikenali'}), 400

    reader  = csv.DictReader(io.StringIO(content))
    kolom_wajib = {'nama', 'kategori', 'harga', 'stok'}

    # Validasi header
    if not reader.fieldnames:
        return jsonify({'error': 'File CSV kosong atau header tidak ditemukan'}), 400

    header_lower = {k.strip().lower() for k in reader.fieldnames}
    missing = kolom_wajib - header_lower
    if missing:
        return jsonify({'error': f'Kolom wajib tidak ada: {", ".join(missing)}'}), 400

    # Normalise key (case-insensitive, strip spasi)
    def norm(row):
        return {k.strip().lower(): v.strip() for k, v in row.items()}

    rows_csv = [norm(r) for r in reader]
    if not rows_csv:
        return jsonify({'error': 'Tidak ada data di file CSV'}), 400

    # Validasi tiap baris
    errors = []
    valid  = []
    for i, r in enumerate(rows_csv, start=2):   # baris 1 = header
        nama = r.get('nama', '').strip()
        kat  = r.get('kategori', '').strip()
        if not nama:
            errors.append(f'Baris {i}: kolom "nama" kosong')
            continue
        if not kat:
            errors.append(f'Baris {i}: kolom "kategori" kosong')
            continue
        try:
            harga      = int(float(r.get('harga', 0)))
            stok       = int(float(r.get('stok',  0)))
            harga_modal= int(float(r.get('harga_modal', 0) or 0))
            stok_min   = int(float(r.get('stok_min', 0) or 0))
            diskon     = int(float(r.get('diskon', 0) or 0))
        except ValueError:
            errors.append(f'Baris {i} ({nama}): harga/stok harus angka')
            continue
        if harga < 0:
            errors.append(f'Baris {i} ({nama}): harga tidak boleh negatif')
            continue
        diskon = max(0, min(100, diskon))
        emoji  = r.get('emoji', '[BOX]').strip() or '[BOX]'
        valid.append({'nama': nama, 'kategori': kat, 'harga': harga, 'stok': stok, 'emoji': emoji,
                      'harga_modal': harga_modal, 'stok_min': stok_min, 'diskon': diskon})

    if not valid:
        return jsonify({'error': 'Semua baris tidak valid', 'detail': errors}), 400

    conn = get_db()
    store_id = get_current_store_id()
    tambah = 0
    update = 0
    skip   = 0
    now_sql = "CURRENT_TIMESTAMP" if USE_POSTGRES else "datetime('now','localtime')"

    try:
        if mode == 'ganti':
            # Nonaktifkan semua produk lama di toko ini
            db_execute(conn, "UPDATE produk SET aktif=0 WHERE store_id=?", (store_id,))

        for p in valid:
            existing = db_execute(conn, 
                "SELECT id FROM produk WHERE LOWER(nama)=LOWER(?) AND aktif=1 AND store_id=?",
                (p['nama'], store_id)
            ).fetchone()

            if existing:
                if mode == 'timpa':
                    db_execute(conn, 
                        f"UPDATE produk SET harga=?, stok=?, emoji=?, kategori=?, harga_modal=?, stok_min=?, diskon=?, diubah={now_sql} WHERE id=?",
                        (p['harga'], p['stok'], p['emoji'], p['kategori'],
                         p['harga_modal'], p['stok_min'], p['diskon'], existing['id'])
                    )
                    update += 1
                elif mode == 'ganti':
                    # Reaktifkan dan update
                    db_execute(conn, 
                        f"UPDATE produk SET harga=?, stok=?, emoji=?, kategori=?, harga_modal=?, stok_min=?, diskon=?, aktif=1, diubah={now_sql} WHERE id=?",
                        (p['harga'], p['stok'], p['emoji'], p['kategori'],
                         p['harga_modal'], p['stok_min'], p['diskon'], existing['id'])
                    )
                    update += 1
                else:
                    # mode tambah → skip yang sudah ada
                    skip += 1
            else:
                # Cek apakah ada produk nonaktif dengan nama sama → reaktifkan
                deleted = db_execute(conn, 
                    "SELECT id FROM produk WHERE LOWER(nama)=LOWER(?) AND aktif=0 AND store_id=?",
                    (p['nama'], store_id)
                ).fetchone()
                if deleted:
                    db_execute(conn, 
                        f"UPDATE produk SET harga=?, stok=?, emoji=?, kategori=?, harga_modal=?, stok_min=?, diskon=?, aktif=1, diubah={now_sql} WHERE id=?",
                        (p['harga'], p['stok'], p['emoji'], p['kategori'],
                         p['harga_modal'], p['stok_min'], p['diskon'], deleted['id'])
                    )
                else:
                    db_execute(conn, 
                        "INSERT INTO produk (nama, harga, stok, emoji, kategori, harga_modal, stok_min, diskon, store_id) VALUES (?,?,?,?,?,?,?,?,?)",
                        (p['nama'], p['harga'], p['stok'], p['emoji'], p['kategori'],
                         p['harga_modal'], p['stok_min'], p['diskon'], store_id)
                    )
                tambah += 1

        conn.commit()
    except Exception as e:
        conn.rollback()
        conn.close()
        return jsonify({'error': f'Gagal menyimpan: {str(e)}'}), 500

    conn.close()
    return jsonify({
        'ok': True,
        'mode': mode,
        'tambah': tambah,
        'update': update,
        'skip': skip,
        'error_baris': errors,
        'total_valid': len(valid)
    })


@app.route('/api/produk/template-csv', methods=['GET'])
@pemilik_required
def template_produk_csv():
    """Download template CSV kosong dengan contoh baris."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['nama', 'kategori', 'harga', 'stok', 'emoji', 'harga_modal', 'stok_min', 'diskon'])
    # Contoh baris
    contoh = [
        ['Indomie Goreng',    'Makanan',    3500,  100, '🍜', 2500,  10, 0],
        ['Aqua 600ml',        'Minuman',    4000,   50, '💧', 2800,   5, 0],
        ['Gula 1kg',          'Sembako',   14000,   25, '🍬', 11000,  5, 0],
        ['Sabun Lifebuoy',    'Kebersihan', 5000,   30, '🧼', 3500,   5, 0],
        ['Gudang Garam 12',   'Rokok',     22000,   20, '🚬', 18000,  5, 0],
    ]
    for c in contoh:
        writer.writerow(c)

    return send_file(
        io.BytesIO(('\ufeff' + output.getvalue()).encode('utf-8-sig')),
        mimetype='text/csv',
        as_attachment=True,
        download_name='template-produk-kasirtoko.csv'
    )


# ─────────────────────────────────────
#  API: PENGGUNA (manajemen akun)
# ─────────────────────────────────────
@app.route('/api/pengguna', methods=['GET'])
@pemilik_required
def get_pengguna():
    conn = get_db()
    rows = db_execute(conn, 
        "SELECT id, username, nama, role, aktif, dibuat FROM pengguna ORDER BY role DESC, nama"
    ).fetchall()
    conn.close()
    return jsonify(rows_to_list(rows))


@app.route('/api/pengguna', methods=['POST'])
@pemilik_required
def tambah_pengguna():
    d        = request.json
    username = d.get('username', '').strip()
    nama     = d.get('nama', '').strip()
    password = d.get('password', '')
    role     = d.get('role', 'karyawan')
    if not username or not nama or len(password) < 6:
        return jsonify({'error': 'Semua field wajib diisi & password minimal 6 karakter'}), 400
    if role not in ('pemilik', 'karyawan'):
        return jsonify({'error': 'Role tidak valid'}), 400
    conn = get_db()
    try:
        # Insert ke tabel pengguna (legacy)
        db_execute(conn, 
            "INSERT INTO pengguna (username, nama, password, role) VALUES (?,?,?,?)",
            (username, nama, generate_password_hash(password, method='pbkdf2:sha256'), role)
        )
        
        # Insert ke tabel users (modern) - untuk backward compatibility
        cur = db_execute_insert(conn,
            "INSERT INTO users (username, nama, password, role, is_superadmin) VALUES (?,?,?,?,?)",
            (username, nama, generate_password_hash(password, method='pbkdf2:sha256'), role, 0)
        )
        user_id = cur.lastrowid
        
        # Assign ke toko aktif jika role karyawan
        if role == 'karyawan':
            store_id = get_current_store_id()
            db_execute(conn,
                "INSERT INTO user_stores (user_id, store_id, role) VALUES (?,?,?)",
                (user_id, store_id, 'kasir')
            )
        
        conn.commit()
    except Exception as e:
        conn.rollback()
        conn.close()
        if 'UNIQUE' in str(e).upper():
            return jsonify({'error': f'Username "{username}" sudah digunakan'}), 400
        return jsonify({'error': str(e)}), 500
    conn.close()
    return jsonify({'ok': True}), 201


@app.route('/api/pengguna/<int:uid>', methods=['DELETE'])
@pemilik_required
def hapus_pengguna_api(uid):
    if uid == session.get('user_id'):
        return jsonify({'error': 'Tidak bisa menonaktifkan akun sendiri'}), 400
    conn = get_db()
    
    # Nonaktifkan di tabel pengguna
    db_execute(conn, "UPDATE pengguna SET aktif=0 WHERE id=?", (uid,))
    
    # Sync ke tabel users (nonaktifkan) - kolom 'aktif' bukan 'is_active'
    try:
        user_row = db_execute(conn, "SELECT username FROM pengguna WHERE id=?", (uid,)).fetchone()
        if user_row:
            db_execute(conn, "UPDATE users SET aktif=0 WHERE username=?", (user_row['username'],))
    except Exception as e:
        print(f"[WARN] Gagal sync ke users: {e}")
    
    conn.commit()
    conn.close()
    return jsonify({'ok': True})


@app.route('/api/pengguna/<int:uid>/reset-password', methods=['POST'])
@pemilik_required
def reset_password_pengguna(uid):
    d = request.json
    password = d.get('password', '')
    if len(password) < 6:
        return jsonify({'error': 'Password minimal 6 karakter'}), 400
    conn = get_db()
    
    hashed_pw = generate_password_hash(password, method='pbkdf2:sha256')
    
    # Update tabel pengguna
    db_execute(conn, "UPDATE pengguna SET password=? WHERE id=?", (hashed_pw, uid))
    
    # Sync ke tabel users - kolom 'password' bukan 'password_hash'
    try:
        user_row = db_execute(conn, "SELECT username FROM pengguna WHERE id=?", (uid,)).fetchone()
        if user_row:
            db_execute(conn, "UPDATE users SET password=? WHERE username=?", (hashed_pw, user_row['username']))
    except Exception as e:
        print(f"[WARN] Gagal sync ke users: {e}")
    
    conn.commit()
    conn.close()
    return jsonify({'ok': True})


@app.route('/api/pengguna/ganti-password', methods=['POST'])
def ganti_password_sendiri():
    """User bisa ganti password sendiri (tidak perlu pemilik)."""
    uid = session.get('user_id')
    if not uid:
        return jsonify({'error': 'Tidak login'}), 401
    d = request.json
    lama = d.get('password_lama', '')
    baru = d.get('password_baru', '')
    if len(baru) < 6:
        return jsonify({'error': 'Password baru minimal 6 karakter'}), 400
    conn = get_db()
    user = db_execute(conn, "SELECT * FROM pengguna WHERE id=?", (uid,)).fetchone()
    if not user or not check_password_hash(user['password'], lama):
        conn.close()
        return jsonify({'error': 'Password lama salah'}), 400
    db_execute(conn, "UPDATE pengguna SET password=? WHERE id=?", (generate_password_hash(baru, method='pbkdf2:sha256'), uid))
    conn.commit()
    conn.close()
    return jsonify({'ok': True})


# ─────────────────────────────────────
#  INIT DATABASE (SAAT IMPORT/STARTUP)
# ─────────────────────────────────────
try:
    init_db()
    print("[OK] Database initialized")
except Exception as e:
    print(f"[WARN] Database init error (will retry on first request): {e}")
    import traceback
    print(traceback.format_exc())
    _db_init_error = e

# [MERGED] ensure_db sudah digabung ke require_login()

# ─────────────────────────────────────
#  JALANKAN SERVER (LOCAL DEV)
# ─────────────────────────────────────
if __name__ == '__main__':
    print("\n" + "="*50)
    print("  [TOKO] KasirToko v2.1.1 — Python + Flask + SQLite")
    print("="*50)
    print("  * Fitur: Scan Barcode | Printer App | Multi User")
    print("")
    # Get IP address for mobile access
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
    except:
        ip = "localhost"
    print(f"  [PC] Laptop:     http://localhost:5000")
    print(f"  [HP] Mobile:     http://{ip}:5000")
    print("")
    print("  [i]  Scan barcode butuh HTTPS/localhost (gunakan IP di atas)")
    print("  [OFF]   Tekan Ctrl+C untuk menghentikan server")
    print("="*50 + "\n")
    app.run(debug=False, host='0.0.0.0', port=5000)

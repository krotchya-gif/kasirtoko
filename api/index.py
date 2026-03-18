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
                emoji     TEXT    NOT NULL DEFAULT '📦',
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
                emoji     TEXT    NOT NULL DEFAULT '📦',
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
                emoji        TEXT    DEFAULT '📦',
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
                emoji        TEXT    DEFAULT '📦',
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

    # Tabel pengguna (login + role)
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
        print("✅ Akun default dibuat: pemilik/pemilik123  dan  karyawan/karyawan123")

    # Tabel pengaturan toko (key-value)
    c.execute("""
        CREATE TABLE IF NOT EXISTS pengaturan (
            kunci TEXT PRIMARY KEY,
            nilai TEXT NOT NULL
        )
    """)
    
    # Create indexes for PostgreSQL performance
    if USE_POSTGRES:
        c.execute("CREATE INDEX IF NOT EXISTS idx_produk_kategori ON produk(kategori)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_produk_aktif ON produk(aktif)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_transaksi_waktu ON transaksi(waktu)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_transaksi_item_trxid ON transaksi_item(transaksi_id)")

    # Insert default pengaturan jika belum ada
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
            c.execute("INSERT INTO pengaturan (kunci, nilai) VALUES (?, ?) ON CONFLICT (kunci) DO NOTHING", (k, v))
        else:
            c.execute("INSERT OR IGNORE INTO pengaturan (kunci, nilai) VALUES (?, ?)", (k, v))

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

    conn.commit()
    conn.close()
    print(f"✅ Database siap: {DB_PATH}")


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
    user = db_execute(conn, 
        "SELECT id, username, nama, role FROM pengguna WHERE id=? AND aktif=1", (uid,)
    ).fetchone()
    conn.close()
    return row_to_dict(user) if user else None


def pemilik_required(f):
    """Decorator: hanya pemilik yang bisa akses endpoint ini."""
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        user = get_current_user()
        if not user or user['role'] != 'pemilik':
            return jsonify({'error': 'Akses ditolak — hanya untuk Pemilik Toko'}), 403
        return f(*args, **kwargs)
    return decorated


@app.before_request
def require_login():
    """Semua route wajib login, kecuali /login, /logout, /offline, /static/, /sw.js"""
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
    return render_template('index.html', user=user)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('user_id') and get_current_user():
        return redirect('/')
    error = None
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        conn = get_db()
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


# ─────────────────────────────────────
#  API: PENGATURAN TOKO
# ─────────────────────────────────────
@app.route('/api/pengaturan', methods=['GET'])
def get_pengaturan():
    conn = get_db()
    rows = db_execute(conn, "SELECT kunci, nilai FROM pengaturan").fetchall()
    conn.close()
    return jsonify({r['kunci']: r['nilai'] for r in rows})

@app.route('/api/pengaturan', methods=['POST'])
@pemilik_required
def save_pengaturan():
    data = request.json
    conn = get_db()
    for k, v in data.items():
        if USE_POSTGRES:
            db_execute(conn, 
                "INSERT INTO pengaturan (kunci, nilai) VALUES (%s, %s) ON CONFLICT(kunci) DO UPDATE SET nilai=EXCLUDED.nilai",
                (k, str(v))
            )
        else:
            db_execute(conn, 
                "INSERT INTO pengaturan (kunci, nilai) VALUES (?,?) ON CONFLICT(kunci) DO UPDATE SET nilai=excluded.nilai",
                (k, str(v))
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
    conn = get_db()
    
    # Jika ada barcode, cari exact match
    if barcode:
        row = db_execute(conn, 
            "SELECT * FROM produk WHERE barcode=? AND aktif=1", (barcode,)
        ).fetchone()
        conn.close()
        if row:
            return jsonify(dict(row))
        return jsonify({'error': 'Produk tidak ditemukan'}), 404
    
    sql = "SELECT * FROM produk WHERE aktif=1"
    params = []
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
    conn = get_db()
    cur = db_execute(conn, 
        "INSERT INTO produk (nama, harga, stok, emoji, kategori, harga_modal, stok_min, diskon, barcode) VALUES (?,?,?,?,?,?,?,?,?)",
        (d['nama'], d['harga'], d['stok'], d.get('emoji','📦'), d['kategori'],
         d.get('harga_modal',0), d.get('stok_min',0), d.get('diskon',0), d.get('barcode',''))
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
    conn = get_db()
    db_execute(conn, 
        """UPDATE produk SET nama=?, harga=?, stok=?, emoji=?, kategori=?,
           harga_modal=?, stok_min=?, diskon=?, barcode=?,
           diubah=datetime('now','localtime') WHERE id=?""",
        (d['nama'], d['harga'], d['stok'], d.get('emoji','📦'), d['kategori'],
         d.get('harga_modal',0), d.get('stok_min',0), d.get('diskon',0), d.get('barcode',''), pid)
    )
    conn.commit()
    row = db_execute(conn, "SELECT * FROM produk WHERE id=?", (pid,)).fetchone()
    conn.close()
    return jsonify(row_to_dict(row))

@app.route('/api/produk/<int:pid>', methods=['DELETE'])
@pemilik_required
def hapus_produk(pid):
    conn = get_db()
    # Soft delete — data tetap ada di DB, hanya tidak ditampilkan
    db_execute(conn, "UPDATE produk SET aktif=0 WHERE id=?", (pid,))
    conn.commit()
    conn.close()
    return jsonify({'ok': True})

@app.route('/api/produk/scan/<barcode>', methods=['GET'])
def scan_produk(barcode):
    """Scan barcode untuk mencari produk (untuk kasir)"""
    conn = get_db()
    row = db_execute(conn, 
        "SELECT * FROM produk WHERE barcode=? AND aktif=1", (barcode,)
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
    conn = get_db()
    rows = db_execute(conn, """
        SELECT * FROM produk
        WHERE aktif = 1
          AND (
              (stok_min > 0 AND stok <= stok_min)
              OR
              (stok_min = 0 AND stok <= 5 AND stok > 0)
          )
        ORDER BY stok ASC, nama
    """).fetchall()
    conn.close()
    return jsonify(rows_to_list(rows))


@app.route('/api/laporan/top-produk', methods=['GET'])
@pemilik_required
def laporan_top_produk():
    dari  = request.args.get('dari', '')
    ke    = request.args.get('ke', '')
    limit = int(request.args.get('limit', 10))

    conn       = get_db()
    # Filter: hanya transaksi aktif (exclude void)
    sql_filter = "WHERE COALESCE(t.status, 'aktif') = 'aktif'"
    params     = []
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
    if metode_bayar not in ('tunai', 'transfer', 'qris'):
        metode_bayar = 'tunai'

    no_trx = 'TRX' + datetime.now().strftime('%y%m%d%H%M%S')

    conn = get_db()
    try:
        # Insert header transaksi
        cur = db_execute_insert(conn, 
            """INSERT INTO transaksi
               (no_trx, subtotal, diskon, diskon_val, diskon_tipe, total, bayar, kembalian, pelanggan_id, metode_bayar)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (no_trx, subtotal, diskon, diskon_val, diskon_tipe, total, bayar, kembalian, pelanggan_id, metode_bayar)
        )
        trx_id = cur.lastrowid

        # Insert item & kurangi stok
        for item in items:
            db_execute(conn, 
                """INSERT INTO transaksi_item
                   (transaksi_id, produk_id, nama_produk, emoji, harga, qty, subtotal)
                   VALUES (?,?,?,?,?,?,?)""",
                (trx_id, item['id'], item['nama'], item.get('emoji','📦'),
                 item['harga'], item['qty'], item['harga'] * item['qty'])
            )
            db_execute(conn, 
                "UPDATE produk SET stok = stok - ? WHERE id=?",
                (item['qty'], item['id'])
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
    conn  = get_db()
    sql   = "SELECT * FROM kas WHERE 1=1"
    params = []
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
        FROM kas WHERE 1=1
    """
    stat_params = []
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
        FROM kas
    """).fetchone()
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
    if metode not in ('tunai', 'transfer', 'qris'):
        metode = 'tunai'
    if tipe not in ('pemasukan', 'pengeluaran') or jumlah <= 0:
        return jsonify({'error': 'Data tidak valid'}), 400
    conn = get_db()
    cur = db_execute(conn, 
        "INSERT INTO kas (tipe, jumlah, keterangan, metode) VALUES (?,?,?,?)",
        (tipe, jumlah, keterangan, metode)
    )
    kid = cur.lastrowid
    conn.commit()
    row = row_to_dict(db_execute(conn, "SELECT * FROM kas WHERE id=?", (kid,)).fetchone())
    conn.close()
    return jsonify(row), 201


@app.route('/api/kas/<int:kid>', methods=['DELETE'])
@pemilik_required
def hapus_kas(kid):
    conn = get_db()
    db_execute(conn, "DELETE FROM kas WHERE id=?", (kid,))
    conn.commit()
    conn.close()
    return jsonify({'ok': True})


# ─────────────────────────────────────
#  API: TUTUP KASIR
# ─────────────────────────────────────
@app.route('/api/tutup-kasir/preview', methods=['GET'])
def tutup_kasir_preview():
    """Hitung transaksi yang belum ditutup (tutup_kasir_id IS NULL)."""
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
    """).fetchone()
    conn.close()
    return jsonify(row_to_dict(row))


@app.route('/api/tutup-kasir', methods=['POST'])
def buat_tutup_kasir():
    """Karyawan/pemilik proses tutup kasir → status pending."""
    user = get_current_user()
    d = request.json or {}
    keterangan = d.get('keterangan', '').strip()

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
    """).fetchone()

    if row['jumlah_trx'] == 0:
        conn.close()
        return jsonify({'error': 'Tidak ada transaksi yang belum ditutup'}), 400

    # Buat record tutup_kasir
    cur = db_execute(conn, 
        """INSERT INTO tutup_kasir
           (total, total_tunai, total_transfer, total_qris, jumlah_trx, keterangan, dibuat_oleh)
           VALUES (?,?,?,?,?,?,?)""",
        (row['total'], row['total_tunai'], row['total_transfer'], row['total_qris'],
         row['jumlah_trx'], keterangan, user['nama'])
    )
    tk_id = cur.lastrowid

    # Tandai semua transaksi belum tutup dengan id ini (hanya yang aktif)
    db_execute(conn, 
        "UPDATE transaksi SET tutup_kasir_id=? WHERE tutup_kasir_id IS NULL AND COALESCE(status, 'aktif') = 'aktif'",
        (tk_id,)
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
    conn = get_db()
    rows = rows_to_list(db_execute(conn, 
        "SELECT * FROM tutup_kasir ORDER BY waktu DESC LIMIT 50"
    ).fetchall())
    pending = db_execute(conn, 
        "SELECT COUNT(*) AS n FROM tutup_kasir WHERE status='pending'"
    ).fetchone()['n']
    conn.close()
    return jsonify({'rows': rows, 'pending': pending})


@app.route('/api/tutup-kasir/<int:tk_id>/konfirmasi', methods=['POST'])
@pemilik_required
def konfirmasi_tutup_kasir(tk_id):
    """Pemilik konfirmasi → buat entri kas pemasukan per metode."""
    user = get_current_user()
    conn = get_db()
    tk = db_execute(conn, "SELECT * FROM tutup_kasir WHERE id=?", (tk_id,)).fetchone()
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
                "INSERT INTO kas (tipe, jumlah, keterangan, metode) VALUES (?,?,?,?)",
                ('pemasukan', jumlah, ket, metode)
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
        
        for item in items:
            produk_id = item['produk_id']
            qty = item['qty']
            
            # Get stok saat ini
            prod = db_execute(conn, 
                "SELECT stok FROM produk WHERE id=?", (produk_id,)
            ).fetchone()
            
            if prod:
                stok_sebelum = prod['stok']
                stok_sesudah = max(0, stok_sebelum - qty)
                
                # Update stok produk
                db_execute(conn, 
                    "UPDATE produk SET stok = MAX(0, stok - ?) WHERE id=?",
                    (qty, produk_id)
                )
                
                # Catat di stok_log (restore)
                db_execute(conn, 
                    """INSERT INTO stok_log 
                       (produk_id, tipe, jumlah, stok_sebelum, stok_sesudah, 
                        alasan, keterangan, transaksi_id, dibuat_oleh)
                       VALUES (?,?,?,?,?,?,?,?,?)""",
                    (produk_id, 'keluar', qty, stok_sebelum, stok_sesudah,
                     'restore_transaksi', f'Pengurangan stok dari restore transaksi {trx["no_trx"]}', 
                     tid, user['nama'])
                )
        
        # Update status transaksi menjadi aktif
        db_execute(conn, 
            """UPDATE transaksi 
               SET status='aktif', void_reason='', void_by='', void_at=''
               WHERE id=?""",
            (tid,)
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
    
    conn = get_db()
    sql = """
        SELECT sl.*, p.nama as produk_nama, p.emoji as produk_emoji
        FROM stok_log sl
        JOIN produk p ON p.id = sl.produk_id
        WHERE 1=1
    """
    params = []
    
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
        db_execute(conn, 
            "UPDATE produk SET stok = ?, diubah = datetime('now','localtime') WHERE id=?",
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
    conn = get_db()
    sql = """
        SELECT p.*,
               COUNT(t.id)                          AS total_trx,
               COALESCE(SUM(t.total), 0)            AS total_belanja
        FROM pelanggan p
        LEFT JOIN transaksi t ON t.pelanggan_id = p.id
        WHERE 1=1
    """
    params = []
    if cari:
        if USE_POSTGRES:
            sql += " AND (p.nama ILIKE %s OR p.telepon ILIKE %s)"
            params.extend([f'%{cari}%', f'%{cari}%'])
            sql += " GROUP BY p.id ORDER BY p.nama"
        else:
            sql += " AND (p.nama LIKE ? OR p.telepon LIKE ?)"
            params.extend([f'%{cari}%', f'%{cari}%'])
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
    conn = get_db()
    cur  = db_execute(conn, 
        "INSERT INTO pelanggan (nama, telepon, alamat, catatan) VALUES (?,?,?,?)",
        (nama, d.get('telepon','').strip(), d.get('alamat','').strip(), d.get('catatan','').strip())
    )
    pid = cur.lastrowid
    conn.commit()
    row = row_to_dict(db_execute(conn, "SELECT * FROM pelanggan WHERE id=?", (pid,)).fetchone())
    conn.close()
    return jsonify(row), 201


@app.route('/api/pelanggan/<int:pid>', methods=['GET'])
def get_pelanggan_detail(pid):
    conn = get_db()
    plg  = db_execute(conn, "SELECT * FROM pelanggan WHERE id=?", (pid,)).fetchone()
    if not plg:
        conn.close()
        return jsonify({'error': 'Tidak ditemukan'}), 404
    stats = row_to_dict(db_execute(conn, """
        SELECT COUNT(*) AS total_trx,
               COALESCE(SUM(total), 0) AS total_belanja,
               MAX(waktu) AS terakhir_belanja
        FROM transaksi WHERE pelanggan_id=?
    """, (pid,)).fetchone())
    transaksi = rows_to_list(db_execute(conn, 
        "SELECT * FROM transaksi WHERE pelanggan_id=? ORDER BY waktu DESC LIMIT 30",
        (pid,)
    ).fetchall())
    conn.close()
    return jsonify({'pelanggan': row_to_dict(plg), 'stats': stats, 'transaksi': transaksi})


@app.route('/api/pelanggan/<int:pid>', methods=['PUT'])
def update_pelanggan(pid):
    d    = request.json
    nama = d.get('nama', '').strip()
    if not nama:
        return jsonify({'error': 'Nama tidak boleh kosong'}), 400
    conn = get_db()
    db_execute(conn, 
        "UPDATE pelanggan SET nama=?, telepon=?, alamat=?, catatan=? WHERE id=?",
        (nama, d.get('telepon','').strip(), d.get('alamat','').strip(), d.get('catatan','').strip(), pid)
    )
    conn.commit()
    row = row_to_dict(db_execute(conn, "SELECT * FROM pelanggan WHERE id=?", (pid,)).fetchone())
    conn.close()
    return jsonify(row)


@app.route('/api/pelanggan/<int:pid>', methods=['DELETE'])
def hapus_pelanggan(pid):
    conn = get_db()
    db_execute(conn, "UPDATE transaksi SET pelanggan_id=NULL WHERE pelanggan_id=?", (pid,))
    db_execute(conn, "DELETE FROM pelanggan WHERE id=?", (pid,))
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
    
    conn.close()
    
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
    conn = get_db()
    rows = db_execute(conn, 
        "SELECT nama, kategori, harga, stok, emoji, harga_modal, stok_min, diskon FROM produk WHERE aktif=1 ORDER BY kategori, nama"
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
        emoji  = r.get('emoji', '📦').strip() or '📦'
        valid.append({'nama': nama, 'kategori': kat, 'harga': harga, 'stok': stok, 'emoji': emoji,
                      'harga_modal': harga_modal, 'stok_min': stok_min, 'diskon': diskon})

    if not valid:
        return jsonify({'error': 'Semua baris tidak valid', 'detail': errors}), 400

    conn = get_db()
    tambah = 0
    update = 0
    skip   = 0

    try:
        if mode == 'ganti':
            # Nonaktifkan semua produk lama
            db_execute(conn, "UPDATE produk SET aktif=0")

        for p in valid:
            existing = db_execute(conn, 
                "SELECT id FROM produk WHERE LOWER(nama)=LOWER(?) AND aktif=1",
                (p['nama'],)
            ).fetchone()

            if existing:
                if mode == 'timpa':
                    db_execute(conn, 
                        "UPDATE produk SET harga=?, stok=?, emoji=?, kategori=?, harga_modal=?, stok_min=?, diskon=?, diubah=datetime('now','localtime') WHERE id=?",
                        (p['harga'], p['stok'], p['emoji'], p['kategori'],
                         p['harga_modal'], p['stok_min'], p['diskon'], existing['id'])
                    )
                    update += 1
                elif mode == 'ganti':
                    # Reaktifkan dan update
                    db_execute(conn, 
                        "UPDATE produk SET harga=?, stok=?, emoji=?, kategori=?, harga_modal=?, stok_min=?, diskon=?, aktif=1, diubah=datetime('now','localtime') WHERE id=?",
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
                    "SELECT id FROM produk WHERE LOWER(nama)=LOWER(?) AND aktif=0",
                    (p['nama'],)
                ).fetchone()
                if deleted:
                    db_execute(conn, 
                        "UPDATE produk SET harga=?, stok=?, emoji=?, kategori=?, harga_modal=?, stok_min=?, diskon=?, aktif=1, diubah=datetime('now','localtime') WHERE id=?",
                        (p['harga'], p['stok'], p['emoji'], p['kategori'],
                         p['harga_modal'], p['stok_min'], p['diskon'], deleted['id'])
                    )
                else:
                    db_execute(conn, 
                        "INSERT INTO produk (nama, harga, stok, emoji, kategori, harga_modal, stok_min, diskon) VALUES (?,?,?,?,?,?,?,?)",
                        (p['nama'], p['harga'], p['stok'], p['emoji'], p['kategori'],
                         p['harga_modal'], p['stok_min'], p['diskon'])
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
        db_execute(conn, 
            "INSERT INTO pengguna (username, nama, password, role) VALUES (?,?,?,?)",
            (username, nama, generate_password_hash(password, method='pbkdf2:sha256'), role)
        )
        conn.commit()
    except Exception as e:
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
    db_execute(conn, "UPDATE pengguna SET aktif=0 WHERE id=?", (uid,))
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
    db_execute(conn, "UPDATE pengguna SET password=? WHERE id=?", (generate_password_hash(password, method='pbkdf2:sha256'), uid))
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
    print("✅ Database initialized")
except Exception as e:
    print(f"⚠️ Database init error (will retry on first request): {e}")
    import traceback
    print(traceback.format_exc())
    _db_init_error = e

# Lazy init handler - akan mencoba init lagi saat request pertama jika gagal
@app.before_request
def ensure_db():
    if '_db_init_error' in globals():
        try:
            init_db()
            print("✅ Database initialized (retry)")
            del globals()['_db_init_error']
        except Exception as e:
            print(f"❌ Database init failed again: {e}")

# ─────────────────────────────────────
#  JALANKAN SERVER (LOCAL DEV)
# ─────────────────────────────────────
if __name__ == '__main__':
    print("\n" + "="*50)
    print("  🏪 KasirToko v1.11.3 — Python + Flask + SQLite")
    print("="*50)
    print("  ✨ Fitur: Scan Barcode | Printer App | Multi User")
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
    print(f"  💻 Laptop:     http://localhost:5000")
    print(f"  📱 Mobile:     http://{ip}:5000")
    print("")
    print("  ℹ️  Scan barcode butuh HTTPS/localhost (gunakan IP di atas)")
    print("  ⏻️   Tekan Ctrl+C untuk menghentikan server")
    print("="*50 + "\n")
    app.run(debug=False, host='0.0.0.0', port=5000)

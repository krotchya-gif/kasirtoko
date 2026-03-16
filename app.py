"""
KasirToko — Backend Flask + SQLite
Jalankan: python app.py
Buka browser: http://localhost:5000
"""

import functools
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from flask import Flask, request, jsonify, render_template, send_file, session, redirect
from flask_cors import CORS
import sqlite3
import os
import json
import csv
import io

app = Flask(__name__)
CORS(app)

# Session — ganti SECRET_KEY di environment saat production
app.secret_key = os.environ.get('SECRET_KEY', 'kasirtoko-dev-secret-2024-change-in-prod')
app.permanent_session_lifetime = timedelta(days=30)

DB_PATH = os.path.join(os.path.dirname(__file__), 'kasirtoko.db')

# ─────────────────────────────────────
#  DATABASE INIT
# ─────────────────────────────────────
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")   # lebih aman saat crash
    conn.execute("PRAGMA foreign_keys=ON")
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()

    # Tabel produk
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

    # Tabel tutup_kasir (end-of-day closing)
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
    c.execute("SELECT COUNT(*) FROM pengguna")
    if c.fetchone()[0] == 0:
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
        c.execute("INSERT OR IGNORE INTO pengaturan (kunci, nilai) VALUES (?, ?)", (k, v))

    # Insert produk default jika tabel kosong
    c.execute("SELECT COUNT(*) FROM produk")
    if c.fetchone()[0] == 0:
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
    return dict(row)

def rows_to_list(rows):
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
    user = conn.execute(
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
        user = conn.execute(
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
    rows = conn.execute("SELECT kunci, nilai FROM pengaturan").fetchall()
    conn.close()
    return jsonify({r['kunci']: r['nilai'] for r in rows})

@app.route('/api/pengaturan', methods=['POST'])
@pemilik_required
def save_pengaturan():
    data = request.json
    conn = get_db()
    for k, v in data.items():
        conn.execute(
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
        row = conn.execute(
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
        sql += " AND nama LIKE ?"
        params.append(f'%{cari}%')
    sql += " ORDER BY kategori, nama LIMIT ?"
    params.append(limit)
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return jsonify(rows_to_list(rows))

@app.route('/api/produk', methods=['POST'])
@pemilik_required
def tambah_produk():
    d = request.json
    conn = get_db()
    cur = conn.execute(
        "INSERT INTO produk (nama, harga, stok, emoji, kategori, harga_modal, stok_min, diskon, barcode) VALUES (?,?,?,?,?,?,?,?,?)",
        (d['nama'], d['harga'], d['stok'], d.get('emoji','📦'), d['kategori'],
         d.get('harga_modal',0), d.get('stok_min',0), d.get('diskon',0), d.get('barcode',''))
    )
    produk_id = cur.lastrowid
    conn.commit()
    row = conn.execute("SELECT * FROM produk WHERE id=?", (produk_id,)).fetchone()
    conn.close()
    return jsonify(row_to_dict(row)), 201

@app.route('/api/produk/<int:pid>', methods=['PUT'])
@pemilik_required
def update_produk(pid):
    d = request.json
    conn = get_db()
    conn.execute(
        """UPDATE produk SET nama=?, harga=?, stok=?, emoji=?, kategori=?,
           harga_modal=?, stok_min=?, diskon=?, barcode=?,
           diubah=datetime('now','localtime') WHERE id=?""",
        (d['nama'], d['harga'], d['stok'], d.get('emoji','📦'), d['kategori'],
         d.get('harga_modal',0), d.get('stok_min',0), d.get('diskon',0), d.get('barcode',''), pid)
    )
    conn.commit()
    row = conn.execute("SELECT * FROM produk WHERE id=?", (pid,)).fetchone()
    conn.close()
    return jsonify(row_to_dict(row))

@app.route('/api/produk/<int:pid>', methods=['DELETE'])
@pemilik_required
def hapus_produk(pid):
    conn = get_db()
    # Soft delete — data tetap ada di DB, hanya tidak ditampilkan
    conn.execute("UPDATE produk SET aktif=0 WHERE id=?", (pid,))
    conn.commit()
    conn.close()
    return jsonify({'ok': True})

@app.route('/api/produk/scan/<barcode>', methods=['GET'])
def scan_produk(barcode):
    """Scan barcode untuk mencari produk (untuk kasir)"""
    conn = get_db()
    row = conn.execute(
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
    rows = conn.execute("""
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
    sql_filter = "WHERE 1=1"
    params     = []
    if dari:
        sql_filter += " AND DATE(t.waktu) >= ?"
        params.append(dari)
    if ke:
        sql_filter += " AND DATE(t.waktu) <= ?"
        params.append(ke)

    top = conn.execute(f"""
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
    rows = conn.execute("SELECT DISTINCT kategori FROM produk WHERE aktif=1 ORDER BY kategori").fetchall()
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
        cur = conn.execute(
            """INSERT INTO transaksi
               (no_trx, subtotal, diskon, diskon_val, diskon_tipe, total, bayar, kembalian, pelanggan_id, metode_bayar)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (no_trx, subtotal, diskon, diskon_val, diskon_tipe, total, bayar, kembalian, pelanggan_id, metode_bayar)
        )
        trx_id = cur.lastrowid

        # Insert item & kurangi stok
        for item in items:
            conn.execute(
                """INSERT INTO transaksi_item
                   (transaksi_id, produk_id, nama_produk, emoji, harga, qty, subtotal)
                   VALUES (?,?,?,?,?,?,?)""",
                (trx_id, item['id'], item['nama'], item.get('emoji','📦'),
                 item['harga'], item['qty'], item['harga'] * item['qty'])
            )
            conn.execute(
                "UPDATE produk SET stok = stok - ? WHERE id=?",
                (item['qty'], item['id'])
            )

        conn.commit()

        # Return transaksi lengkap
        trx = row_to_dict(conn.execute("SELECT * FROM transaksi WHERE id=?", (trx_id,)).fetchone())
        trx['items'] = rows_to_list(conn.execute(
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
    sql += " ORDER BY t.waktu DESC LIMIT ?"
    params.append(limit)

    rows = conn.execute(sql, params).fetchall()
    result = []
    for r in rows:
        trx = row_to_dict(r)
        trx['items'] = rows_to_list(conn.execute(
            "SELECT * FROM transaksi_item WHERE transaksi_id=?", (r['id'],)
        ).fetchall())
        result.append(trx)
    conn.close()
    return jsonify(result)

@app.route('/api/transaksi/<int:tid>', methods=['GET'])
def get_transaksi_by_id(tid):
    conn = get_db()
    trx = conn.execute("SELECT * FROM transaksi WHERE id=?", (tid,)).fetchone()
    if not trx:
        conn.close()
        return jsonify({'error': 'Tidak ditemukan'}), 404
    result = row_to_dict(trx)
    result['items'] = rows_to_list(conn.execute(
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
    rows = rows_to_list(conn.execute(sql, params).fetchall())

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
    stat = row_to_dict(conn.execute(sql_stat, stat_params).fetchone())

    # Saldo keseluruhan (all time) + breakdown per metode
    saldo_row = conn.execute("""
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
    cur = conn.execute(
        "INSERT INTO kas (tipe, jumlah, keterangan, metode) VALUES (?,?,?,?)",
        (tipe, jumlah, keterangan, metode)
    )
    kid = cur.lastrowid
    conn.commit()
    row = row_to_dict(conn.execute("SELECT * FROM kas WHERE id=?", (kid,)).fetchone())
    conn.close()
    return jsonify(row), 201


@app.route('/api/kas/<int:kid>', methods=['DELETE'])
@pemilik_required
def hapus_kas(kid):
    conn = get_db()
    conn.execute("DELETE FROM kas WHERE id=?", (kid,))
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
    row = conn.execute("""
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
    # Ambil preview dulu
    row = conn.execute("""
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
    """).fetchone()

    if row['jumlah_trx'] == 0:
        conn.close()
        return jsonify({'error': 'Tidak ada transaksi yang belum ditutup'}), 400

    # Buat record tutup_kasir
    cur = conn.execute(
        """INSERT INTO tutup_kasir
           (total, total_tunai, total_transfer, total_qris, jumlah_trx, keterangan, dibuat_oleh)
           VALUES (?,?,?,?,?,?,?)""",
        (row['total'], row['total_tunai'], row['total_transfer'], row['total_qris'],
         row['jumlah_trx'], keterangan, user['nama'])
    )
    tk_id = cur.lastrowid

    # Tandai semua transaksi belum tutup dengan id ini
    conn.execute(
        "UPDATE transaksi SET tutup_kasir_id=? WHERE tutup_kasir_id IS NULL",
        (tk_id,)
    )
    conn.commit()

    result = row_to_dict(conn.execute(
        "SELECT * FROM tutup_kasir WHERE id=?", (tk_id,)
    ).fetchone())
    conn.close()
    return jsonify(result), 201


@app.route('/api/tutup-kasir', methods=['GET'])
@pemilik_required
def list_tutup_kasir():
    """Pemilik: ambil riwayat tutup kasir + jumlah pending."""
    conn = get_db()
    rows = rows_to_list(conn.execute(
        "SELECT * FROM tutup_kasir ORDER BY waktu DESC LIMIT 50"
    ).fetchall())
    pending = conn.execute(
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
    tk = conn.execute("SELECT * FROM tutup_kasir WHERE id=?", (tk_id,)).fetchone()
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
            conn.execute(
                "INSERT INTO kas (tipe, jumlah, keterangan, metode) VALUES (?,?,?,?)",
                ('pemasukan', jumlah, ket, metode)
            )

    # Update status tutup_kasir
    conn.execute(
        """UPDATE tutup_kasir
           SET status='confirmed', dikonfirmasi_oleh=?, waktu_konfirmasi=?
           WHERE id=?""",
        (user['nama'], waktu_now, tk_id)
    )
    conn.commit()

    result = row_to_dict(conn.execute(
        "SELECT * FROM tutup_kasir WHERE id=?", (tk_id,)
    ).fetchone())
    conn.close()
    return jsonify(result)


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
        sql += " AND (p.nama LIKE ? OR p.telepon LIKE ?)"
        params.extend([f'%{cari}%', f'%{cari}%'])
    sql += " GROUP BY p.id ORDER BY p.nama COLLATE NOCASE"
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return jsonify(rows_to_list(rows))


@app.route('/api/pelanggan', methods=['POST'])
def tambah_pelanggan():
    d    = request.json
    nama = d.get('nama', '').strip()
    if not nama:
        return jsonify({'error': 'Nama tidak boleh kosong'}), 400
    conn = get_db()
    cur  = conn.execute(
        "INSERT INTO pelanggan (nama, telepon, alamat, catatan) VALUES (?,?,?,?)",
        (nama, d.get('telepon','').strip(), d.get('alamat','').strip(), d.get('catatan','').strip())
    )
    pid = cur.lastrowid
    conn.commit()
    row = row_to_dict(conn.execute("SELECT * FROM pelanggan WHERE id=?", (pid,)).fetchone())
    conn.close()
    return jsonify(row), 201


@app.route('/api/pelanggan/<int:pid>', methods=['GET'])
def get_pelanggan_detail(pid):
    conn = get_db()
    plg  = conn.execute("SELECT * FROM pelanggan WHERE id=?", (pid,)).fetchone()
    if not plg:
        conn.close()
        return jsonify({'error': 'Tidak ditemukan'}), 404
    stats = row_to_dict(conn.execute("""
        SELECT COUNT(*) AS total_trx,
               COALESCE(SUM(total), 0) AS total_belanja,
               MAX(waktu) AS terakhir_belanja
        FROM transaksi WHERE pelanggan_id=?
    """, (pid,)).fetchone())
    transaksi = rows_to_list(conn.execute(
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
    conn.execute(
        "UPDATE pelanggan SET nama=?, telepon=?, alamat=?, catatan=? WHERE id=?",
        (nama, d.get('telepon','').strip(), d.get('alamat','').strip(), d.get('catatan','').strip(), pid)
    )
    conn.commit()
    row = row_to_dict(conn.execute("SELECT * FROM pelanggan WHERE id=?", (pid,)).fetchone())
    conn.close()
    return jsonify(row)


@app.route('/api/pelanggan/<int:pid>', methods=['DELETE'])
def hapus_pelanggan(pid):
    conn = get_db()
    conn.execute("UPDATE transaksi SET pelanggan_id=NULL WHERE pelanggan_id=?", (pid,))
    conn.execute("DELETE FROM pelanggan WHERE id=?", (pid,))
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
    stats = conn.execute("""
        SELECT
            COUNT(*)        AS total_transaksi,
            COALESCE(SUM(total),0)     AS omzet,
            COALESCE(SUM(diskon),0)    AS total_diskon,
            COALESCE(AVG(total),0)     AS rata_rata
        FROM transaksi
        WHERE DATE(waktu) = DATE('now','localtime')
    """).fetchone()

    top_produk = conn.execute("""
        SELECT ti.nama_produk AS nama, ti.emoji,
               SUM(ti.qty) AS total_qty,
               SUM(ti.subtotal) AS total_nilai
        FROM transaksi_item ti
        JOIN transaksi t ON t.id = ti.transaksi_id
        WHERE DATE(t.waktu) = DATE('now','localtime')
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

    sql_filter = "WHERE 1=1"
    params = []
    if dari:
        sql_filter += " AND DATE(waktu) >= ?"
        params.append(dari)
    if ke:
        sql_filter += " AND DATE(waktu) <= ?"
        params.append(ke)

    stats = conn.execute(f"""
        SELECT COUNT(*) AS total_transaksi,
               COALESCE(SUM(total),0) AS omzet,
               COALESCE(SUM(diskon),0) AS total_diskon,
               COALESCE(AVG(total),0) AS rata_rata
        FROM transaksi {sql_filter}
    """, params).fetchone()

    harian = conn.execute(f"""
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

    rows = conn.execute(sql, params).fetchall()
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
    rows = conn.execute(
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
            conn.execute("UPDATE produk SET aktif=0")

        for p in valid:
            existing = conn.execute(
                "SELECT id FROM produk WHERE LOWER(nama)=LOWER(?) AND aktif=1",
                (p['nama'],)
            ).fetchone()

            if existing:
                if mode == 'timpa':
                    conn.execute(
                        "UPDATE produk SET harga=?, stok=?, emoji=?, kategori=?, harga_modal=?, stok_min=?, diskon=?, diubah=datetime('now','localtime') WHERE id=?",
                        (p['harga'], p['stok'], p['emoji'], p['kategori'],
                         p['harga_modal'], p['stok_min'], p['diskon'], existing['id'])
                    )
                    update += 1
                elif mode == 'ganti':
                    # Reaktifkan dan update
                    conn.execute(
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
                deleted = conn.execute(
                    "SELECT id FROM produk WHERE LOWER(nama)=LOWER(?) AND aktif=0",
                    (p['nama'],)
                ).fetchone()
                if deleted:
                    conn.execute(
                        "UPDATE produk SET harga=?, stok=?, emoji=?, kategori=?, harga_modal=?, stok_min=?, diskon=?, aktif=1, diubah=datetime('now','localtime') WHERE id=?",
                        (p['harga'], p['stok'], p['emoji'], p['kategori'],
                         p['harga_modal'], p['stok_min'], p['diskon'], deleted['id'])
                    )
                else:
                    conn.execute(
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
    rows = conn.execute(
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
        conn.execute(
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
    conn.execute("UPDATE pengguna SET aktif=0 WHERE id=?", (uid,))
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
    conn.execute("UPDATE pengguna SET password=? WHERE id=?", (generate_password_hash(password, method='pbkdf2:sha256'), uid))
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
    user = conn.execute("SELECT * FROM pengguna WHERE id=?", (uid,)).fetchone()
    if not user or not check_password_hash(user['password'], lama):
        conn.close()
        return jsonify({'error': 'Password lama salah'}), 400
    conn.execute("UPDATE pengguna SET password=? WHERE id=?", (generate_password_hash(baru, method='pbkdf2:sha256'), uid))
    conn.commit()
    conn.close()
    return jsonify({'ok': True})


# ─────────────────────────────────────
#  JALANKAN SERVER
# ─────────────────────────────────────
if __name__ == '__main__':
    init_db()
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

"""Init DB & migrasi — pindahan murni dari app.py."""

from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from .db import get_db, get_db_cursor, db_execute
from .config import USE_POSTGRES, DB_PATH


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
                store_id INTEGER DEFAULT 0 REFERENCES stores(id) ON DELETE CASCADE,
                PRIMARY KEY (kunci, store_id)
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
            c.execute("INSERT OR IGNORE INTO pengaturan (kunci, nilai, store_id) VALUES (?, ?, 0)", (k, v))

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

    # Idempotency key untuk pembayaran piutang (P1-3: cegah double-submit)
    try:
        c.execute("ALTER TABLE piutang_bayar ADD COLUMN idempotency_key TEXT DEFAULT ''")
    except Exception:
        pass  # Kolom sudah ada
    try:
        c.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_piutang_bayar_idem ON piutang_bayar(transaksi_id, idempotency_key) WHERE idempotency_key <> ''")
    except Exception as e:
        print(f"[WARN] Index idempotency: {e}")

    # Index tambahan (P3-1)
    index_sql = [
        "CREATE INDEX IF NOT EXISTS idx_produk_store_aktif ON produk(store_id, aktif)",
        "CREATE INDEX IF NOT EXISTS idx_produk_kategori ON produk(kategori)",
        "CREATE INDEX IF NOT EXISTS idx_transaksi_store_waktu ON transaksi(store_id, waktu)",
        "CREATE INDEX IF NOT EXISTS idx_transaksi_status ON transaksi(status)",
        "CREATE INDEX IF NOT EXISTS idx_transaksi_item_trxid ON transaksi_item(transaksi_id)",
        "CREATE INDEX IF NOT EXISTS idx_stoklog_produk_waktu ON stok_log(produk_id, waktu)",
        "CREATE INDEX IF NOT EXISTS idx_kas_store_waktu ON kas(store_id, waktu)",
    ]
    for stmt in index_sql:
        try:
            c.execute(stmt)
        except Exception as e:
            print(f"[WARN] Index: {e}")

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
        # Ambil data pengaturan global (store_id=0 untuk SQLite, NULL untuk Postgres)
        if use_postgres:
            c.execute("SELECT nilai FROM pengaturan WHERE kunci = 'nama_toko' AND store_id IS NULL")
        else:
            c.execute("SELECT nilai FROM pengaturan WHERE kunci = 'nama_toko' AND store_id = 0")
        result = c.fetchone()
        nama_toko = result['nilai'] if result else 'Toko Saya'
        
        if use_postgres:
            c.execute("SELECT nilai FROM pengaturan WHERE kunci = 'alamat' AND store_id IS NULL")
        else:
            c.execute("SELECT nilai FROM pengaturan WHERE kunci = 'alamat' AND store_id = 0")
        result = c.fetchone()
        alamat = result['nilai'] if result else ''
        
        if use_postgres:
            c.execute("SELECT nilai FROM pengaturan WHERE kunci = 'telp' AND store_id IS NULL")
        else:
            c.execute("SELECT nilai FROM pengaturan WHERE kunci = 'telp' AND store_id = 0")
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
    
    # 5b. Migrasi tabel pengaturan - tambah store_id dan perbaiki primary key untuk multi-store
    try:
        if use_postgres:
            c.execute("ALTER TABLE pengaturan ADD COLUMN IF NOT EXISTS store_id INTEGER REFERENCES stores(id) ON DELETE CASCADE")
            # Buat ulang primary key untuk support composite
            c.execute("ALTER TABLE pengaturan DROP CONSTRAINT IF EXISTS pengaturan_pkey")
            c.execute("ALTER TABLE pengaturan ADD PRIMARY KEY (kunci, COALESCE(store_id, 0))")
        else:
            # SQLite: periksa apakah perlu migrasi (cek apakah pk hanya kunci saja)
            c.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='pengaturan'")
            table_sql = c.fetchone()
            if table_sql and 'PRIMARY KEY (kunci)' in table_sql['sql'] and 'PRIMARY KEY (kunci, store_id)' not in table_sql['sql']:
                # Recreate tabel dengan skema baru
                print("[MIGRASI] Memperbarui tabel pengaturan untuk multi-store...")
                # 1. Rename tabel lama
                c.execute("ALTER TABLE pengaturan RENAME TO pengaturan_old")
                # 2. Buat tabel baru dengan skema benar
                c.execute("""
                    CREATE TABLE pengaturan (
                        kunci TEXT NOT NULL,
                        nilai TEXT NOT NULL,
                        store_id INTEGER DEFAULT 0 REFERENCES stores(id) ON DELETE CASCADE,
                        PRIMARY KEY (kunci, store_id)
                    )
                """)
                # 3. Pindahkan data - global settings pakai store_id=0, yang lain tetap
                c.execute("""
                    INSERT INTO pengaturan (kunci, nilai, store_id)
                    SELECT kunci, nilai, COALESCE(store_id, 0) FROM pengaturan_old
                """)
                # 4. Hapus tabel lama
                c.execute("DROP TABLE pengaturan_old")
                # 5. Buat index
                c.execute("CREATE INDEX IF NOT EXISTS idx_pengaturan_store ON pengaturan(store_id)")
                print("[MIGRASI] Tabel pengaturan berhasil diperbarui")
            else:
                # Tambah kolom store_id jika belum ada
                try:
                    c.execute("ALTER TABLE pengaturan ADD COLUMN store_id INTEGER DEFAULT 0 REFERENCES stores(id) ON DELETE CASCADE")
                except Exception:
                    pass  # Kolom sudah ada
    except Exception as e:
        print(f"[WARN] Migrasi pengaturan: {e}")
    
    # 6. Assign karyawan ke toko (idempoten P3-4: hanya karyawan yang BELUM
    # punya assignment sama sekali; versi lama hanya jalan saat tabel kosong
    # sehingga karyawan/store baru tidak pernah ter-assign otomatis)
    try:
        # Toko default: id aktif terkecil KECUALI pseudo-store id 0
        # ('Global Settings' bukan toko operasional)
        dflt = c.execute(
            "SELECT id FROM stores WHERE is_active = 1 AND id <> 0 ORDER BY id ASC LIMIT 1"
        ).fetchone()
        if not dflt:
            dflt = c.execute(
                "SELECT id FROM stores WHERE is_active = 1 ORDER BY id ASC LIMIT 1"
            ).fetchone()
        default_store = dflt['id'] if dflt else 1
        c.execute("""
            INSERT INTO user_stores (user_id, store_id, role)
            SELECT u.id, ?, 'kasir' FROM users u
            WHERE u.role = 'karyawan' AND u.aktif = 1
              AND NOT EXISTS (SELECT 1 FROM user_stores us WHERE us.user_id = u.id)
            ON CONFLICT (user_id, store_id) DO NOTHING
        """, (default_store,))
        print(f"[OK] Backfill user_stores ke toko {default_store} (yang belum punya akses)")
    except Exception as e:
        print(f"[WARN] Backfill user_stores: {e}")
    
    print("[OK] Data existing diupdate dengan store_id = 1")


# ─────────────────────────────────────
#  HELPER
# ─────────────────────────────────────


def warn_default_credentials():
    try:
        conn = get_db()
        rows = db_execute(conn, 'SELECT username, password FROM users WHERE aktif=1').fetchall()
        conn.close()
        defaults = {'superadmin': 'superadmin123', 'pemilik': 'pemilik123', 'karyawan': 'karyawan123'}
        for r in rows:
            pw_default = defaults.get((r['username'] or '').lower())
            if pw_default and check_password_hash(r['password'], pw_default):
                print('[WARN] Keamanan: user \'' + r['username'] + '\' masih memakai password default!')
    except Exception as e:
        print('[WARN] Cek kredensial default gagal: ' + str(e))

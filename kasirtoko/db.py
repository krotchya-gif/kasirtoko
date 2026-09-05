"""DB helpers — pindahan murni dari app.py."""

from flask import current_app
from flask import jsonify
from .config import USE_POSTGRES, DB_PATH

if USE_POSTGRES:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    print("Using PostgreSQL database")
else:
    import sqlite3
    print("Using SQLite database")



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


def begin_tx(conn):
    """Mulai transaksi tulis.
    SQLite: BEGIN IMMEDIATE agar write-lock didapat di awal (mencegah race
    double-submit). PostgreSQL: no-op karena psycopg2 sudah membuka transaksi
    implisit per koneksi (dan conn tidak punya .execute)."""
    if not USE_POSTGRES:
        conn.execute("BEGIN IMMEDIATE")


def server_error(pesan="Terjadi kesalahan server"):
    """P2-3: respons 500 generik — detail exception hanya masuk log server,
    tidak dibocorkan ke client."""
    current_app.logger.exception("Internal error")
    return jsonify({'error': pesan}), 500

# ─────────────────────────────────────
#  DATABASE INIT
# ─────────────────────────────────────


def get_db():
    return get_db_connection()


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

"""Auth, decorator & permission — pindahan murni dari app.py."""

from flask import request, jsonify, session
import json
import functools
from .db import get_db, db_execute, row_to_dict, rows_to_list


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


# P2-4: penyimpan percobaan login per IP (in-memory, cukup untuk single-process)


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


def no_ghost_write(f):
    """P2-5: superadmin dalam ghost mode hanya boleh baca (view-only).
    Semua endpoint tulis data wajib memakai decorator ini."""
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        if session.get('is_ghost_mode'):
            return jsonify({'error': 'Mode lihat saja — keluar dari ghost mode untuk mengubah data'}), 403
        return f(*args, **kwargs)
    return decorated


def too_large(e):
    """P2-6: respons JSON ramah saat upload melebihi MAX_CONTENT_LENGTH."""
    return jsonify({'error': 'File terlalu besar (maksimal 2 MB)'}), 413


def not_found(e):
    if request.path.startswith('/api/'):
        return jsonify({'error': 'Tidak ditemukan'}), 404
    return e


_login_attempts = {}

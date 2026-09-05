"""Modul routes/pengguna.py — pindahan murni dari app.py (split Fase 2)."""

from flask import Blueprint
from flask import request, jsonify, session
from werkzeug.security import generate_password_hash, check_password_hash
from ..db import get_db, db_execute, db_execute_insert, rows_to_list, server_error
from ..auth import pemilik_required, get_current_store_id, is_superadmin

bp = Blueprint('pengguna', __name__)


@bp.route('/api/pengguna', methods=['GET'])
@pemilik_required
def get_pengguna():
    conn = get_db()
    rows = db_execute(conn, 
        "SELECT id, username, nama, role, aktif, dibuat FROM pengguna ORDER BY role DESC, nama"
    ).fetchall()
    conn.close()
    return jsonify(rows_to_list(rows))


@bp.route('/api/pengguna', methods=['POST'])
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
        return server_error()
    conn.close()
    return jsonify({'ok': True}), 201


@bp.route('/api/pengguna/<int:uid>', methods=['DELETE'])
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


@bp.route('/api/pengguna/<int:uid>/reset-password', methods=['POST'])
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


@bp.route('/api/pengguna/ganti-password', methods=['POST'])
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
    # Verifikasi password lama. Catatan: id sequence tabel users dan pengguna
    # BERBEDA, jadi cari berdasarkan kecocokan hash di kedua tabel, lalu
    # update keduanya berdasarkan username (bukan id).
    target_username = None
    row_u = db_execute(conn, "SELECT * FROM users WHERE id=?", (uid,)).fetchone()
    if row_u and check_password_hash(row_u['password'], lama):
        target_username = row_u['username']
    else:
        row_p = db_execute(conn, "SELECT * FROM pengguna WHERE id=?", (uid,)).fetchone()
        if row_p and check_password_hash(row_p['password'], lama):
            target_username = row_p['username']
        elif row_u:
            # Fallback: username dari session record, verifikasi ulang via pengguna
            row_p2 = db_execute(conn, "SELECT * FROM pengguna WHERE username=?",
                                (row_u['username'],)).fetchone()
            if row_p2 and check_password_hash(row_p2['password'], lama):
                target_username = row_u['username']
    if not target_username:
        conn.close()
        return jsonify({'error': 'Password lama salah'}), 400
    hashed = generate_password_hash(baru, method='pbkdf2:sha256')
    # Update KEDUA tabel berdasarkan username (login membaca users dulu)
    db_execute(conn, "UPDATE pengguna SET password=? WHERE username=?", (hashed, target_username))
    try:
        db_execute(conn, "UPDATE users SET password=? WHERE username=?", (hashed, target_username))
    except Exception as e:
        print(f"[WARN] Gagal sync password ke users: {e}")
    conn.commit()
    conn.close()
    return jsonify({'ok': True})


# ─────────────────────────────────────
#  INIT DATABASE (SAAT IMPORT/STARTUP)
# ─────────────────────────────────────

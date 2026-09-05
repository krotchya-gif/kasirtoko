"""Modul routes/admin.py — pindahan murni dari app.py (split Fase 2)."""

from flask import Blueprint
from flask import request, jsonify, session
from werkzeug.security import generate_password_hash, check_password_hash
from ..db import get_db, db_execute, db_execute_insert, row_to_dict, rows_to_list, server_error
from ..auth import get_current_user, pemilik_required, superadmin_required, is_superadmin, is_store_owner, can_access_store, get_accessible_stores, log_admin_action

bp = Blueprint('admin', __name__)


@bp.route('/api/admin/stores', methods=['GET'])
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


@bp.route('/api/admin/stores', methods=['POST'])
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
        return server_error()


@bp.route('/api/admin/owners', methods=['POST'])
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
        return server_error()


@bp.route('/api/admin/owners', methods=['GET'])
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


@bp.route('/api/admin/owners/<int:owner_id>/reset-password', methods=['POST'])
@superadmin_required
def admin_reset_password_owner(owner_id):
    """Superadmin reset password pemilik."""
    data = request.json
    password = data.get('password', '').strip()
    
    if not password:
        return jsonify({'error': 'Password baru wajib diisi'}), 400
    if len(password) < 6:
        return jsonify({'error': 'Password minimal 6 karakter'}), 400
    
    conn = get_db()
    
    # Cek pemilik exists
    owner = db_execute(conn, "SELECT * FROM users WHERE id = ? AND role = 'pemilik'", (owner_id,)).fetchone()
    if not owner:
        conn.close()
        return jsonify({'error': 'Pemilik tidak ditemukan'}), 404
    
    # Update password
    hashed_pw = generate_password_hash(password, method='pbkdf2:sha256')
    db_execute(conn, "UPDATE users SET password = ? WHERE id = ?", (hashed_pw, owner_id))
    
    # Sync ke tabel pengguna juga
    try:
        db_execute(conn, "UPDATE pengguna SET password = ? WHERE username = ?", (hashed_pw, owner['username']))
    except:
        pass
    
    conn.commit()
    conn.close()
    
    # Log action
    log_admin_action(session['user_id'], None, 'reset_password_owner', 'users', owner_id, None, {'owner_username': owner['username']})
    
    return jsonify({'ok': True, 'message': f'Password {owner["nama"]} berhasil direset'})


@bp.route('/api/admin/enter-store/<int:store_id>', methods=['POST'])
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


@bp.route('/api/admin/exit-store', methods=['POST'])
@superadmin_required
def admin_exit_store():
    """Superadmin keluar dari ghost mode."""
    store_id = session.get('current_store_id')
    session.pop('current_store_id', None)
    session.pop('is_ghost_mode', None)
    
    if store_id:
        log_admin_action(session['user_id'], store_id, 'exit_store', None, None, None, None)
    
    return jsonify({'ok': True})


@bp.route('/api/admin/logs', methods=['GET'])
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


@bp.route('/api/admin/stores/<int:store_id>', methods=['PUT'])
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
        return server_error()


# ═════════════════════════════════════
#  API: USER STORES (KARYAWAN ASSIGNMENT)
# ═════════════════════════════════════


@bp.route('/api/stores/<int:store_id>/users', methods=['GET'])
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


@bp.route('/api/stores/<int:store_id>/users', methods=['POST'])
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
        return server_error()


@bp.route('/api/stores/<int:store_id>/users/<int:user_id>', methods=['DELETE'])
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


@bp.route('/api/my-stores', methods=['GET'])
def my_stores():
    """Get semua toko yang bisa diakses user saat ini."""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401
    
    stores = get_accessible_stores(user['id'])
    return jsonify(stores)


@bp.route('/api/switch-store/<int:store_id>', methods=['POST'])
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

"""Modul routes/pages.py — pindahan murni dari app.py (split Fase 2)."""

from flask import Blueprint
from flask import request, jsonify, render_template, session, redirect
from werkzeug.security import generate_password_hash, check_password_hash
import time
from ..db import get_db, db_execute
from ..auth import get_current_user, pemilik_required, is_superadmin, get_accessible_stores, _login_attempts
from ..models_init import init_db
from ..config import USE_POSTGRES

bp = Blueprint('pages', __name__)


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
    public_paths = {'/login', '/logout', '/offline', '/sw.js', '/api/health'}
    if request.path in public_paths or request.path.startswith('/static/'):
        return None
    if not session.get('user_id'):
        if request.path.startswith('/api/'):
            return jsonify({'error': 'Sesi berakhir. Silakan login kembali.', 'needLogin': True}), 401
        return redirect('/login')


# ─────────────────────────────────────
#  HALAMAN UTAMA & PWA
# ─────────────────────────────────────


@bp.route('/api/health', methods=['GET'])
def health():
    """P3-6: status backend untuk diagnosa (DB apa yang aktif)."""
    try:
        conn = get_db()
        db_execute(conn, "SELECT 1").fetchone()
        conn.close()
        db_ok = True
    except Exception:
        db_ok = False
    return jsonify({
        'ok': db_ok,
        'db': 'postgres' if USE_POSTGRES else 'sqlite',
        'version': '2.3.0',
    }), (200 if db_ok else 500)


@bp.route('/')
def index():
    user = get_current_user()
    # Get user's stores for the switcher
    stores = []
    if user:
        stores = get_accessible_stores(user['id'])
    return render_template('index.html', user=user, stores=stores)


@bp.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('user_id') and get_current_user():
        return redirect('/')
    error = None
    if request.method == 'POST':
        # P2-4: rate-limit sederhana anti brute-force (10x/menit per IP)
        ip = request.remote_addr or 'unknown'
        now = time.time()
        _login_attempts[ip] = [t for t in _login_attempts.get(ip, []) if now - t < 60]
        if len(_login_attempts[ip]) >= 10:
            error = 'Terlalu banyak percobaan. Coba lagi semenit lagi.'
            return render_template('login.html', error=error), 429
        _login_attempts[ip].append(now)

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


@bp.route('/logout')
def logout():
    session.clear()
    return redirect('/login')


@bp.route('/sw.js')
def service_worker():
    """Service worker harus diakses dari root agar scope-nya '/'"""
    from flask import send_from_directory
    return send_from_directory('static', 'sw.js',
                               mimetype='application/javascript')


@bp.route('/offline')
def offline():
    return render_template('offline.html')


# ═════════════════════════════════════
#  API: SUPERADMIN (MULTI-TENANT)
# ═════════════════════════════════════


@bp.route('/api/pengaturan', methods=['GET'])
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
            # SQLite: gunakan UNION untuk ordering, global settings pakai store_id=0
            rows = db_execute(conn, 
                """SELECT kunci, nilai FROM pengaturan WHERE store_id = ?
                   UNION ALL
                   SELECT kunci, nilai FROM pengaturan 
                   WHERE store_id = 0 
                     AND kunci NOT IN (SELECT kunci FROM pengaturan WHERE store_id = ?)""",
                (store_id, store_id)
            ).fetchall()
        # Store-specific menang (override global)
        result = {}
        for r in rows:
            result[r['kunci']] = r['nilai']
    else:
        # Fallback: ambil semua pengaturan global
        if USE_POSTGRES:
            rows = db_execute(conn, "SELECT kunci, nilai FROM pengaturan WHERE store_id IS NULL").fetchall()
        else:
            rows = db_execute(conn, "SELECT kunci, nilai FROM pengaturan WHERE store_id = 0").fetchall()
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


@bp.route('/api/pengaturan', methods=['POST'])
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
            # SQLite: replace into langsung (upsert workaround untuk partial unique index)
            db_execute(conn, 
                "REPLACE INTO pengaturan (kunci, nilai, store_id) VALUES (?,?,?)",
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

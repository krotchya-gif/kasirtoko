"""Modul routes/pelanggan.py — pindahan murni dari app.py (split Fase 2)."""

from flask import Blueprint
from flask import request, jsonify
from ..db import get_db, db_execute, row_to_dict, rows_to_list
from ..auth import get_current_store_id
from ..config import USE_POSTGRES

bp = Blueprint('pelanggan', __name__)


@bp.route('/api/pelanggan', methods=['GET'])
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


@bp.route('/api/pelanggan', methods=['POST'])
def tambah_pelanggan():
    d    = request.json or {}
    nama = d.get('nama', '').strip()
    if not nama:
        return jsonify({'error': 'Nama tidak boleh kosong'}), 400
    store_id = get_current_store_id()
    conn = get_db()
    # Peringatkan nama duplikat agar kasir tidak salah pilih di autocomplete
    kembar = db_execute(conn,
        "SELECT id, nama, telepon FROM pelanggan WHERE LOWER(nama)=LOWER(?) AND store_id=?",
        (nama, store_id)
    ).fetchall()
    if kembar and not d.get('force'):
        conn.close()
        return jsonify({
            'error': f'Nama "{nama}" sudah ada. Tambah lagi?',
            'duplikat': rows_to_list(kembar),
            'butuh_force': True
        }), 409
    cur  = db_execute(conn,
        "INSERT INTO pelanggan (nama, telepon, alamat, catatan, store_id) VALUES (?,?,?,?,?)",
        (nama, d.get('telepon','').strip(), d.get('alamat','').strip(), d.get('catatan','').strip(), store_id)
    )
    pid = cur.lastrowid
    conn.commit()
    row = row_to_dict(db_execute(conn, "SELECT * FROM pelanggan WHERE id=?", (pid,)).fetchone())
    conn.close()
    return jsonify(row), 201


@bp.route('/api/pelanggan/<int:pid>', methods=['GET'])
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


@bp.route('/api/pelanggan/<int:pid>', methods=['PUT'])
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


@bp.route('/api/pelanggan/<int:pid>', methods=['DELETE'])
def hapus_pelanggan(pid):
    store_id = get_current_store_id()
    conn = get_db()
    # Tolak hapus jika masih ada piutang aktif (jejak penagihan putus)
    menunggak = db_execute(conn, """
        SELECT COUNT(*) AS n, COALESCE(SUM(sisa_piutang), 0) AS s
        FROM transaksi
        WHERE pelanggan_id=? AND store_id=?
          AND metode_bayar='piutang' AND COALESCE(is_lunas, 0)=0
          AND COALESCE(status, 'aktif')='aktif'
    """, (pid, store_id)).fetchone()
    if menunggak and menunggak['n'] > 0:
        conn.close()
        return jsonify({'error': f"Pelanggan masih punya {menunggak['n']} piutang aktif (sisa Rp {menunggak['s']:,}). Lunasi dulu sebelum menghapus."}), 400
    db_execute(conn, "UPDATE transaksi SET pelanggan_id=NULL WHERE pelanggan_id=? AND store_id=?", (pid, store_id))
    db_execute(conn, "DELETE FROM pelanggan WHERE id=? AND store_id=?", (pid, store_id))
    conn.commit()
    conn.close()
    return jsonify({'ok': True})


# ─────────────────────────────────────
#  API: LAPORAN & STATISTIK
# ─────────────────────────────────────

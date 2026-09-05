"""Modul routes/piutang.py — pindahan murni dari app.py (split Fase 2)."""

from flask import Blueprint
from flask import request, jsonify
from datetime import datetime
from ..db import get_db, db_execute, db_execute_insert, row_to_dict, begin_tx, server_error
from ..auth import get_current_user, login_required, no_ghost_write, get_current_store_id
from ..config import USE_POSTGRES

bp = Blueprint('piutang', __name__)


@bp.route('/api/piutang', methods=['GET'])
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

    # Ambil history pembayaran sekaligus untuk semua piutang (hindari N+1)
    ids = [r['id'] for r in rows]
    hist_map = {}
    if ids:
        placeholders = ",".join(["?"] * len(ids))
        for h in db_execute(conn, f"""
            SELECT * FROM piutang_bayar
            WHERE transaksi_id IN ({placeholders}) ORDER BY waktu DESC
        """, ids).fetchall():
            hd = row_to_dict(h)
            hist_map.setdefault(hd['transaksi_id'], []).append(hd)

    # Ambil history pembayaran untuk setiap piutang
    result = []
    for row in rows:
        piutang = row_to_dict(row)

        # Hitung total sudah dibayar dari piutang_bayar
        history = hist_map.get(piutang['id'], [])

        piutang['history_bayar'] = history
        piutang['total_bayar'] = sum(h['nominal'] for h in history)
        piutang['sisa_real'] = piutang['total'] - piutang['total_bayar']

        result.append(piutang)
    
    conn.close()
    return jsonify(result)


@bp.route('/api/piutang/<int:tid>/bayar', methods=['POST'])
@login_required
@no_ghost_write
def bayar_piutang(tid):
    """Bayar cicilan piutang (partial atau full)."""
    d = request.json or {}
    nominal = d.get('nominal', 0)
    metode = d.get('metode_bayar', 'tunai')
    catatan = d.get('catatan', '').strip()
    idem_key = (d.get('idempotency_key') or '').strip()[:64]
    
    if nominal <= 0:
        return jsonify({'error': 'Nominal pembayaran harus lebih dari 0'}), 400
    
    user = get_current_user()
    store_id = get_current_store_id()

    conn = get_db()
    begin_tx(conn)

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

        # Idempotency: tolak retry double-submit dengan key yang sama
        if idem_key:
            duplikat = db_execute(conn, """
                SELECT id FROM piutang_bayar WHERE transaksi_id=? AND idempotency_key=?
            """, (tid, idem_key)).fetchone()
            if duplikat:
                conn.rollback()
                conn.close()
                return jsonify({'error': 'Pembayaran ini sudah diproses (duplikat ditolak)', 'duplikat': True}), 409

        # Insert ke piutang_bayar
        cur = db_execute_insert(conn, """
            INSERT INTO piutang_bayar
            (transaksi_id, nominal, metode_bayar, catatan, dibuat_oleh, store_id, idempotency_key)
            VALUES (?,?,?,?,?,?,?)
        """, (tid, nominal, metode, catatan, user['nama'], store_id, idem_key))
        
        bayar_id = cur.lastrowid
        
        # Update total terbayar di transaksi
        total_terbayar = total_sudah_bayar + nominal
        sisa_baru = trx['total'] - total_terbayar
        is_lunas = 1 if sisa_baru <= 0 else 0
        
        if is_lunas == 1:
            if USE_POSTGRES:
                db_execute(conn, """
                    UPDATE transaksi 
                    SET terbayar=?, sisa_piutang=?, is_lunas=?, waktu=CURRENT_TIMESTAMP
                    WHERE id=?
                """, (total_terbayar, max(0, sisa_baru), is_lunas, tid))
            else:
                db_execute(conn, """
                    UPDATE transaksi 
                    SET terbayar=?, sisa_piutang=?, is_lunas=?, waktu=datetime('now','localtime')
                    WHERE id=?
                """, (total_terbayar, max(0, sisa_baru), is_lunas, tid))
        else:
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
        return server_error()


@bp.route('/api/piutang/<int:tid>/history', methods=['GET'])
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


@bp.route('/api/piutang/reminder', methods=['GET'])
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

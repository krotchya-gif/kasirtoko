"""Modul routes/kas.py — pindahan murni dari app.py (split Fase 2)."""

from flask import Blueprint
from flask import request, jsonify
from ..db import get_db, db_execute, row_to_dict, rows_to_list
from ..auth import get_current_user, pemilik_required, no_ghost_write, get_current_store_id

bp = Blueprint('kas', __name__)


@bp.route('/api/kas', methods=['GET'])
@pemilik_required
def get_kas():
    dari  = request.args.get('dari', '')
    ke    = request.args.get('ke', '')
    store_id = get_current_store_id()
    conn  = get_db()
    sql   = "SELECT * FROM kas WHERE store_id = ?"
    params = [store_id]
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
        FROM kas WHERE store_id = ?
    """
    stat_params = [store_id]
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
        FROM kas WHERE store_id = ?
    """, (store_id,)).fetchone()
    stat['saldo']         = saldo_row['saldo']
    stat['saldo_tunai']   = saldo_row['saldo_tunai']
    stat['saldo_nontunai']= saldo_row['saldo_nontunai']
    conn.close()
    return jsonify({'rows': rows, 'stats': stat})


@bp.route('/api/kas', methods=['POST'])
@pemilik_required
@no_ghost_write
def tambah_kas():
    d = request.json
    tipe       = d.get('tipe')
    jumlah     = int(d.get('jumlah', 0))
    keterangan = d.get('keterangan', '').strip()
    metode     = d.get('metode', 'tunai')
    store_id   = get_current_store_id()
    if metode not in ('tunai', 'transfer', 'qris'):
        metode = 'tunai'
    if tipe not in ('pemasukan', 'pengeluaran') or jumlah <= 0:
        return jsonify({'error': 'Data tidak valid'}), 400
    conn = get_db()
    cur = db_execute(conn, 
        "INSERT INTO kas (tipe, jumlah, keterangan, metode, store_id) VALUES (?,?,?,?,?)",
        (tipe, jumlah, keterangan, metode, store_id)
    )
    kid = cur.lastrowid
    conn.commit()
    row = row_to_dict(db_execute(conn, "SELECT * FROM kas WHERE id=?", (kid,)).fetchone())
    conn.close()
    return jsonify(row), 201


@bp.route('/api/kas/<int:kid>', methods=['DELETE'])
@pemilik_required
def hapus_kas(kid):
    store_id = get_current_store_id()
    conn = get_db()
    db_execute(conn, "DELETE FROM kas WHERE id=? AND store_id=?", (kid, store_id))
    conn.commit()
    conn.close()
    return jsonify({'ok': True})


@bp.route('/api/kas/reset', methods=['POST'])
@pemilik_required
def reset_saldo_kas():
    """Reset saldo dompet ke 0 dengan konfirmasi.
    Riwayat TIDAK dihapus: saldo dinolkan lewat jurnal penyeimbang agar
    audit (void, piutang, tutup kasir) tetap bisa direkonsiliasi."""
    d = request.json or {}
    konfirmasi = d.get('konfirmasi', '').strip()

    if konfirmasi != 'Reset Saldo':
        return jsonify({'error': 'Konfirmasi tidak valid. Ketik "Reset Saldo" untuk melanjutkan.'}), 400

    user = get_current_user()
    store_id = get_current_store_id()
    conn = get_db()
    saldo = db_execute(conn,
        "SELECT COALESCE(SUM(CASE WHEN tipe='pemasukan' THEN jumlah ELSE -jumlah END), 0) AS s FROM kas WHERE store_id=?",
        (store_id,)
    ).fetchone()['s']
    if saldo > 0:
        db_execute(conn,
            "INSERT INTO kas (tipe, jumlah, keterangan, metode, store_id) VALUES (?,?,?,?,?)",
            ('pengeluaran', saldo, f"Reset saldo oleh {user['nama']}", 'tunai', store_id)
        )
    elif saldo < 0:
        db_execute(conn,
            "INSERT INTO kas (tipe, jumlah, keterangan, metode, store_id) VALUES (?,?,?,?,?)",
            ('pemasukan', -saldo, f"Reset saldo oleh {user['nama']}", 'tunai', store_id)
        )
    conn.commit()
    conn.close()
    return jsonify({'ok': True, 'message': 'Saldo dompet berhasil direset', 'saldo_sebelum': saldo, 'saldo': 0})


# ─────────────────────────────────────
#  TUTUP KASIR (pindahan dari laporan.py — menulis entri kas)
# ─────────────────────────────────────


@bp.route('/api/tutup-kasir/preview', methods=['GET'])
def tutup_kasir_preview():
    """Hitung transaksi yang belum ditutup (tutup_kasir_id IS NULL)."""
    store_id = get_current_store_id()
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
          AND store_id = ?
    """, (store_id,)).fetchone()
    conn.close()
    return jsonify(row_to_dict(row))


@bp.route('/api/tutup-kasir', methods=['POST'])
@no_ghost_write
def buat_tutup_kasir():
    """Karyawan/pemilik proses tutup kasir → status pending."""
    user = get_current_user()
    d = request.json or {}
    keterangan = d.get('keterangan', '').strip()
    store_id = get_current_store_id()

    conn = get_db()
    # Kunci tulis di awal agar double-submit paralel tidak membuat 2 closing
    # untuk transaksi yang sama (request kedua melihat jumlah 0 setelah
    # request pertama commit).
    begin_tx(conn)
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
          AND store_id = ?
    """, (store_id,)).fetchone()

    if row['jumlah_trx'] == 0:
        conn.rollback()
        conn.close()
        return jsonify({'error': 'Tidak ada transaksi yang belum ditutup'}), 400

    # Buat record tutup_kasir
    cur = db_execute(conn, 
        """INSERT INTO tutup_kasir
           (total, total_tunai, total_transfer, total_qris, jumlah_trx, keterangan, dibuat_oleh, store_id)
           VALUES (?,?,?,?,?,?,?,?)""",
        (row['total'], row['total_tunai'], row['total_transfer'], row['total_qris'],
         row['jumlah_trx'], keterangan, user['nama'], store_id)
    )
    tk_id = cur.lastrowid

    # Tandai semua transaksi belum tutup dengan id ini (hanya yang aktif)
    db_execute(conn, 
        "UPDATE transaksi SET tutup_kasir_id=? WHERE tutup_kasir_id IS NULL AND COALESCE(status, 'aktif') = 'aktif' AND store_id=?",
        (tk_id, store_id)
    )
    conn.commit()

    result = row_to_dict(db_execute(conn, 
        "SELECT * FROM tutup_kasir WHERE id=?", (tk_id,)
    ).fetchone())
    conn.close()
    return jsonify(result), 201


@bp.route('/api/tutup-kasir', methods=['GET'])
@pemilik_required
def list_tutup_kasir():
    """Pemilik: ambil riwayat tutup kasir + jumlah pending."""
    store_id = get_current_store_id()
    conn = get_db()
    rows = rows_to_list(db_execute(conn, 
        "SELECT * FROM tutup_kasir WHERE store_id=? ORDER BY waktu DESC LIMIT 50",
        (store_id,)
    ).fetchall())
    pending = db_execute(conn, 
        "SELECT COUNT(*) AS n FROM tutup_kasir WHERE status='pending' AND store_id=?",
        (store_id,)
    ).fetchone()['n']
    conn.close()
    return jsonify({'rows': rows, 'pending': pending})


@bp.route('/api/tutup-kasir/<int:tk_id>/konfirmasi', methods=['POST'])
@pemilik_required
def konfirmasi_tutup_kasir(tk_id):
    """Pemilik konfirmasi → buat entri kas pemasukan per metode."""
    user = get_current_user()
    store_id = get_current_store_id()
    conn = get_db()
    tk = db_execute(conn, "SELECT * FROM tutup_kasir WHERE id=? AND store_id=?", (tk_id, store_id)).fetchone()
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
                "INSERT INTO kas (tipe, jumlah, keterangan, metode, store_id) VALUES (?,?,?,?,?)",
                ('pemasukan', jumlah, ket, metode, store_id)
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

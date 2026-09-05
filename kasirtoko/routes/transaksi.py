"""Modul routes/transaksi.py — pindahan murni dari app.py (split Fase 2)."""

from flask import current_app
from flask import Blueprint
from flask import request, jsonify
from datetime import datetime
import os
import csv
from ..db import get_db, db_execute, db_execute_insert, row_to_dict, rows_to_list, begin_tx, server_error
from ..auth import get_current_user, login_required, pemilik_required, no_ghost_write, get_current_store_id
from ..config import USE_POSTGRES, BACKUP_DIR

bp = Blueprint('transaksi', __name__)


@bp.route('/api/transaksi', methods=['POST'])
@login_required
@no_ghost_write
def buat_transaksi():
    d = request.json or {}
    items        = d.get('items', [])
    diskon_val   = d.get('diskon_val', 0) or 0
    diskon_tipe  = d.get('diskon_tipe', 'persen')
    bayar_in     = d.get('bayar', 0) or 0
    pelanggan_id = d.get('pelanggan_id') or None
    metode_bayar = d.get('metode_bayar', 'tunai')
    store_id     = get_current_store_id()
    user         = get_current_user()

    if not items:
        return jsonify({'error': 'Keranjang kosong'}), 400
    if diskon_tipe not in ('persen', 'nominal'):
        diskon_tipe = 'persen'
    try:
        diskon_val = float(diskon_val)
        bayar_in = int(float(bayar_in))
    except (ValueError, TypeError):
        return jsonify({'error': 'Nilai diskon/bayar tidak valid'}), 400
    if diskon_val < 0:
        return jsonify({'error': 'Diskon tidak boleh negatif'}), 400
    if diskon_tipe == 'persen' and diskon_val > 100:
        return jsonify({'error': 'Diskon persen maksimal 100'}), 400

    conn = get_db()
    try:
        # Validasi tiap item ke database (harga, stok, kepemilikan toko)
        lines = []
        kurang_stok = []
        for item in items:
            try:
                pid = int(item.get('id'))
                qty = int(item.get('qty', 0))
            except (ValueError, TypeError, AttributeError):
                conn.close()
                return jsonify({'error': 'Item tidak valid'}), 400
            if qty <= 0:
                conn.close()
                return jsonify({'error': 'Qty harus lebih dari 0'}), 400
            prod = db_execute(conn,
                "SELECT id, nama, harga, stok, emoji FROM produk WHERE id=? AND store_id=? AND aktif=1",
                (pid, store_id)
            ).fetchone()
            if not prod:
                conn.close()
                return jsonify({'error': f'Produk id {pid} tidak ditemukan di toko ini'}), 400
            if prod['stok'] < qty:
                kurang_stok.append(f"{prod['nama']} (tersedia {prod['stok']}, diminta {qty})")
            lines.append({'produk': row_to_dict(prod), 'qty': qty})

        if kurang_stok:
            conn.close()
            return jsonify({'error': 'Stok tidak cukup: ' + '; '.join(kurang_stok)}), 400

        # Hitung ulang di server (jangan percaya total dari client)
        subtotal = sum(l['produk']['harga'] * l['qty'] for l in lines)
        if diskon_tipe == 'persen':
            diskon = round(subtotal * diskon_val / 100)
        else:
            diskon = int(diskon_val)
        diskon = min(diskon, subtotal)
        total = subtotal - diskon

        # Validasi pelanggan milik toko ini
        if pelanggan_id is not None:
            try:
                pelanggan_id = int(pelanggan_id)
            except (ValueError, TypeError):
                conn.close()
                return jsonify({'error': 'pelanggan_id tidak valid'}), 400
            plg = db_execute(conn,
                "SELECT 1 FROM pelanggan WHERE id=? AND store_id=?", (pelanggan_id, store_id)
            ).fetchone()
            if not plg:
                conn.close()
                return jsonify({'error': 'Pelanggan tidak ditemukan di toko ini'}), 400

        # Handle piutang/hutang
        is_piutang = metode_bayar == 'piutang'
        if is_piutang:
            if bayar_in < 0:
                conn.close()
                return jsonify({'error': 'Pembayaran awal tidak boleh negatif'}), 400
            terbayar = min(bayar_in, total)
            sisa_piutang = total - terbayar
            is_lunas = 1 if sisa_piutang <= 0 else 0
            bayar = terbayar
            kembalian = 0  # Piutang tidak ada kembalian
        else:
            if metode_bayar not in ('tunai', 'transfer', 'qris'):
                metode_bayar = 'tunai'
            is_lunas = 1
            terbayar = total
            sisa_piutang = 0
            if metode_bayar == 'tunai':
                bayar = bayar_in
                kembalian = bayar - total
                if kembalian < 0:
                    conn.close()
                    return jsonify({'error': f'Uang bayar kurang Rp {total - bayar:,}'}), 400
            else:
                bayar = total
                kembalian = 0

        # Generate no_trx unik dengan suffix counter untuk menghindari duplikat
        base_no_trx = 'TRX' + datetime.now().strftime('%y%m%d%H%M%S')

        begin_tx(conn)
        trx_id = None
        no_trx = None
        now_sql = "CURRENT_TIMESTAMP" if USE_POSTGRES else "datetime('now','localtime')"
        for attempt in range(6):
            cand = base_no_trx if attempt == 0 else f"{base_no_trx}-{attempt:03d}"
            try:
                cur = db_execute_insert(conn,
                    f"""INSERT INTO transaksi
                       (no_trx, waktu, subtotal, diskon, diskon_val, diskon_tipe, total, bayar, kembalian,
                        kasir, pelanggan_id, metode_bayar, is_lunas, terbayar, sisa_piutang, store_id)
                       VALUES (?,{now_sql},?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (cand, subtotal, diskon, diskon_val, diskon_tipe, total, bayar, kembalian,
                     user['nama'] if user else 'Kasir 1',
                     pelanggan_id, metode_bayar, is_lunas, terbayar, sisa_piutang, store_id)
                )
                trx_id = cur.lastrowid
                no_trx = cand
                break
            except Exception as e:
                if 'UNIQUE' in str(e).upper() and attempt < 5:
                    continue
                raise
        if trx_id is None:
            raise RuntimeError('Gagal membuat nomor transaksi unik')

        # Insert item, kurangi stok, catat stok_log keluar
        for l in lines:
            p, qty = l['produk'], l['qty']
            db_execute(conn,
                """INSERT INTO transaksi_item
                   (transaksi_id, produk_id, nama_produk, emoji, harga, qty, subtotal)
                   VALUES (?,?,?,?,?,?,?)""",
                (trx_id, p['id'], p['nama'], p.get('emoji') or '[BOX]',
                 p['harga'], qty, p['harga'] * qty)
            )
            stok_sebelum = p['stok']
            stok_sesudah = stok_sebelum - qty
            db_execute(conn,
                "UPDATE produk SET stok = ? WHERE id=?",
                (stok_sesudah, p['id'])
            )
            db_execute(conn,
                """INSERT INTO stok_log
                   (produk_id, tipe, jumlah, stok_sebelum, stok_sesudah,
                    alasan, keterangan, transaksi_id, dibuat_oleh, store_id)
                   VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (p['id'], 'keluar', qty, stok_sebelum, stok_sesudah,
                 'penjualan', f'Penjualan {no_trx}', trx_id,
                 user['nama'] if user else '', store_id)
            )

        # NOTE (P1-5 Opsi A): kas TIDAK dicatat di sini. Pemasukan kas hanya
        # dicatat saat tutup kasir dikonfirmasi, agar tidak double-count.
        # Pelunasan piutang tetap dicatat di bayar_piutang().

        conn.commit()

        # Return transaksi lengkap
        trx = row_to_dict(db_execute(conn, "SELECT * FROM transaksi WHERE id=?", (trx_id,)).fetchone())
        trx['items'] = rows_to_list(db_execute(conn,
            "SELECT * FROM transaksi_item WHERE transaksi_id=?", (trx_id,)
        ).fetchall())

        conn.close()
        return jsonify(trx), 201

    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
        conn.close()
        current_app.logger.exception("buat_transaksi gagal")
        return jsonify({'error': 'Gagal memproses transaksi'}), 500


@bp.route('/api/transaksi', methods=['GET'])
def get_transaksi():
    tgl_dari = request.args.get('dari', '')
    tgl_ke   = request.args.get('ke', '')
    status   = request.args.get('status', '')  # aktif, void, atau kosong (semua)
    limit    = min(int(request.args.get('limit', 100)), 500)
    offset   = max(int(request.args.get('offset', 0)), 0)
    store_id = get_current_store_id()

    conn = get_db()
    sql = """
        SELECT t.*, COALESCE(p.nama, '') AS pelanggan_nama
        FROM transaksi t
        LEFT JOIN pelanggan p ON p.id = t.pelanggan_id
        WHERE t.store_id = ?
    """
    params = [store_id]
    if tgl_dari:
        sql += " AND DATE(t.waktu) >= ?"
        params.append(tgl_dari)
    if tgl_ke:
        sql += " AND DATE(t.waktu) <= ?"
        params.append(tgl_ke)
    if status:
        sql += " AND COALESCE(t.status, 'aktif') = ?"
        params.append(status)
    sql += " ORDER BY t.waktu DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    rows = db_execute(conn, sql, params).fetchall()
    # Batch ambil items sekaligus (hindari N+1 query)
    trx_ids = [r['id'] for r in rows]
    items_map = {}
    if trx_ids:
        placeholders = ",".join(["?"] * len(trx_ids))
        for it in db_execute(conn,
            f"SELECT * FROM transaksi_item WHERE transaksi_id IN ({placeholders})",
            trx_ids
        ).fetchall():
            items_map.setdefault(it['transaksi_id'], []).append(row_to_dict(it))
    result = []
    for r in rows:
        trx = row_to_dict(r)
        trx['items'] = items_map.get(r['id'], [])
        result.append(trx)
    conn.close()
    return jsonify(result)


@bp.route('/api/transaksi/<int:tid>', methods=['GET'])
def get_transaksi_by_id(tid):
    store_id = get_current_store_id()
    conn = get_db()
    trx = db_execute(conn, """
        SELECT t.*, COALESCE(p.nama, '') AS pelanggan_nama
        FROM transaksi t
        LEFT JOIN pelanggan p ON p.id = t.pelanggan_id
        WHERE t.id=? AND t.store_id=?
    """, (tid, store_id)).fetchone()
    if not trx:
        conn.close()
        return jsonify({'error': 'Tidak ditemukan'}), 404
    result = row_to_dict(trx)
    result['items'] = rows_to_list(db_execute(conn, 
        "SELECT * FROM transaksi_item WHERE transaksi_id=?", (tid,)
    ).fetchall())
    conn.close()
    return jsonify(result)


# ─────────────────────────────────────
#  API: KAS / DOMPET
# ─────────────────────────────────────


@bp.route('/api/transaksi/<int:tid>/void', methods=['POST'])
@pemilik_required
@no_ghost_write
def void_transaksi(tid):
    """Void transaksi: kembalikan stok dan tandai transaksi sebagai void."""
    user = get_current_user()
    store_id = get_current_store_id()
    d = request.json or {}
    reason = d.get('reason', '').strip()

    if not reason:
        return jsonify({'error': 'Alasan void wajib diisi'}), 400

    conn = get_db()
    begin_tx(conn)

    try:
        # Cek transaksi exists, belum void, dan milik toko aktif
        trx = db_execute(conn,
            "SELECT * FROM transaksi WHERE id=? AND store_id=?", (tid, store_id)
        ).fetchone()
        
        if not trx:
            conn.rollback()
            conn.close()
            return jsonify({'error': 'Transaksi tidak ditemukan'}), 404
        
        if trx.get('status') == 'void':
            conn.rollback()
            conn.close()
            return jsonify({'error': 'Transaksi sudah di-void sebelumnya'}), 400
        
        # Jika transaksi sudah masuk tutup kasir yang confirmed, tidak bisa void
        if trx.get('tutup_kasir_id'):
            tk = db_execute(conn, 
                "SELECT status FROM tutup_kasir WHERE id=?", (trx['tutup_kasir_id'],)
            ).fetchone()
            if tk and tk['status'] == 'confirmed':
                conn.rollback()
                conn.close()
                return jsonify({'error': 'Transaksi sudah ditutup dan dikonfirmasi, tidak bisa di-void'}), 400
        
        waktu_now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Kembalikan stok untuk setiap item
        items = db_execute(conn, 
            "SELECT * FROM transaksi_item WHERE transaksi_id=?", (tid,)
        ).fetchall()
        
        for item in items:
            produk_id = item['produk_id']
            qty = item['qty']
            
            # Get stok saat ini
            prod = db_execute(conn, 
                "SELECT stok FROM produk WHERE id=?", (produk_id,)
            ).fetchone()
            
            if prod:
                stok_sebelum = prod['stok']
                stok_sesudah = stok_sebelum + qty
                
                # Update stok produk
                db_execute(conn, 
                    "UPDATE produk SET stok = stok + ? WHERE id=?",
                    (qty, produk_id)
                )
                
                # Catat di stok_log (void)
                db_execute(conn, 
                    """INSERT INTO stok_log 
                       (produk_id, tipe, jumlah, stok_sebelum, stok_sesudah, 
                        alasan, keterangan, transaksi_id, dibuat_oleh)
                       VALUES (?,?,?,?,?,?,?,?,?)""",
                    (produk_id, 'masuk', qty, stok_sebelum, stok_sesudah,
                     'void_transaksi', f'Pengembalian stok dari void transaksi {trx["no_trx"]}', 
                     tid, user['nama'])
                )
        
        # Update status transaksi menjadi void
        db_execute(conn, 
            """UPDATE transaksi 
               SET status='void', void_reason=?, void_by=?, void_at=?
               WHERE id=?""",
            (reason, user['nama'], waktu_now, tid)
        )
        
        # Jika transaksi sudah lunas (bukan piutang), keluarkan dari kas
        if trx.get('is_lunas', 1) == 1 and trx.get('metode_bayar') != 'piutang':
            db_execute(conn,
                """INSERT INTO kas (tipe, jumlah, keterangan, metode, store_id) 
                   VALUES (?,?,?,?,?)""",
                ('pengeluaran', trx['total'], 
                 f'Void transaksi {trx["no_trx"]}: {reason}',
                 trx.get('metode_bayar', 'tunai'),
                 store_id)
            )
        
        conn.commit()
        
        # Return updated transaksi
        result = row_to_dict(db_execute(conn, 
            "SELECT * FROM transaksi WHERE id=?", (tid,)
        ).fetchone())
        conn.close()
        
        return jsonify({'ok': True, 'transaksi': result})
        
    except Exception as e:
        conn.rollback()
        conn.close()
        return server_error()


@bp.route('/api/transaksi/<int:tid>/restore', methods=['POST'])
@pemilik_required
@no_ghost_write
def restore_transaksi(tid):
    """Restore transaksi yang sudah di-void (batalkan void)."""
    user = get_current_user()
    store_id = get_current_store_id()
    conn = get_db()
    begin_tx(conn)

    try:
        # Cek transaksi exists, status void, dan milik toko aktif
        trx = db_execute(conn,
            "SELECT * FROM transaksi WHERE id=? AND store_id=?", (tid, store_id)
        ).fetchone()

        if not trx:
            conn.rollback()
            conn.close()
            return jsonify({'error': 'Transaksi tidak ditemukan'}), 404

        if trx.get('status') != 'void':
            conn.rollback()
            conn.close()
            return jsonify({'error': 'Transaksi tidak dalam status void'}), 400

        # Jika transaksi sudah masuk tutup kasir yang confirmed, tidak bisa restore
        if trx.get('tutup_kasir_id'):
            tk = db_execute(conn,
                "SELECT status FROM tutup_kasir WHERE id=?", (trx['tutup_kasir_id'],)
            ).fetchone()
            if tk and tk['status'] == 'confirmed':
                conn.rollback()
                conn.close()
                return jsonify({'error': 'Transaksi sudah ditutup dan dikonfirmasi, tidak bisa di-restore'}), 400
        
        # Kurangi stok kembali (karena transaksi di-restore)
        items = db_execute(conn, 
            "SELECT * FROM transaksi_item WHERE transaksi_id=?", (tid,)
        ).fetchall()
        
        # Validasi stok terlebih dahulu
        stok_tidak_cukup = []
        for item in items:
            produk_id = item['produk_id']
            qty = item['qty']
            
            prod = db_execute(conn, 
                "SELECT nama, stok FROM produk WHERE id=? AND store_id=?", (produk_id, store_id)
            ).fetchone()
            
            if prod and prod['stok'] < qty:
                stok_tidak_cukup.append({
                    'nama': prod['nama'],
                    'stok_tersedia': prod['stok'],
                    'stok_dibutuhkan': qty
                })
        
        # Jika ada stok yang tidak cukup, beri warning tapi tetap lanjutkan (stok jadi negatif)
        if stok_tidak_cukup:
            # Log warning - tetap lanjutkan tapi catat
            print(f"[WARN] Restore transaksi {trx['no_trx']}: Stok tidak cukup untuk {len(stok_tidak_cukup)} produk")
        
        for item in items:
            produk_id = item['produk_id']
            qty = item['qty']
            
            # Get stok saat ini
            prod = db_execute(conn, 
                "SELECT nama, stok FROM produk WHERE id=? AND store_id=?", (produk_id, store_id)
            ).fetchone()
            
            if prod:
                stok_sebelum = prod['stok']
                stok_sesudah = stok_sebelum - qty  # Bisa negatif
                
                # Update stok produk (boleh negatif untuk kasus restore)
                db_execute(conn, 
                    "UPDATE produk SET stok = ? WHERE id=?",
                    (stok_sesudah, produk_id)
                )
                
                # Catat di stok_log (restore)
                db_execute(conn, 
                    """INSERT INTO stok_log 
                       (produk_id, tipe, jumlah, stok_sebelum, stok_sesudah, 
                        alasan, keterangan, transaksi_id, dibuat_oleh, store_id)
                       VALUES (?,?,?,?,?,?,?,?,?,?)""",
                    (produk_id, 'keluar', qty, stok_sebelum, stok_sesudah,
                     'restore_transaksi', f'Pengurangan stok dari restore transaksi {trx["no_trx"]}', 
                     tid, user['nama'], store_id)
                )
        
        # Update status transaksi menjadi aktif
        db_execute(conn, 
            """UPDATE transaksi 
               SET status='aktif', void_reason='', void_by='', void_at=''
               WHERE id=?""",
            (tid,)
        )
        
        # Jika transaksi lunas (bukan piutang), masukkan kembali ke kas
        if trx.get('is_lunas', 1) == 1 and trx.get('metode_bayar') != 'piutang':
            db_execute(conn,
                """INSERT INTO kas (tipe, jumlah, keterangan, metode, store_id) 
                   VALUES (?,?,?,?,?)""",
                ('pemasukan', trx['total'], 
                 f'Restore transaksi {trx["no_trx"]}',
                 trx.get('metode_bayar', 'tunai'),
                 store_id)
            )
        
        conn.commit()
        
        result = row_to_dict(db_execute(conn, 
            "SELECT * FROM transaksi WHERE id=?", (tid,)
        ).fetchone())
        conn.close()
        
        return jsonify({'ok': True, 'transaksi': result})
        
    except Exception as e:
        conn.rollback()
        conn.close()
        return server_error()


# ═════════════════════════════════════
#  API: PIUTANG (PELUNASAN CICILAN)
# ═════════════════════════════════════


@bp.route('/api/transaksi/reset', methods=['POST'])
@pemilik_required
@no_ghost_write
def reset_transaksi():
    """Reset seluruh data transaksi + dompet toko aktif.
    Yang dihapus (scope toko aktif saja): transaksi, transaksi_item,
    piutang_bayar, tutup_kasir, kas.
    Yang TIDAK disentuh: produk (termasuk stok), pelanggan, pengguna, pengaturan.
    Selalu backup ke CSV di folder backups/ sebelum menghapus."""
    d = request.json or {}
    if (d.get('konfirmasi') or '').strip() != 'RESET TRANSAKSI':
        return jsonify({'error': 'Konfirmasi tidak valid. Ketik "RESET TRANSAKSI" untuk melanjutkan.'}), 400

    user = get_current_user()
    store_id = get_current_store_id()
    conn = get_db()
    try:
        # 1. Backup dulu (CSV per tabel, prefix timestamp + store)
        backup_dir = BACKUP_DIR
        os.makedirs(backup_dir, exist_ok=True)
        ts = datetime.now().strftime('%Y%m%d%H%M%S')
        prefix = f'reset-store{store_id}-{ts}'
        backup_files = []

        def _dump(nama, sql, params):
            rows = db_execute(conn, sql, params).fetchall()
            if not rows:
                return 0
            path = os.path.join(backup_dir, f'{prefix}-{nama}.csv')
            with open(path, 'w', newline='', encoding='utf-8-sig') as fh:
                w = csv.writer(fh)
                cols = list(rows[0].keys()) if USE_POSTGRES else rows[0].keys()
                w.writerow(cols)
                for r in rows:
                    w.writerow([r[k] for k in cols])
            backup_files.append(os.path.basename(path))
            return len(rows)

        n_trx = _dump('transaksi', "SELECT * FROM transaksi WHERE store_id=?", (store_id,))
        n_item = _dump('transaksi_item',
            """SELECT ti.* FROM transaksi_item ti
               JOIN transaksi t ON t.id = ti.transaksi_id WHERE t.store_id=?""", (store_id,))
        n_piutang = _dump('piutang_bayar',
            """SELECT pb.* FROM piutang_bayar pb
               JOIN transaksi t ON t.id = pb.transaksi_id WHERE t.store_id=?""", (store_id,))
        n_tutup = _dump('tutup_kasir', "SELECT * FROM tutup_kasir WHERE store_id=?", (store_id,))
        n_kas = _dump('kas', "SELECT * FROM kas WHERE store_id=?", (store_id,))

        # 2. Hapus berurutan (eksplisit, tidak mengandalkan CASCADE)
        begin_tx(conn)
        db_execute(conn,
            "DELETE FROM transaksi_item WHERE transaksi_id IN (SELECT id FROM transaksi WHERE store_id=?)",
            (store_id,))
        db_execute(conn,
            "DELETE FROM piutang_bayar WHERE transaksi_id IN (SELECT id FROM transaksi WHERE store_id=?)",
            (store_id,))
        # (pengaman bila ada baris piutang dengan store_id tak konsisten)
        db_execute(conn, "DELETE FROM piutang_bayar WHERE store_id=?", (store_id,))
        db_execute(conn, "DELETE FROM transaksi WHERE store_id=?", (store_id,))
        db_execute(conn, "DELETE FROM tutup_kasir WHERE store_id=?", (store_id,))
        db_execute(conn, "DELETE FROM kas WHERE store_id=?", (store_id,))
        conn.commit()
        conn.close()
        return jsonify({
            'ok': True,
            'message': 'Data transaksi & dompet berhasil direset (produk & pelanggan aman)',
            'dihapus': {'transaksi': n_trx, 'item': n_item, 'piutang_bayar': n_piutang,
                        'tutup_kasir': n_tutup, 'kas': n_kas},
            'backup': backup_files,
            'oleh': user['nama'] if user else '',
        })
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        conn.close()
        return server_error('Gagal mereset transaksi')


# ─────────────────────────────────────
#  API: PRODUK TERJUAL (Aggregasi)
# ─────────────────────────────────────

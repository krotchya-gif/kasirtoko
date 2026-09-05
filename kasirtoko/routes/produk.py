"""Modul routes/produk.py — pindahan murni dari app.py (split Fase 2)."""

from flask import Blueprint
from flask import request, jsonify, send_file
from datetime import datetime
import os
import csv
import io
from ..db import get_db, db_execute, row_to_dict, rows_to_list, begin_tx, server_error
from ..auth import get_current_user, pemilik_required, no_ghost_write, get_current_store_id
from ..config import USE_POSTGRES, BACKUP_DIR

bp = Blueprint('produk', __name__)


@bp.route('/api/produk', methods=['GET'])
def get_produk():
    kategori = request.args.get('kategori', '')
    cari     = request.args.get('cari', '')
    barcode  = request.args.get('barcode', '')
    limit    = int(request.args.get('limit', 500))
    store_id = get_current_store_id()
    conn = get_db()
    
    # Jika ada barcode, cari exact match
    if barcode:
        row = db_execute(conn, 
            "SELECT * FROM produk WHERE barcode=? AND store_id=? AND aktif=1", (barcode, store_id)
        ).fetchone()
        conn.close()
        if row:
            return jsonify(dict(row))
        return jsonify({'error': 'Produk tidak ditemukan'}), 404
    
    sql = "SELECT * FROM produk WHERE store_id=? AND aktif=1"
    params = [store_id]
    if kategori and kategori != 'Semua':
        sql += " AND kategori=?"
        params.append(kategori)
    if cari:
        if USE_POSTGRES:
            sql += " AND nama ILIKE %s"
        else:
            sql += " AND nama LIKE ?"
        params.append(f'%{cari}%')
    sql += " ORDER BY kategori, nama LIMIT ?"
    params.append(limit)
    rows = db_execute(conn, sql, params).fetchall()
    conn.close()
    return jsonify(rows_to_list(rows))


@bp.route('/api/produk', methods=['POST'])
@pemilik_required
def tambah_produk():
    d = request.json or {}
    nama = (d.get('nama') or '').strip()
    kategori = (d.get('kategori') or 'Umum').strip() or 'Umum'
    try:
        harga = int(float(d.get('harga', 0)))
        stok = int(float(d.get('stok', 0)))
    except (ValueError, TypeError):
        return jsonify({'error': 'Harga/stok harus angka'}), 400
    if not nama:
        return jsonify({'error': 'Nama produk wajib diisi'}), 400
    if harga < 0 or stok < 0:
        return jsonify({'error': 'Harga/stok tidak boleh negatif'}), 400
    store_id = get_current_store_id()
    conn = get_db()
    cur = db_execute(conn,
        "INSERT INTO produk (nama, harga, stok, emoji, kategori, harga_modal, stok_min, diskon, barcode, store_id) VALUES (?,?,?,?,?,?,?,?,?,?)",
        (nama, harga, stok, d.get('emoji') or '[BOX]', kategori,
         d.get('harga_modal', 0) or 0, d.get('stok_min', 0) or 0, d.get('diskon', 0) or 0,
         (d.get('barcode') or '').strip(), store_id)
    )
    produk_id = cur.lastrowid
    conn.commit()
    row = db_execute(conn, "SELECT * FROM produk WHERE id=?", (produk_id,)).fetchone()
    conn.close()
    return jsonify(row_to_dict(row)), 201


@bp.route('/api/produk/<int:pid>', methods=['PUT'])
@pemilik_required
def update_produk(pid):
    d = request.json or {}
    nama = (d.get('nama') or '').strip()
    kategori = (d.get('kategori') or 'Umum').strip() or 'Umum'
    try:
        harga = int(float(d.get('harga', 0)))
        stok = int(float(d.get('stok', 0)))
    except (ValueError, TypeError):
        return jsonify({'error': 'Harga/stok harus angka'}), 400
    if not nama:
        return jsonify({'error': 'Nama produk wajib diisi'}), 400
    if harga < 0 or stok < 0:
        return jsonify({'error': 'Harga/stok tidak boleh negatif'}), 400
    store_id = get_current_store_id()
    conn = get_db()
    # Cek apakah produk milik toko ini
    existing = db_execute(conn, "SELECT 1 FROM produk WHERE id=? AND store_id=?", (pid, store_id)).fetchone()
    if not existing:
        conn.close()
        return jsonify({'error': 'Produk tidak ditemukan atau bukan milik toko ini'}), 404

    now_sql = "CURRENT_TIMESTAMP" if USE_POSTGRES else "datetime('now','localtime')"
    db_execute(conn,
        f"""UPDATE produk SET nama=?, harga=?, stok=?, emoji=?, kategori=?,
           harga_modal=?, stok_min=?, diskon=?, barcode=?,
           diubah={now_sql} WHERE id=? AND store_id=?""",
        (nama, harga, stok, d.get('emoji') or '[BOX]', kategori,
         d.get('harga_modal', 0) or 0, d.get('stok_min', 0) or 0, d.get('diskon', 0) or 0,
         (d.get('barcode') or '').strip(), pid, store_id)
    )
    conn.commit()
    row = db_execute(conn, "SELECT * FROM produk WHERE id=?", (pid,)).fetchone()
    conn.close()
    return jsonify(row_to_dict(row))


@bp.route('/api/produk/<int:pid>', methods=['DELETE'])
@pemilik_required
def hapus_produk(pid):
    store_id = get_current_store_id()
    conn = get_db()
    # Soft delete — hanya untuk toko ini
    db_execute(conn, "UPDATE produk SET aktif=0 WHERE id=? AND store_id=?", (pid, store_id))
    conn.commit()
    conn.close()
    return jsonify({'ok': True})


@bp.route('/api/produk/scan/<barcode>', methods=['GET'])
def scan_produk(barcode):
    """Scan barcode untuk mencari produk (untuk kasir)"""
    store_id = get_current_store_id()
    conn = get_db()
    row = db_execute(conn, 
        "SELECT * FROM produk WHERE barcode=? AND store_id=? AND aktif=1", (barcode, store_id)
    ).fetchone()
    conn.close()
    if row:
        return jsonify(dict(row))
    return jsonify({'error': 'Produk tidak ditemukan'}), 404


@bp.route('/api/produk/stok-rendah', methods=['GET'])
@pemilik_required
def produk_stok_rendah():
    """Produk yang stoknya di bawah atau sama dengan stok_min (jika stok_min > 0)
       atau stok <= 5 jika stok_min belum diset."""
    store_id = get_current_store_id()
    conn = get_db()
    rows = db_execute(conn, """
        SELECT * FROM produk
        WHERE aktif = 1
          AND store_id = ?
          AND (
              (stok_min > 0 AND stok <= stok_min)
              OR
              (stok_min = 0 AND stok <= 5 AND stok > 0)
          )
        ORDER BY stok ASC, nama
    """, (store_id,)).fetchall()
    conn.close()
    return jsonify(rows_to_list(rows))


@bp.route('/api/produk/kategori', methods=['GET'])
def get_kategori():
    store_id = get_current_store_id()
    conn = get_db()
    rows = db_execute(conn, "SELECT DISTINCT kategori FROM produk WHERE aktif=1 AND store_id=? ORDER BY kategori", (store_id,)).fetchall()
    conn.close()
    return jsonify([r['kategori'] for r in rows])


# ─────────────────────────────────────
#  API: TRANSAKSI
# ─────────────────────────────────────


@bp.route('/api/produk/<int:pid>/adjust-stok', methods=['POST'])
@pemilik_required
@no_ghost_write
def adjust_stok(pid):
    """Adjust stok manual dengan alasan."""
    user = get_current_user()
    d = request.json
    
    stok_baru = int(d.get('stok_baru', 0))
    alasan    = d.get('alasan', '').strip()
    keterangan = d.get('keterangan', '').strip()
    
    if stok_baru < 0:
        return jsonify({'error': 'Stok tidak boleh negatif'}), 400
    if not alasan:
        return jsonify({'error': 'Alasan adjust wajib diisi'}), 400
    
    conn = get_db()
    begin_tx(conn)

    try:
        # Get produk dan stok saat ini — hanya milik toko aktif
        store_id = get_current_store_id()
        prod = db_execute(conn, "SELECT * FROM produk WHERE id=? AND aktif=1 AND store_id=?", (pid, store_id)).fetchone()
        if not prod:
            conn.rollback()
            conn.close()
            return jsonify({'error': 'Produk tidak ditemukan'}), 404
        
        stok_sebelum = prod['stok']
        stok_sesudah = stok_baru
        selisih = stok_sesudah - stok_sebelum
        
        if selisih == 0:
            conn.rollback()
            conn.close()
            return jsonify({'error': 'Tidak ada perubahan stok'}), 400
        
        # Update stok produk — hanya milik toko aktif
        now_sql = "CURRENT_TIMESTAMP" if USE_POSTGRES else "datetime('now','localtime')"
        db_execute(conn,
            f"UPDATE produk SET stok = ?, diubah = {now_sql} WHERE id=? AND store_id=?",
            (stok_baru, pid, store_id)
        )

        # Tentukan tipe log
        tipe = 'masuk' if selisih > 0 else 'keluar'

        # Catat di stok_log (dengan store_id agar muncul di riwayat toko)
        db_execute(conn,
            """INSERT INTO stok_log
               (produk_id, tipe, jumlah, stok_sebelum, stok_sesudah,
                alasan, keterangan, dibuat_oleh, store_id)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (pid, tipe, abs(selisih), stok_sebelum, stok_sesudah,
             alasan, keterangan, user['nama'], store_id)
        )
        
        conn.commit()
        
        # Return updated produk
        row = row_to_dict(db_execute(conn, "SELECT * FROM produk WHERE id=?", (pid,)).fetchone())
        conn.close()
        
        return jsonify({'ok': True, 'produk': row})
        
    except Exception as e:
        conn.rollback()
        conn.close()
        return server_error()


@bp.route('/api/produk/<int:pid>/stok-history', methods=['GET'])
@pemilik_required
def get_stok_history(pid):
    """Ambil riwayat perubahan stok untuk produk tertentu."""
    limit = int(request.args.get('limit', 50))
    store_id = get_current_store_id()

    conn = get_db()
    rows = db_execute(conn, """
        SELECT sl.*, p.nama as produk_nama, p.emoji as produk_emoji
        FROM stok_log sl
        JOIN produk p ON p.id = sl.produk_id
        WHERE sl.produk_id = ?
          AND p.store_id = ?
        ORDER BY sl.waktu DESC
        LIMIT ?
    """, (pid, store_id, limit)).fetchall()
    conn.close()
    return jsonify(rows_to_list(rows))


# ─────────────────────────────────────
#  API: PELANGGAN
# ─────────────────────────────────────


@bp.route('/api/stok-log', methods=['GET'])
@pemilik_required
def get_stok_log():
    """Ambil riwayat perubahan stok dengan filter."""
    dari   = request.args.get('dari', '')
    ke     = request.args.get('ke', '')
    produk_id = request.args.get('produk_id', '')
    tipe   = request.args.get('tipe', '')  # masuk, keluar, adjust
    limit  = int(request.args.get('limit', 100))
    store_id = get_current_store_id()
    
    conn = get_db()
    sql = """
        SELECT sl.*, p.nama as produk_nama, p.emoji as produk_emoji
        FROM stok_log sl
        JOIN produk p ON p.id = sl.produk_id
        WHERE p.store_id = ?
    """
    params = [store_id]
    
    if dari:
        sql += " AND DATE(sl.waktu) >= ?"
        params.append(dari)
    if ke:
        sql += " AND DATE(sl.waktu) <= ?"
        params.append(ke)
    if produk_id:
        sql += " AND sl.produk_id = ?"
        params.append(int(produk_id))
    if tipe:
        sql += " AND sl.tipe = ?"
        params.append(tipe)
    
    sql += " ORDER BY sl.waktu DESC LIMIT ?"
    params.append(limit)
    
    rows = db_execute(conn, sql, params).fetchall()
    conn.close()
    return jsonify(rows_to_list(rows))


@bp.route('/api/produk/export-csv', methods=['GET'])
@pemilik_required
def export_produk_csv():
    """Export semua produk aktif ke CSV — siap diedit di Excel lalu di-import kembali."""
    store_id = get_current_store_id()
    conn = get_db()
    rows = db_execute(conn,
        "SELECT nama, kategori, harga, stok, emoji, harga_modal, stok_min, diskon, barcode FROM produk WHERE aktif=1 AND store_id=? ORDER BY kategori, nama",
        (store_id,)
    ).fetchall()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['nama', 'kategori', 'harga', 'stok', 'emoji', 'harga_modal', 'stok_min', 'diskon', 'barcode'])
    for r in rows:
        writer.writerow([r['nama'], r['kategori'], r['harga'], r['stok'], r['emoji'],
                         r['harga_modal'] or 0, r['stok_min'] or 0, r['diskon'] or 0,
                         r['barcode'] or ''])

    tanggal = datetime.now().strftime('%Y-%m-%d')
    return send_file(
        io.BytesIO(('\ufeff' + output.getvalue()).encode('utf-8-sig')),
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'produk-kasirtoko-{tanggal}.csv'
    )


@bp.route('/api/produk/import-csv', methods=['POST'])
@pemilik_required
def import_produk_csv():
    """
    Import produk dari CSV.
    Mode: 'tambah'  → hanya tambah produk baru (skip yang sudah ada berdasarkan nama)
          'timpa'   → update stok+harga produk yang sudah ada, tambah yang baru
          'ganti'   → nonaktifkan semua produk lama, masukkan semua dari CSV (fresh)
    """
    if 'file' not in request.files:
        return jsonify({'error': 'File tidak ditemukan'}), 400

    file   = request.files['file']
    mode   = request.form.get('mode', 'tambah')   # tambah | timpa | ganti

    if not (file.filename or '').lower().endswith('.csv'):
        return jsonify({'error': 'Hanya file .csv yang diterima'}), 400

    if mode not in ('tambah', 'timpa', 'ganti'):
        return jsonify({'error': 'Mode tidak valid'}), 400

    # Mode ganti menonaktifkan seluruh katalog: wajib konfirmasi eksplisit
    if mode == 'ganti' and (request.form.get('konfirmasi') or '').strip() != 'GANTI KATALOG':
        return jsonify({'error': 'Mode ganti butuh konfirmasi. Kirim konfirmasi="GANTI KATALOG".'}), 400

    # Baca isi file — coba beberapa encoding umum
    raw = file.read()
    for enc in ['utf-8-sig', 'utf-8', 'latin-1', 'cp1252']:
        try:
            content = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        return jsonify({'error': 'Encoding file tidak dikenali'}), 400

    reader  = csv.DictReader(io.StringIO(content))
    kolom_wajib = {'nama', 'kategori', 'harga', 'stok'}

    # Validasi header
    if not reader.fieldnames:
        return jsonify({'error': 'File CSV kosong atau header tidak ditemukan'}), 400

    header_lower = {k.strip().lower() for k in reader.fieldnames}
    missing = kolom_wajib - header_lower
    if missing:
        return jsonify({'error': f'Kolom wajib tidak ada: {", ".join(missing)}'}), 400

    # Normalise key (case-insensitive, strip spasi)
    def norm(row):
        return {k.strip().lower(): v.strip() for k, v in row.items()}

    rows_csv = [norm(r) for r in reader]
    if not rows_csv:
        return jsonify({'error': 'Tidak ada data di file CSV'}), 400

    # Validasi tiap baris
    errors = []
    valid  = []
    for i, r in enumerate(rows_csv, start=2):   # baris 1 = header
        nama = r.get('nama', '').strip()
        kat  = r.get('kategori', '').strip()
        if not nama:
            errors.append(f'Baris {i}: kolom "nama" kosong')
            continue
        if not kat:
            errors.append(f'Baris {i}: kolom "kategori" kosong')
            continue
        try:
            harga      = int(float(r.get('harga', 0)))
            stok       = int(float(r.get('stok',  0)))
            harga_modal= int(float(r.get('harga_modal', 0) or 0))
            stok_min   = int(float(r.get('stok_min', 0) or 0))
            diskon     = int(float(r.get('diskon', 0) or 0))
        except ValueError:
            errors.append(f'Baris {i} ({nama}): harga/stok harus angka')
            continue
        if harga < 0:
            errors.append(f'Baris {i} ({nama}): harga tidak boleh negatif')
            continue
        diskon = max(0, min(100, diskon))
        emoji  = r.get('emoji', '[BOX]').strip() or '[BOX]'
        barcode = (r.get('barcode', '') or '').strip()
        valid.append({'nama': nama, 'kategori': kat, 'harga': harga, 'stok': stok, 'emoji': emoji,
                      'harga_modal': harga_modal, 'stok_min': stok_min, 'diskon': diskon,
                      'barcode': barcode})

    if not valid:
        return jsonify({'error': 'Semua baris tidak valid', 'detail': errors}), 400

    conn = get_db()
    store_id = get_current_store_id()
    tambah = 0
    update = 0
    skip   = 0
    now_sql = "CURRENT_TIMESTAMP" if USE_POSTGRES else "datetime('now','localtime')"

    try:
        if mode == 'ganti':
            # Backup katalog aktif ke folder backups sebelum dinonaktifkan
            try:
                backup_dir = BACKUP_DIR
                os.makedirs(backup_dir, exist_ok=True)
                snap = db_execute(conn,
                    "SELECT nama, kategori, harga, stok, emoji, harga_modal, stok_min, diskon, barcode FROM produk WHERE aktif=1 AND store_id=?",
                    (store_id,)
                ).fetchall()
                if snap:
                    import csv as _csv
                    ts = datetime.now().strftime('%Y%m%d%H%M%S')
                    with open(os.path.join(backup_dir, f'produk-store{store_id}-{ts}.csv'),
                              'w', newline='', encoding='utf-8-sig') as fh:
                        w = _csv.writer(fh)
                        w.writerow(['nama', 'kategori', 'harga', 'stok', 'emoji', 'harga_modal', 'stok_min', 'diskon', 'barcode'])
                        for r in snap:
                            w.writerow([r['nama'], r['kategori'], r['harga'], r['stok'], r['emoji'],
                                        r['harga_modal'] or 0, r['stok_min'] or 0, r['diskon'] or 0, r['barcode'] or ''])
            except Exception as be:
                print(f"[WARN] Backup katalog gagal: {be}")
            # Nonaktifkan semua produk lama di toko ini
            db_execute(conn, "UPDATE produk SET aktif=0 WHERE store_id=?", (store_id,))

        for p in valid:
            # Barcode harus unik per toko (jika diisi)
            if p['barcode']:
                pemilik_barcode = db_execute(conn,
                    "SELECT id FROM produk WHERE barcode=? AND store_id=? AND aktif=1",
                    (p['barcode'], store_id)
                ).fetchone()
                if pemilik_barcode:
                    # Boleh jika barcode milik produk yang sama (berdasarkan nama)
                    same = db_execute(conn,
                        "SELECT id FROM produk WHERE LOWER(nama)=LOWER(?) AND store_id=?",
                        (p['nama'], store_id)
                    ).fetchone()
                    if not same or same['id'] != pemilik_barcode['id']:
                        errors.append(f'Baris ({p["nama"]}): barcode "{p["barcode"]}" sudah dipakai produk lain')
                        continue

            existing = db_execute(conn,
                "SELECT id FROM produk WHERE LOWER(nama)=LOWER(?) AND aktif=1 AND store_id=?",
                (p['nama'], store_id)
            ).fetchone()

            if existing:
                if mode == 'timpa':
                    db_execute(conn,
                        f"UPDATE produk SET harga=?, stok=?, emoji=?, kategori=?, harga_modal=?, stok_min=?, diskon=?, barcode=?, diubah={now_sql} WHERE id=?",
                        (p['harga'], p['stok'], p['emoji'], p['kategori'],
                         p['harga_modal'], p['stok_min'], p['diskon'], p['barcode'], existing['id'])
                    )
                    update += 1
                elif mode == 'ganti':
                    # Reaktifkan dan update
                    db_execute(conn,
                        f"UPDATE produk SET harga=?, stok=?, emoji=?, kategori=?, harga_modal=?, stok_min=?, diskon=?, barcode=?, aktif=1, diubah={now_sql} WHERE id=?",
                        (p['harga'], p['stok'], p['emoji'], p['kategori'],
                         p['harga_modal'], p['stok_min'], p['diskon'], p['barcode'], existing['id'])
                    )
                    update += 1
                else:
                    # mode tambah → skip yang sudah ada
                    skip += 1
            else:
                # Cek apakah ada produk nonaktif dengan nama sama → reaktifkan
                deleted = db_execute(conn,
                    "SELECT id FROM produk WHERE LOWER(nama)=LOWER(?) AND aktif=0 AND store_id=?",
                    (p['nama'], store_id)
                ).fetchone()
                if deleted:
                    db_execute(conn,
                        f"UPDATE produk SET harga=?, stok=?, emoji=?, kategori=?, harga_modal=?, stok_min=?, diskon=?, barcode=?, aktif=1, diubah={now_sql} WHERE id=?",
                        (p['harga'], p['stok'], p['emoji'], p['kategori'],
                         p['harga_modal'], p['stok_min'], p['diskon'], p['barcode'], deleted['id'])
                    )
                else:
                    db_execute(conn,
                        "INSERT INTO produk (nama, harga, stok, emoji, kategori, harga_modal, stok_min, diskon, barcode, store_id) VALUES (?,?,?,?,?,?,?,?,?,?)",
                        (p['nama'], p['harga'], p['stok'], p['emoji'], p['kategori'],
                         p['harga_modal'], p['stok_min'], p['diskon'], p['barcode'], store_id)
                    )
                tambah += 1

        conn.commit()
    except Exception as e:
        conn.rollback()
        conn.close()
        return server_error('Gagal menyimpan data')

    conn.close()
    return jsonify({
        'ok': True,
        'mode': mode,
        'tambah': tambah,
        'update': update,
        'skip': skip,
        'error_baris': errors,
        'total_valid': len(valid)
    })


@bp.route('/api/produk/template-csv', methods=['GET'])
@pemilik_required
def template_produk_csv():
    """Download template CSV kosong dengan contoh baris."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['nama', 'kategori', 'harga', 'stok', 'emoji', 'harga_modal', 'stok_min', 'diskon'])
    # Contoh baris
    contoh = [
        ['Indomie Goreng',    'Makanan',    3500,  100, '🍜', 2500,  10, 0],
        ['Aqua 600ml',        'Minuman',    4000,   50, '💧', 2800,   5, 0],
        ['Gula 1kg',          'Sembako',   14000,   25, '🍬', 11000,  5, 0],
        ['Sabun Lifebuoy',    'Kebersihan', 5000,   30, '🧼', 3500,   5, 0],
        ['Gudang Garam 12',   'Rokok',     22000,   20, '🚬', 18000,  5, 0],
    ]
    for c in contoh:
        writer.writerow(c)

    return send_file(
        io.BytesIO(('\ufeff' + output.getvalue()).encode('utf-8-sig')),
        mimetype='text/csv',
        as_attachment=True,
        download_name='template-produk-kasirtoko.csv'
    )


# ─────────────────────────────────────
#  API: PENGGUNA (manajemen akun)
# ─────────────────────────────────────

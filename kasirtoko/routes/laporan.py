"""Modul routes/laporan.py — pindahan murni dari app.py (split Fase 2)."""

from flask import Blueprint
from flask import request, jsonify, send_file
from datetime import datetime, timedelta
import csv
import io
from ..db import get_db, db_execute, row_to_dict, rows_to_list, begin_tx
from ..auth import get_current_user, pemilik_required, no_ghost_write, get_current_store_id
from ..config import USE_POSTGRES

bp = Blueprint('laporan', __name__)


@bp.route('/api/laporan/produk-terjual', methods=['GET'])
@pemilik_required
def get_produk_terjual():
    """Aggregasi produk terjual per periode (harian/mingguan/bulanan)."""
    dari = request.args.get('dari', '')
    ke   = request.args.get('ke', '')
    
    if not dari or not ke:
        return jsonify({'error': 'Parameter dari dan ke wajib diisi'}), 400

    store_id = get_current_store_id()
    conn = get_db()

    # Query aggregasi produk terjual - semua transaksi aktif (termasuk piutang,
    # karena barang sudah keluar). Sama definisinya dengan laporan_top_produk.
    sql = """
        SELECT
            p.id,
            p.nama,
            p.emoji,
            p.kategori,
            COALESCE(SUM(ti.qty), 0) as total_terjual,
            COALESCE(SUM(ti.subtotal), 0) as total_omzet,
            COUNT(DISTINCT ti.transaksi_id) as jumlah_transaksi
        FROM produk p
        JOIN transaksi_item ti ON ti.produk_id = p.id
        JOIN transaksi t ON t.id = ti.transaksi_id
        WHERE DATE(t.waktu) >= ?
          AND DATE(t.waktu) <= ?
          AND COALESCE(t.status, 'aktif') = 'aktif'
          AND t.store_id = ?
          AND p.store_id = ?
        GROUP BY p.id, p.nama, p.emoji, p.kategori
        HAVING total_terjual > 0
        ORDER BY total_terjual DESC
    """

    rows = rows_to_list(db_execute(conn, sql, (dari, ke, store_id, store_id)).fetchall())

    # Hitung total keseluruhan
    total_stat = db_execute(conn, """
        SELECT
            COALESCE(SUM(ti.qty), 0) as total_qty,
            COALESCE(SUM(ti.subtotal), 0) as total_omzet
        FROM transaksi_item ti
        JOIN transaksi t ON t.id = ti.transaksi_id
        WHERE DATE(t.waktu) >= ?
          AND DATE(t.waktu) <= ?
          AND COALESCE(t.status, 'aktif') = 'aktif'
          AND t.store_id = ?
    """, (dari, ke, store_id)).fetchone()
    
    conn.close()
    
    return jsonify({
        'rows': rows,
        'total_qty': total_stat['total_qty'] if total_stat else 0,
        'total_omzet': total_stat['total_omzet'] if total_stat else 0
    })


# ─────────────────────────────────────
#  API: TUTUP KASIR
# ─────────────────────────────────────


@bp.route('/api/laporan/top-produk', methods=['GET'])
@pemilik_required
def laporan_top_produk():
    dari  = request.args.get('dari', '')
    ke    = request.args.get('ke', '')
    limit = int(request.args.get('limit', 10))
    store_id = get_current_store_id()

    conn       = get_db()
    # Filter: hanya transaksi aktif (exclude void)
    sql_filter = "WHERE COALESCE(t.status, 'aktif') = 'aktif' AND t.store_id = ?"
    params     = [store_id]
    if dari:
        sql_filter += " AND DATE(t.waktu) >= ?"
        params.append(dari)
    if ke:
        sql_filter += " AND DATE(t.waktu) <= ?"
        params.append(ke)

    top = db_execute(conn, f"""
        SELECT ti.produk_id, ti.nama_produk AS nama, ti.emoji,
               SUM(ti.qty)      AS total_qty,
               SUM(ti.subtotal) AS total_nilai,
               COALESCE(p.harga_modal, 0) AS harga_modal
        FROM transaksi_item ti
        JOIN transaksi t ON t.id = ti.transaksi_id
        LEFT JOIN produk p ON p.id = ti.produk_id
        {sql_filter}
        GROUP BY ti.produk_id, ti.nama_produk
        ORDER BY total_qty DESC
        LIMIT ?
    """, params + [limit]).fetchall()
    conn.close()
    return jsonify(rows_to_list(top))


# ═════════════════════════════════════
#  API: VOID / CANCEL TRANSAKSI
# ═════════════════════════════════════


@bp.route('/api/laporan/hari-ini', methods=['GET'])
@pemilik_required
def laporan_hari_ini():
    store_id = get_current_store_id()
    conn = get_db()
    stats = db_execute(conn, """
        SELECT
            COUNT(*)        AS total_transaksi,
            COALESCE(SUM(total),0)     AS omzet,
            COALESCE(SUM(diskon),0)    AS total_diskon,
            COALESCE(AVG(total),0)     AS rata_rata
        FROM transaksi
        WHERE DATE(waktu) = DATE('now','localtime')
          AND COALESCE(status, 'aktif') = 'aktif'
          AND store_id = ?
    """, (store_id,)).fetchone()

    top_produk = db_execute(conn, """
        SELECT ti.nama_produk AS nama, ti.emoji,
               SUM(ti.qty) AS total_qty,
               SUM(ti.subtotal) AS total_nilai
        FROM transaksi_item ti
        JOIN transaksi t ON t.id = ti.transaksi_id
        WHERE DATE(t.waktu) = DATE('now','localtime')
          AND COALESCE(t.status, 'aktif') = 'aktif'
          AND t.store_id = ?
        GROUP BY ti.produk_id, ti.nama_produk
        ORDER BY total_nilai DESC
        LIMIT 5
    """, (store_id,)).fetchall()

    conn.close()
    return jsonify({
        'stats': row_to_dict(stats),
        'top_produk': rows_to_list(top_produk)
    })


@bp.route('/api/laporan/rentang', methods=['GET'])
@pemilik_required
def laporan_rentang():
    dari = request.args.get('dari', '')
    ke   = request.args.get('ke', '')
    store_id = get_current_store_id()
    conn = get_db()

    # Filter: hanya transaksi aktif (exclude void) milik toko ini
    sql_filter = "WHERE COALESCE(status, 'aktif') = 'aktif' AND store_id = ?"
    params = [store_id]
    if dari:
        sql_filter += " AND DATE(waktu) >= ?"
        params.append(dari)
    if ke:
        sql_filter += " AND DATE(waktu) <= ?"
        params.append(ke)

    stats = db_execute(conn, f"""
        SELECT COUNT(*) AS total_transaksi,
               COALESCE(SUM(total),0) AS omzet,
               COALESCE(SUM(diskon),0) AS total_diskon,
               COALESCE(AVG(total),0) AS rata_rata
        FROM transaksi {sql_filter}
    """, params).fetchone()

    harian = db_execute(conn, f"""
        SELECT DATE(waktu) AS tanggal,
               COUNT(*) AS transaksi,
               SUM(total) AS omzet
        FROM transaksi {sql_filter}
        GROUP BY DATE(waktu)
        ORDER BY tanggal DESC
    """, params).fetchall()

    conn.close()
    return jsonify({
        'stats': row_to_dict(stats),
        'harian': rows_to_list(harian)
    })


# ═════════════════════════════════════
#  API: GRAFIK / CHART DATA
# ═════════════════════════════════════


@bp.route('/api/laporan/chart', methods=['GET'])
@pemilik_required
def laporan_chart():
    """Data untuk grafik penjualan (harian/mingguan/bulanan)."""
    tipe = request.args.get('tipe', 'harian')  # harian, mingguan, bulanan
    dari = request.args.get('dari', '')
    ke   = request.args.get('ke', '')
    store_id = get_current_store_id()

    conn = get_db()

    if tipe == 'harian':
        # Default: 30 hari terakhir jika tidak ada filter
        if not dari:
            dari = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        if not ke:
            ke = datetime.now().strftime('%Y-%m-%d')

        rows = db_execute(conn, """
            SELECT
                DATE(waktu) as label,
                COUNT(*) as transaksi,
                COALESCE(SUM(total), 0) as omzet,
                COALESCE(SUM(diskon), 0) as diskon
            FROM transaksi
            WHERE DATE(waktu) >= ? AND DATE(waktu) <= ?
              AND COALESCE(status, 'aktif') = 'aktif'
              AND store_id = ?
            GROUP BY DATE(waktu)
            ORDER BY DATE(waktu) ASC
        """, (dari, ke, store_id)).fetchall()
            
    elif tipe == 'mingguan':
        # Default: 12 minggu terakhir
        if not dari:
            dari = (datetime.now() - timedelta(weeks=12)).strftime('%Y-%m-%d')
        if not ke:
            ke = datetime.now().strftime('%Y-%m-%d')
            
        if USE_POSTGRES:
            rows = db_execute(conn, """
                SELECT
                    DATE_TRUNC('week', waktu)::date || ' - ' ||
                    (DATE_TRUNC('week', waktu) + interval '6 days')::date as label,
                    EXTRACT(WEEK FROM waktu) as week_num,
                    COUNT(*) as transaksi,
                    COALESCE(SUM(total), 0) as omzet,
                    COALESCE(SUM(diskon), 0) as diskon
                FROM transaksi
                WHERE DATE(waktu) >= ? AND DATE(waktu) <= ?
                  AND COALESCE(status, 'aktif') = 'aktif'
                  AND store_id = ?
                GROUP BY DATE_TRUNC('week', waktu), EXTRACT(WEEK FROM waktu)
                ORDER BY DATE_TRUNC('week', waktu) ASC
            """, (dari, ke, store_id)).fetchall()
        else:
            rows = db_execute(conn, """
                SELECT
                    strftime('%W', waktu) as week_num,
                    'Minggu ' || strftime('%W', waktu) as label,
                    COUNT(*) as transaksi,
                    COALESCE(SUM(total), 0) as omzet,
                    COALESCE(SUM(diskon), 0) as diskon
                FROM transaksi
                WHERE DATE(waktu) >= ? AND DATE(waktu) <= ?
                  AND COALESCE(status, 'aktif') = 'aktif'
                  AND store_id = ?
                GROUP BY strftime('%W', waktu)
                ORDER BY strftime('%W', waktu) ASC
            """, (dari, ke, store_id)).fetchall()
            
    elif tipe == 'bulanan':
        # Default: 12 bulan terakhir
        if not dari:
            dari = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
        if not ke:
            ke = datetime.now().strftime('%Y-%m-%d')

        if USE_POSTGRES:
            rows = db_execute(conn, """
                SELECT
                    TO_CHAR(waktu, 'YYYY-MM') as label,
                    TO_CHAR(waktu, 'MM/YYYY') as bulan,
                    COUNT(*) as transaksi,
                    COALESCE(SUM(total), 0) as omzet,
                    COALESCE(SUM(diskon), 0) as diskon
                FROM transaksi
                WHERE DATE(waktu) >= ? AND DATE(waktu) <= ?
                  AND COALESCE(status, 'aktif') = 'aktif'
                  AND store_id = ?
                GROUP BY TO_CHAR(waktu, 'YYYY-MM'), TO_CHAR(waktu, 'MM/YYYY')
                ORDER BY TO_CHAR(waktu, 'YYYY-MM') ASC
            """, (dari, ke, store_id)).fetchall()
        else:
            rows = db_execute(conn, """
                SELECT
                    strftime('%Y-%m', waktu) as label,
                    strftime('%m/%Y', waktu) as bulan,
                    COUNT(*) as transaksi,
                    COALESCE(SUM(total), 0) as omzet,
                    COALESCE(SUM(diskon), 0) as diskon
                FROM transaksi
                WHERE DATE(waktu) >= ? AND DATE(waktu) <= ?
                  AND COALESCE(status, 'aktif') = 'aktif'
                  AND store_id = ?
                GROUP BY strftime('%Y-%m', waktu)
                ORDER BY strftime('%Y-%m', waktu) ASC
            """, (dari, ke, store_id)).fetchall()
    else:
        conn.close()
        return jsonify({'error': 'Tipe tidak valid'}), 400
    
    # Format data untuk Chart.js
    labels = [r['label'] for r in rows]
    data_transaksi = [r['transaksi'] for r in rows]
    data_omzet = [r['omzet'] for r in rows]
    data_diskon = [r['diskon'] for r in rows]
    
    conn.close()
    return jsonify({
        'tipe': tipe,
        'labels': labels,
        'datasets': {
            'transaksi': data_transaksi,
            'omzet': data_omzet,
            'diskon': data_diskon
        }
    })


# ═════════════════════════════════════
#  API: LAPORAN STOK
# ═════════════════════════════════════


@bp.route('/api/laporan/stok', methods=['GET'])
@pemilik_required
def laporan_stok():
    """Laporan stok: hampir habis, opname, dan statistik."""
    mode = request.args.get('mode', 'semua')  # semua, hampir_habis, opname
    store_id = get_current_store_id()
    
    conn = get_db()
    
    # Base query dengan store_id filter - FIX Bug #11: hapus OR IS NULL
    base_where = "WHERE p.store_id = ? AND p.aktif = 1"
    params = [store_id]
    
    if mode == 'hampir_habis':
        # Stok <= stok_min atau stok <= 5 jika stok_min = 0
        sql = f"""
            SELECT p.*, 
                   COALESCE(SUM(CASE WHEN sl.tipe = 'masuk' THEN sl.jumlah ELSE 0 END), 0) as total_masuk,
                   COALESCE(SUM(CASE WHEN sl.tipe = 'keluar' THEN sl.jumlah ELSE 0 END), 0) as total_keluar
            FROM produk p
            LEFT JOIN stok_log sl ON sl.produk_id = p.id
            {base_where}
              AND (p.stok <= p.stok_min OR (p.stok_min = 0 AND p.stok <= 5))
            GROUP BY p.id
            ORDER BY p.stok ASC
        """
    elif mode == 'opname':
        # Semua produk untuk stok opname
        sql = f"""
            SELECT p.*,
                   COALESCE(SUM(CASE WHEN sl.tipe = 'masuk' THEN sl.jumlah ELSE 0 END), 0) as total_masuk,
                   COALESCE(SUM(CASE WHEN sl.tipe = 'keluar' THEN sl.jumlah ELSE 0 END), 0) as total_keluar,
                   COUNT(DISTINCT sl.id) as total_perubahan
            FROM produk p
            LEFT JOIN stok_log sl ON sl.produk_id = p.id
            {base_where}
            GROUP BY p.id
            ORDER BY p.kategori, p.nama
        """
    else:
        # Semua produk aktif
        sql = f"""
            SELECT p.*,
                   COALESCE(SUM(CASE WHEN sl.tipe = 'masuk' THEN sl.jumlah ELSE 0 END), 0) as total_masuk,
                   COALESCE(SUM(CASE WHEN sl.tipe = 'keluar' THEN sl.jumlah ELSE 0 END), 0) as total_keluar
            FROM produk p
            LEFT JOIN stok_log sl ON sl.produk_id = p.id
            {base_where}
            GROUP BY p.id
            ORDER BY p.kategori, p.nama
        """
    
    rows = db_execute(conn, sql, tuple(params)).fetchall()
    
    # Stats - dihitung via SQL untuk performance
    stats_sql = f"""
        SELECT 
            COUNT(*) as total_produk,
            SUM(CASE WHEN p.stok <= p.stok_min OR (p.stok_min = 0 AND p.stok <= 5) THEN 1 ELSE 0 END) as hampir_habis,
            SUM(CASE WHEN p.stok = 0 THEN 1 ELSE 0 END) as stok_nol,
            SUM(p.stok * p.harga_modal) as total_nilai
        FROM produk p
        {base_where}
    """
    stats = db_execute(conn, stats_sql, tuple(params)).fetchone()
    total_produk = stats['total_produk'] if stats else 0
    hampir_habis = stats['hampir_habis'] if stats else 0
    stok_nol = stats['stok_nol'] if stats else 0
    total_nilai = stats['total_nilai'] if stats else 0
    
    conn.close()
    
    return jsonify({
        'mode': mode,
        'stats': {
            'total_produk': total_produk,
            'hampir_habis': hampir_habis,
            'stok_nol': stok_nol,
            'total_nilai_stok': total_nilai
        },
        'produk': [row_to_dict(r) for r in rows]
    })


# ═════════════════════════════════════
#  API: LAPORAN KEUANGAN
# ═════════════════════════════════════


@bp.route('/api/laporan/keuangan', methods=['GET'])
@pemilik_required
def laporan_keuangan():
    """Laporan keuangan: arus kas, laba/rugi."""
    dari = request.args.get('dari', '')
    ke   = request.args.get('ke', '')
    store_id = get_current_store_id()
    
    if not dari:
        dari = datetime.now().strftime('%Y-%m-%d')
    if not ke:
        ke = datetime.now().strftime('%Y-%m-%d')
    
    conn = get_db()
    
    # Arus Kas dari tabel kas
    kas_masuk = db_execute(conn, """
        SELECT COALESCE(SUM(jumlah), 0) as total, COUNT(*) as count
        FROM kas
        WHERE tipe = 'pemasukan'
          AND DATE(waktu) >= ? AND DATE(waktu) <= ?
          AND (store_id = ? OR ? IS NULL)
    """, (dari, ke, store_id, store_id)).fetchone()
    
    kas_keluar = db_execute(conn, """
        SELECT COALESCE(SUM(jumlah), 0) as total, COUNT(*) as count
        FROM kas
        WHERE tipe = 'pengeluaran'
          AND DATE(waktu) >= ? AND DATE(waktu) <= ?
          AND (store_id = ? OR ? IS NULL)
    """, (dari, ke, store_id, store_id)).fetchone()
    
    # Pemasukan dari transaksi (penjualan)
    penjualan = db_execute(conn, """
        SELECT 
            COALESCE(SUM(total), 0) as total,
            COALESCE(SUM(diskon), 0) as diskon,
            COUNT(*) as count
        FROM transaksi
        WHERE DATE(waktu) >= ? AND DATE(waktu) <= ?
          AND COALESCE(status, 'aktif') = 'aktif'
          AND (store_id = ? OR ? IS NULL)
    """, (dari, ke, store_id, store_id)).fetchone()
    
    # Laba/Rugi (Omzet - Modal)
    # Hitung laba kotor dari transaksi_item
    laba = db_execute(conn, """
        SELECT COALESCE(SUM(
            (ti.harga - COALESCE(p.harga_modal, 0)) * ti.qty
        ), 0) as laba_kotor
        FROM transaksi_item ti
        JOIN transaksi t ON t.id = ti.transaksi_id
        LEFT JOIN produk p ON p.id = ti.produk_id
        WHERE DATE(t.waktu) >= ? AND DATE(t.waktu) <= ?
          AND COALESCE(t.status, 'aktif') = 'aktif'
          AND (t.store_id = ? OR ? IS NULL)
    """, (dari, ke, store_id, store_id)).fetchone()
    
    # Metode pembayaran breakdown
    metode = db_execute(conn, """
        SELECT metode_bayar, COALESCE(SUM(total), 0) as total, COUNT(*) as count
        FROM transaksi
        WHERE DATE(waktu) >= ? AND DATE(waktu) <= ?
          AND COALESCE(status, 'aktif') = 'aktif'
          AND (store_id = ? OR ? IS NULL)
        GROUP BY metode_bayar
    """, (dari, ke, store_id, store_id)).fetchall()
    
    # Harian breakdown
    harian = db_execute(conn, """
        SELECT 
            DATE(waktu) as tanggal,
            COALESCE(SUM(total), 0) as omzet,
            COALESCE(SUM(diskon), 0) as diskon,
            COUNT(*) as transaksi
        FROM transaksi
        WHERE DATE(waktu) >= ? AND DATE(waktu) <= ?
          AND COALESCE(status, 'aktif') = 'aktif'
          AND (store_id = ? OR ? IS NULL)
        GROUP BY DATE(waktu)
        ORDER BY DATE(waktu) ASC
    """, (dari, ke, store_id, store_id)).fetchall()
    
    conn.close()
    
    return jsonify({
        'periode': {'dari': dari, 'ke': ke},
        'arus_kas': {
            'pemasukan': {'total': kas_masuk['total'], 'count': kas_masuk['count']},
            'pengeluaran': {'total': kas_keluar['total'], 'count': kas_keluar['count']},
            'saldo': kas_masuk['total'] - kas_keluar['total']
        },
        'penjualan': {
            'omzet': penjualan['total'],
            'diskon': penjualan['diskon'],
            'net': penjualan['total'] - penjualan['diskon'],
            'transaksi': penjualan['count']
        },
        'laba_rugi': {
            'laba_kotor': laba['laba_kotor'],
            'estimasi_net': laba['laba_kotor'] - kas_keluar['total']
        },
        'metode_pembayaran': [row_to_dict(m) for m in metode],
        'harian': [row_to_dict(h) for h in harian]
    })


# ─────────────────────────────────────
#  API: EXPORT PDF LAPORAN
# ─────────────────────────────────────


@bp.route('/api/export/pdf', methods=['GET'])
@pemilik_required
def export_pdf():
    """Export laporan transaksi ke PDF."""
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
    except ImportError:
        return jsonify({'error': 'Library reportlab tidak tersedia'}), 500
    
    dari = request.args.get('dari', '')
    ke   = request.args.get('ke', '')
    store_id = get_current_store_id()

    conn = get_db()

    # Get transaksi data — hanya milik toko aktif
    sql = """
        SELECT t.*, COALESCE(p.nama, '') AS pelanggan_nama
        FROM transaksi t
        LEFT JOIN pelanggan p ON p.id = t.pelanggan_id
        WHERE COALESCE(t.status, 'aktif') = 'aktif'
          AND t.store_id = ?
    """
    params = [store_id]
    if dari:
        sql += " AND DATE(t.waktu) >= ?"
        params.append(dari)
    if ke:
        sql += " AND DATE(t.waktu) <= ?"
        params.append(ke)
    sql += " ORDER BY t.waktu DESC LIMIT 500"

    transaksi = db_execute(conn, sql, params).fetchall()

    # Get summary stats — hanya milik toko aktif
    stats = db_execute(conn, f"""
        SELECT
            COUNT(*) as total_transaksi,
            COALESCE(SUM(total), 0) as total_omzet,
            COALESCE(SUM(diskon), 0) as total_diskon,
            COALESCE(AVG(total), 0) as rata_rata
        FROM transaksi
        WHERE COALESCE(status, 'aktif') = 'aktif'
          AND store_id = ?
        {' AND DATE(waktu) >= ?' if dari else ''}
        {' AND DATE(waktu) <= ?' if ke else ''}
    """, [store_id] + [p for p in [dari, ke] if p]).fetchone()

    # Hitung jumlah item per transaksi sekaligus (1 query, hindari N+1)
    trx_ids = [t['id'] for t in transaksi]
    item_count_map = {}
    if trx_ids:
        placeholders = ",".join(["?"] * len(trx_ids))
        for r in db_execute(conn,
            f"SELECT transaksi_id, COUNT(*) as c FROM transaksi_item WHERE transaksi_id IN ({placeholders}) GROUP BY transaksi_id",
            trx_ids
        ).fetchall():
            item_count_map[r['transaksi_id']] = r['c']
    
    # Create PDF
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=1.5*cm,
        leftMargin=1.5*cm,
        topMargin=1.5*cm,
        bottomMargin=1.5*cm
    )
    
    elements = []
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#f5a623'),
        spaceAfter=20,
        alignment=1  # Center
    )
    
    # Title
    periode = f"Periode: {dari or 'Awal'} s/d {ke or 'Sekarang'}"
    elements.append(Paragraph("LAPORAN PENJUALAN", title_style))
    elements.append(Paragraph(periode, styles['Normal']))
    elements.append(Spacer(1, 20))
    
    # Summary table
    summary_data = [
        ['Ringkasan', ''],
        ['Total Transaksi', str(stats['total_transaksi'])],
        ['Total Omzet', f"Rp {stats['total_omzet']:,.0f}".replace(',', '.')],
        ['Total Diskon', f"Rp {stats['total_diskon']:,.0f}".replace(',', '.')],
        ['Rata-rata per Transaksi', f"Rp {stats['rata_rata']:,.0f}".replace(',', '.')]
    ]
    
    summary_table = Table(summary_data, colWidths=[doc.width/2]*2)
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f5a623')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#1a1d27')),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.white),
        ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#2e3244')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 30))
    
    # Transaksi detail (render semua yang di-fetch, maks 500 baris)
    if transaksi:
        elements.append(Paragraph("Detail Transaksi", styles['Heading2']))
        elements.append(Spacer(1, 10))
        elements.append(Paragraph(f"Menampilkan {len(transaksi)} transaksi (maksimal 500).", styles['Normal']))
        elements.append(Spacer(1, 10))

        detail_data = [['No', 'Waktu', 'No. Trx', 'Pelanggan', 'Item', 'Total', 'Metode']]
        for i, t in enumerate(transaksi, 1):
            item_count = item_count_map.get(t['id'], 0)
            detail_data.append([
                str(i),
                t['waktu'][:16],
                t['no_trx'],
                t['pelanggan_nama'] or '-',
                f"{item_count} item",
                f"Rp {t['total']:,.0f}".replace(',', '.'),
                t.get('metode_bayar', 'tunai').upper()
            ])

        # Build detail table setelah loop selesai dan data terkumpul
        detail_table = Table(detail_data, colWidths=[0.6*cm, 2.8*cm, 2.5*cm, 2.5*cm, 1.5*cm, 2.2*cm, 1.5*cm])
        detail_table = Table(detail_data, colWidths=[0.6*cm, 2.8*cm, 2.5*cm, 2.5*cm, 1.5*cm, 2.2*cm, 1.5*cm])
        detail_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2e3244')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#f5a623')),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#1a1d27')),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.white),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#2e3244')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 5),
            ('RIGHTPADDING', (0, 0), (-1, -1), 5),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#1a1d27'), colors.HexColor('#242736')])
        ]))
        elements.append(detail_table)
    
    # Footer
    elements.append(Spacer(1, 30))
    footer_text = f"Dibuat pada: {datetime.now().strftime('%d %B %Y %H:%M')} oleh {get_current_user()['nama']}"
    elements.append(Paragraph(footer_text, styles['Normal']))
    
    # Tutup koneksi database setelah semua data diambil
    conn.close()
    
    doc.build(elements)
    buffer.seek(0)
    
    filename = f"laporan-penjualan-{dari or 'semua'}-{ke or 'semua'}.pdf"
    return send_file(
        buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=filename
    )


# ─────────────────────────────────────
#  API: EXPORT CSV
# ─────────────────────────────────────


@bp.route('/api/export/csv', methods=['GET'])
@pemilik_required
def export_csv():
    dari = request.args.get('dari', '')
    ke   = request.args.get('ke', '')
    store_id = get_current_store_id()

    conn = get_db()
    sql = """
        SELECT t.no_trx, t.waktu, ti.nama_produk, ti.emoji,
               ti.qty, ti.harga, ti.subtotal,
               t.diskon, t.total, t.bayar, t.kembalian
        FROM transaksi_item ti
        JOIN transaksi t ON t.id = ti.transaksi_id
        WHERE t.store_id = ?
    """
    params = [store_id]
    if dari:
        sql += " AND DATE(t.waktu) >= ?"
        params.append(dari)
    if ke:
        sql += " AND DATE(t.waktu) <= ?"
        params.append(ke)
    sql += " ORDER BY t.waktu DESC"

    rows = db_execute(conn, sql, params).fetchall()
    conn.close()

    output = io.StringIO()
    output.write('\ufeff')  # BOM untuk Excel
    writer = csv.writer(output)
    writer.writerow(['No Transaksi','Waktu','Produk','Qty',
                     'Harga Satuan','Subtotal Item','Diskon Trx',
                     'Total','Bayar','Kembalian'])
    for r in rows:
        writer.writerow([r['no_trx'], r['waktu'], r['nama_produk'],
                         r['qty'], r['harga'], r['subtotal'],
                         r['diskon'], r['total'], r['bayar'], r['kembalian']])

    output.seek(0)
    tanggal = datetime.now().strftime('%Y-%m-%d')
    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8-sig')),
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'laporan-kasir-{tanggal}.csv'
    )


# ─────────────────────────────────────
#  API: EXPORT / IMPORT PRODUK CSV
# ─────────────────────────────────────

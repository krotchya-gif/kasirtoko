"""Modul routes/struk.py — pindahan murni dari app.py (split Fase 2)."""

from flask import Blueprint
from flask import request, jsonify, send_file
from datetime import datetime
import json
import io
import traceback
from ..db import get_db, db_execute, server_error
from ..auth import pemilik_required, get_current_store_id
from ..config import USE_POSTGRES

bp = Blueprint('struk', __name__)


@bp.route('/api/struk/<int:tid>/image', methods=['GET'])
def generate_struk_image(tid):
    """Generate struk transaksi sebagai gambar PNG untuk share."""
    try:
        from PIL import Image, ImageDraw, ImageFont
        import textwrap
    except ImportError:
        return jsonify({'error': 'Library PIL tidak tersedia'}), 500
    
    conn = get_db()
    store_id = get_current_store_id()

    # Get transaksi — hanya milik toko aktif
    trx = db_execute(conn, """
        SELECT t.*, COALESCE(p.nama, '') AS pelanggan_nama
        FROM transaksi t
        LEFT JOIN pelanggan p ON p.id = t.pelanggan_id
        WHERE t.id = ? AND t.store_id = ?
    """, (tid, store_id)).fetchone()
    
    if not trx:
        conn.close()
        return jsonify({'error': 'Transaksi tidak ditemukan'}), 404
    
    # Get items
    items = db_execute(conn, 
        "SELECT * FROM transaksi_item WHERE transaksi_id=?", (tid,)
    ).fetchall()
    
    # Get pengaturan toko - filter by store_id dari transaksi
    trx_store_id = trx.get('store_id') or 0
    if USE_POSTGRES:
        pengaturan_rows = db_execute(conn, 
            """SELECT kunci, nilai FROM pengaturan WHERE store_id = %s OR store_id IS NULL 
               ORDER BY store_id NULLS LAST""", (trx_store_id,)
        ).fetchall()
    else:
        # SQLite: gunakan UNION untuk mendapatkan store-specific + global fallback
        pengaturan_rows = db_execute(conn, 
            """SELECT kunci, nilai FROM pengaturan WHERE store_id = ?
               UNION ALL
               SELECT kunci, nilai FROM pengaturan 
               WHERE store_id = 0 
                 AND kunci NOT IN (SELECT kunci FROM pengaturan WHERE store_id = ?)""",
            (trx_store_id, trx_store_id)
        ).fetchall()
    toko = {p['kunci']: p['nilai'] for p in pengaturan_rows}
    
    # Override dengan data dari tabel stores (sama seperti get_pengaturan)
    if trx_store_id:
        store = db_execute(conn, 
            "SELECT name, address, phone, email FROM stores WHERE id = ?",
            (trx_store_id,)
        ).fetchone()
        if store:
            toko['nama_toko'] = store['name']
            if store['address']:
                toko['alamat'] = store['address']
            if store['phone']:
                toko['telp'] = store['phone']
    
    conn.close()
    
    try:
        # Ukuran struk digital high-res (lebar 800px agar jelas saat dibagikan)
        WIDTH = 800
        MARGIN = 40
        LINE_HEIGHT = 42
        HEADER_HEIGHT = 160
        FOOTER_HEIGHT = 120
        
        # Hitung total height
        item_height = len(items) * (LINE_HEIGHT * 2 + 8)  # nama + qty x harga
        summary_height = LINE_HEIGHT * 7  # subtotal, diskon, total, bayar, kembalian, metode + padding
        total_height = HEADER_HEIGHT + item_height + summary_height + FOOTER_HEIGHT + 60
        
        # Buat image
        img = Image.new('RGB', (WIDTH, total_height), color='#1a1d27')
        draw = ImageDraw.Draw(img)
        
        # Coba load font sistem yang umum (macOS, Linux, Windows)
        font_paths = [
            "/System/Library/Fonts/Helvetica.ttc",
            "/Library/Fonts/Arial.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
            "C:/Windows/Fonts/arial.ttf",
            "arial.ttf"
        ]
        
        def load_font(size):
            for path in font_paths:
                try:
                    return ImageFont.truetype(path, size)
                except Exception:
                    continue
            return ImageFont.load_default()
        
        font_title = load_font(36)
        font_normal = load_font(28)
        font_small = load_font(24)
        font_large = load_font(32)
        
        y = MARGIN
        
        # Header Toko
        nama_toko = toko.get('nama_toko', 'TOKO')
        draw.text((WIDTH//2, y), nama_toko, fill='#f5a623', font=font_title, anchor='mt')
        y += LINE_HEIGHT + 10
        
        alamat = toko.get('alamat', '')
        if alamat:
            draw.text((WIDTH//2, y), alamat, fill='#8891a8', font=font_small, anchor='mt')
            y += LINE_HEIGHT
        
        telp = toko.get('telp', '')
        if telp:
            draw.text((WIDTH//2, y), f'Telp: {telp}', fill='#8891a8', font=font_small, anchor='mt')
            y += LINE_HEIGHT
        
        y += 20
        draw.line([(MARGIN, y), (WIDTH-MARGIN, y)], fill='#2e3244', width=2)
        y += 20
        
        # Info Transaksi
        waktu = datetime.strptime(trx['waktu'], '%Y-%m-%d %H:%M:%S').strftime('%d/%m/%Y %H:%M')
        draw.text((MARGIN, y), f"No: {trx['no_trx']}", fill='#f0f0f8', font=font_small)
        y += LINE_HEIGHT
        draw.text((MARGIN, y), f"Waktu: {waktu}", fill='#f0f0f8', font=font_small)
        y += LINE_HEIGHT
        
        if trx.get('kasir'):
            draw.text((MARGIN, y), f"Kasir: {trx['kasir']}", fill='#f0f0f8', font=font_small)
            y += LINE_HEIGHT
        
        if trx.get('pelanggan_nama'):
            draw.text((MARGIN, y), f"Pelanggan: {trx['pelanggan_nama']}", fill='#f0f0f8', font=font_small)
            y += LINE_HEIGHT
        
        y += 15
        draw.line([(MARGIN, y), (WIDTH-MARGIN, y)], fill='#2e3244', width=2)
        y += 20
        
        # Items
        for item in items:
            # Nama produk (lebih panjang karena lebar besar)
            nama = item['nama_produk'][:45]
            draw.text((MARGIN, y), f"{item['emoji']} {nama}", fill='#f0f0f8', font=font_normal)
            y += LINE_HEIGHT
            
            # Qty x Harga = Subtotal
            qty_harga = f"{item['qty']} x {item['harga']:,}".replace(',', '.')
            subtotal = f"Rp {item['subtotal']:,}".replace(',', '.')
            draw.text((MARGIN + 20, y), qty_harga, fill='#8891a8', font=font_small)
            draw.text((WIDTH-MARGIN, y), subtotal, fill='#f0f0f8', font=font_large, anchor='rt')
            y += LINE_HEIGHT + 8
        
        y += 15
        draw.line([(MARGIN, y), (WIDTH-MARGIN, y)], fill='#2e3244', width=2)
        y += 20
        
        # Summary
        def draw_row(label, value, color='#f0f0f8', bold=False):
            nonlocal y
            font = font_normal if not bold else font_title
            draw.text((MARGIN, y), label, fill='#8891a8', font=font_small)
            draw.text((WIDTH-MARGIN, y), value, fill=color, font=font, anchor='rt')
            y += LINE_HEIGHT
        
        subtotal = f"Rp {trx['subtotal']:,}".replace(',', '.')
        draw_row('Subtotal', subtotal)
        
        if trx['diskon'] > 0:
            diskon = f"- Rp {trx['diskon']:,}".replace(',', '.')
            draw_row('Diskon', diskon, color='#3dffa0')
        
        total = f"Rp {trx['total']:,}".replace(',', '.')
        draw_row('TOTAL', total, color='#f5a623', bold=True)
        
        bayar = f"Rp {trx['bayar']:,}".replace(',', '.')
        draw_row('Bayar', bayar)
        
        kembalian = f"Rp {trx['kembalian']:,}".replace(',', '.')
        draw_row('Kembalian', kembalian, color='#3dffa0')
        
        metode = (trx.get('metode_bayar') or 'tunai').upper()
        draw_row('Metode', metode)
        
        y += 15
        draw.line([(MARGIN, y), (WIDTH-MARGIN, y)], fill='#2e3244', width=2)
        y += 20
        
        # Footer
        pesan = toko.get('pesan_struk', 'Terima kasih!')
        draw.text((WIDTH//2, y), pesan, fill='#8891a8', font=font_small, anchor='mt')
        y += LINE_HEIGHT + 10
        
        draw.text((WIDTH//2, y), '--- KasirToko ---', fill='#f5a623', font=font_small, anchor='mt')
        
        # Save to buffer
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        
        filename = f"struk-{trx['no_trx']}.png"
        return send_file(
            buffer,
            mimetype='image/png',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        import traceback
        print(f"Error generating struk image: {e}")
        print(traceback.format_exc())
        return server_error()


# ═════════════════════════════════════
#  API: BARCODE GENERATOR
# ═════════════════════════════════════


@bp.route('/api/barcode/generate', methods=['POST'])
@pemilik_required
def generate_barcode():
    """Generate barcode image untuk produk."""
    try:
        from barcode import EAN13, Code128
        from barcode.writer import ImageWriter
        from PIL import Image
    except ImportError:
        return jsonify({'error': 'Library barcode tidak tersedia. Install: pip install python-barcode pillow'}), 500
    
    d = request.json
    code = d.get('code', '').strip()
    format_type = d.get('format', 'code128')  # ean13 atau code128
    
    if not code:
        return jsonify({'error': 'Kode barcode wajib diisi'}), 400
    
    try:
        # Buat barcode
        if format_type == 'ean13':
            # EAN13 harus 12-13 digit
            if not code.isdigit():
                return jsonify({'error': 'EAN13 hanya boleh angka'}), 400
            # Pad dengan 0 di depan jika kurang dari 12 digit
            code = code.zfill(12)[:12]
            barcode_obj = EAN13(code, writer=ImageWriter())
        else:
            # Code128 support alphanumeric
            barcode_obj = Code128(code, writer=ImageWriter())
        
        # Simpan ke buffer
        buffer = io.BytesIO()
        barcode_obj.write(buffer, options={
            'module_height': 15,
            'module_width': 0.5,
            'quiet_zone': 6,
            'font_size': 12,
            'text_distance': 5
        })
        buffer.seek(0)
        
        # Konversi ke PNG dengan PIL untuk optimasi
        img = Image.open(buffer)
        output = io.BytesIO()
        img.save(output, format='PNG')
        output.seek(0)
        
        return send_file(
            output,
            mimetype='image/png',
            as_attachment=True,
            download_name=f'barcode-{code}.png'
        )
        
    except Exception as e:
        return server_error('Gagal generate barcode')


@bp.route('/api/barcode/print-sheet', methods=['POST'])
@pemilik_required
def print_barcode_sheet():
    """Generate sheet barcode untuk multiple produk (printable A4)."""
    try:
        from barcode import Code128
        from barcode.writer import ImageWriter
        from PIL import Image
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image as RLImage
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import cm
    except ImportError:
        return jsonify({'error': 'Library tidak tersedia'}), 500
    
    items = request.json.get('items', [])  # [{id, nama, barcode, harga, qty}]
    
    if not items:
        return jsonify({'error': 'Tidak ada item untuk diprint'}), 400
    
    try:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=1*cm,
            leftMargin=1*cm,
            topMargin=1*cm,
            bottomMargin=1*cm
        )
        
        elements = []
        styles = getSampleStyleSheet()
        
        # Title
        elements.append(Paragraph("LABEL BARCODE", styles['Heading1']))
        elements.append(Spacer(1, 20))
        
        # Buat grid barcode (5 kolom x 11 baris = 55 per halaman)
        from reportlab.lib.utils import ImageReader
        
        row_data = []
        table_data = []
        
        for item in items:
            code = item.get('barcode', '')
            if not code:
                continue
                
            # Generate barcode image
            barcode_obj = Code128(code, writer=ImageWriter())
            img_buffer = io.BytesIO()
            barcode_obj.write(img_buffer, options={
                'module_height': 10,
                'module_width': 0.4,
                'quiet_zone': 3,
                'font_size': 8,
                'text_distance': 3
            })
            img_buffer.seek(0)
            
            # Buat cell dengan barcode + info produk
            cell_content = [
                RLImage(img_buffer, width=2.8*cm, height=1.2*cm),
                Paragraph(f"<font size='7'>{item['nama'][:20]}</font>", styles['Normal']),
                Paragraph(f"<font size='8'><b>Rp {item['harga']:,}</b></font>".replace(',', '.'), styles['Normal'])
            ]
            
            row_data.append(cell_content)
            
            # 5 kolom per baris
            if len(row_data) == 5:
                table_data.append(row_data)
                row_data = []
        
        # Sisa item yang belum masuk
        if row_data:
            while len(row_data) < 5:
                row_data.append('')
            table_data.append(row_data)
        
        if table_data:
            table = Table(table_data, colWidths=[3.5*cm]*5, rowHeights=[2.5*cm]*len(table_data))
            table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('BOX', (0, 0), (-1, -1), 0.5, colors.grey),
                ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('LEFTPADDING', (0, 0), (-1, -1), 5),
                ('RIGHTPADDING', (0, 0), (-1, -1), 5),
                ('TOPPADDING', (0, 0), (-1, -1), 5),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ]))
            elements.append(table)
        
        doc.build(elements)
        buffer.seek(0)
        
        return send_file(
            buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name='barcode-sheet.pdf'
        )
        
    except Exception as e:
        import traceback
        return server_error('Gagal generate sheet barcode')


# ═════════════════════════════════════
#  API: STOK LOG / ADJUST STOK
# ═════════════════════════════════════

import sqlite3
import shutil
from datetime import datetime

print("=" * 60)
print("IMPORT PRODUK DARI BACKUP")
print("=" * 60)

# Backup database aktif dulu
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
shutil.copy('kasirtoko.db', f'kasirtoko.db.backup_{timestamp}')
print(f"[OK] Backup database aktif: kasirtoko.db.backup_{timestamp}")

# Koneksi ke kedua database
conn_bak = sqlite3.connect('kasirtoko.db.bak')
conn_curr = sqlite3.connect('kasirtoko.db')

c_bak = conn_bak.cursor()
c_curr = conn_curr.cursor()

# Ambil produk dari backup
c_bak.execute("SELECT * FROM produk WHERE aktif=1")
produk_backup = c_bak.fetchall()

# Ambil nama kolom
c_bak.execute("PRAGMA table_info(produk)")
cols = [col[1] for col in c_bak.fetchall()]
print(f"\n[INFO] Kolom produk: {cols}")

# Ambil barcode yang sudah ada di database aktif
c_curr.execute("SELECT barcode FROM produk WHERE barcode IS NOT NULL AND barcode != ''")
existing_barcodes = set([r[0] for r in c_curr.fetchall()])

# Import produk
imported = 0
skipped = 0
errors = 0

for row in produk_backup:
    produk_dict = dict(zip(cols, row))
    
    # Skip jika barcode sudah ada
    barcode = produk_dict.get('barcode', '')
    if barcode and barcode in existing_barcodes:
        print(f"[SKIP] Barcode {barcode} sudah ada: {produk_dict['nama']}")
        skipped += 1
        continue
    
    try:
        # Insert produk baru (tanpa ID, biar auto increment)
        c_curr.execute("""
            INSERT INTO produk (nama, harga, stok, emoji, kategori, aktif, 
                              harga_modal, stok_min, diskon, barcode, dibuat, diubah)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            produk_dict['nama'],
            produk_dict['harga'],
            produk_dict.get('stok', 0),
            produk_dict.get('emoji', '📦'),
            produk_dict.get('kategori', 'Umum'),
            1,  # aktif
            produk_dict.get('harga_modal', 0),
            produk_dict.get('stok_min', 0),
            produk_dict.get('diskon', 0),
            barcode if barcode else '',
            produk_dict.get('dibuat', datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
            produk_dict.get('diubah', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        ))
        imported += 1
        print(f"[OK] Import: {produk_dict['nama']}")
    except Exception as e:
        print(f"[ERR] Gagal import {produk_dict.get('nama', '?')}: {e}")
        errors += 1

conn_curr.commit()

# Cek hasil akhir
c_curr.execute("SELECT COUNT(*) FROM produk WHERE aktif=1")
total_produk = c_curr.fetchone()[0]

print("\n" + "=" * 60)
print("HASIL IMPORT")
print("=" * 60)
print(f"Total produk di backup: {len(produk_backup)}")
print(f"Berhasil diimport: {imported}")
print(f"Di-skip (duplikat): {skipped}")
print(f"Error: {errors}")
print(f"\nTotal produk sekarang: {total_produk}")

conn_bak.close()
conn_curr.close()

print("\n[OK] Import selesai! Restart server untuk melihat perubahan.")

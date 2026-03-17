#!/usr/bin/env python3
"""
Script migrasi data dari SQLite ke PostgreSQL
Run: python migrate_to_postgres.py
"""

import os
import sys
import sqlite3

# Fix encoding untuk Windows
sys.stdout.reconfigure(encoding='utf-8')

# Ambil connection string dari environment
POSTGRES_URL = os.environ.get('DATABASE_URL') or os.environ.get('POSTGRES_URL')
SQLITE_DB = 'kasirtoko.db'

def get_sqlite_connection():
    """Koneksi ke database SQLite lokal"""
    if not os.path.exists(SQLITE_DB):
        print(f"File {SQLITE_DB} tidak ditemukan!")
        return None
    
    conn = sqlite3.connect(SQLITE_DB)
    conn.row_factory = sqlite3.Row
    return conn

def get_postgres_connection():
    """Koneksi ke PostgreSQL (Neon)"""
    if not POSTGRES_URL:
        print("POSTGRES_URL/DATABASE_URL tidak ditemukan!")
        print("Set environment variable terlebih dahulu")
        return None
    
    try:
        import psycopg2
        conn = psycopg2.connect(POSTGRES_URL)
        conn.autocommit = False
        return conn
    except Exception as e:
        print(f"Gagal koneksi ke PostgreSQL: {e}")
        return None

def truncate_all_tables(pg_cur):
    """Hapus semua data dari tabel di PostgreSQL"""
    print("Membersihkan tabel di PostgreSQL...")
    tables = [
        'transaksi_item',
        'transaksi',
        'kas',
        'pengaturan',
        'pengguna',
        'pelanggan',
        'tutup_kasir',
        'produk'
    ]
    for table in tables:
        try:
            pg_cur.execute(f"DELETE FROM {table}")
            print(f"  {table} dibersihkan")
        except Exception as e:
            print(f"  {table} gagal: {e}")

def clean_value(value, col_name=None):
    """Bersihkan nilai untuk PostgreSQL"""
    if value == '':
        # String kosong untuk timestamp jadi NULL
        if col_name and col_name in ['waktu', 'void_at', 'dibuat', 'diubah', 'waktu_konfirmasi']:
            return None
        return value
    return value

def migrate_table(sqlite_cur, postgres_conn, table_name, columns, has_id=True, conflict_column=None):
    """Migrate satu tabel dengan savepoint per baris"""
    print(f"\nMigrasi tabel: {table_name}")
    
    # Ambil data dari SQLite
    sqlite_cur.execute(f"SELECT * FROM {table_name}")
    rows = sqlite_cur.fetchall()
    
    if not rows:
        print(f"  Tabel {table_name} kosong, skip")
        return
    
    pg_cur = postgres_conn.cursor()
    success = 0
    skipped = 0
    error_log = []
    
    for row in rows:
        row_dict = dict(row)
        
        # Bersihkan nilai
        for key in row_dict:
            row_dict[key] = clean_value(row_dict[key], key)
        
        # Buat query INSERT
        if has_id and 'id' in row_dict:
            # Untuk tabel dengan ID auto-increment, jangan insert ID
            cols = [c for c in columns if c != 'id']
            placeholders = ','.join(['%s'] * len(cols))
            col_names = ','.join(cols)
            values = [row_dict[c] for c in cols]
            
            query = f"INSERT INTO {table_name} ({col_names}) VALUES ({placeholders})"
            if conflict_column:
                query += f" ON CONFLICT ({conflict_column}) DO NOTHING"
        else:
            placeholders = ','.join(['%s'] * len(columns))
            col_names = ','.join(columns)
            values = [row_dict.get(c) for c in columns]
            
            query = f"INSERT INTO {table_name} ({col_names}) VALUES ({placeholders})"
            if conflict_column:
                query += f" ON CONFLICT ({conflict_column}) DO NOTHING"
        
        try:
            # Gunakan savepoint untuk tiap baris
            pg_cur.execute("SAVEPOINT insert_sp")
            pg_cur.execute(query, values)
            pg_cur.execute("RELEASE SAVEPOINT insert_sp")
            success += 1
        except Exception as e:
            # Rollback ke savepoint dan lanjut baris berikutnya
            pg_cur.execute("ROLLBACK TO SAVEPOINT insert_sp")
            skipped += 1
            if len(error_log) < 3:  # Simpan max 3 error pertama
                error_log.append(str(e)[:100])
    
    postgres_conn.commit()
    pg_cur.close()
    print(f"  {success} baris dimigrasi, {skipped} baris di-skip")
    if error_log and skipped > 0:
        print(f"  Error sample: {error_log[0]}")

def main():
    print("=" * 60)
    print("  MIGRASI SQLITE --> POSTGRESQL")
    print("=" * 60)
    
    # Koneksi ke SQLite
    sqlite_conn = get_sqlite_connection()
    if not sqlite_conn:
        return
    
    sqlite_cur = sqlite_conn.cursor()
    
    # Koneksi ke PostgreSQL
    postgres_conn = get_postgres_connection()
    if not postgres_conn:
        sqlite_conn.close()
        return
    
    pg_cur = postgres_conn.cursor()
    
    try:
        # Bersihkan tabel dulu
        truncate_all_tables(pg_cur)
        postgres_conn.commit()
        
        # 1. PRODUK
        migrate_table(
            sqlite_cur, postgres_conn, 'produk',
            ['id', 'nama', 'harga', 'stok', 'emoji', 'kategori', 'aktif', 
             'harga_modal', 'stok_min', 'diskon', 'barcode', 'dibuat', 'diubah']
        )
        
        # 2. PELANGGAN
        migrate_table(
            sqlite_cur, postgres_conn, 'pelanggan',
            ['id', 'nama', 'telepon', 'alamat', 'catatan', 'dibuat']
        )
        
        # 3. PENGGUNA - dengan ON CONFLICT untuk username
        migrate_table(
            sqlite_cur, postgres_conn, 'pengguna',
            ['id', 'username', 'nama', 'password', 'role', 'aktif', 'dibuat'],
            conflict_column='username'
        )
        
        # 4. PENGATURAN - dengan ON CONFLICT untuk kunci
        migrate_table(
            sqlite_cur, postgres_conn, 'pengaturan',
            ['kunci', 'nilai'],
            has_id=False,
            conflict_column='kunci'
        )
        
        # 5. TUTUP_KASIR (migrasi dulu karena transaksi punya FK ke tutup_kasir)
        migrate_table(
            sqlite_cur, postgres_conn, 'tutup_kasir',
            ['id', 'waktu', 'total', 'total_tunai', 'total_transfer', 
             'total_qris', 'jumlah_trx', 'keterangan', 'status',
             'dibuat_oleh', 'dikonfirmasi_oleh', 'waktu_konfirmasi']
        )
        
        # 6. KAS
        migrate_table(
            sqlite_cur, postgres_conn, 'kas',
            ['id', 'tipe', 'jumlah', 'keterangan', 'waktu', 'metode']
        )
        
        # 7. TRANSAKSI
        migrate_table(
            sqlite_cur, postgres_conn, 'transaksi',
            ['id', 'no_trx', 'waktu', 'subtotal', 'diskon', 'diskon_val', 
             'diskon_tipe', 'total', 'bayar', 'kembalian', 'kasir', 
             'pelanggan_id', 'metode_bayar', 'tutup_kasir_id',
             'status', 'void_reason', 'void_by', 'void_at']
        )
        
        # 8. TRANSAKSI_ITEM
        migrate_table(
            sqlite_cur, postgres_conn, 'transaksi_item',
            ['id', 'transaksi_id', 'produk_id', 'nama_produk', 'emoji', 
             'harga', 'qty', 'subtotal']
        )
        
        print("\n" + "=" * 60)
        print("  MIGRASI SELESAI!")
        print("=" * 60)
        print("\nData berhasil dipindahkan dari SQLite ke PostgreSQL")
        print("Aplikasi Vercel sekarang bisa menggunakan data lama Anda")
        
    except Exception as e:
        postgres_conn.rollback()
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        sqlite_conn.close()
        postgres_conn.close()
        print("\nKoneksi ditutup")

if __name__ == '__main__':
    main()

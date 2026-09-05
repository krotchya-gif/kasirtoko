#!/usr/bin/env python3
"""
Script migrasi data dari SQLite ke PostgreSQL
Run: python3 migrate_to_postgres.py
"""

import os
import sys
import sqlite3

# Fix encoding untuk Windows
sys.stdout.reconfigure(encoding='utf-8')

POSTGRES_URL = os.environ.get('DATABASE_URL') or os.environ.get('POSTGRES_URL')
SQLITE_DB = 'kasirtoko.db'

def get_sqlite_connection():
    if not os.path.exists(SQLITE_DB):
        print(f"File {SQLITE_DB} tidak ditemukan!")
        return None
    conn = sqlite3.connect(SQLITE_DB)
    conn.row_factory = sqlite3.Row
    return conn

def get_postgres_connection():
    if not POSTGRES_URL:
        print("POSTGRES_URL/DATABASE_URL tidak ditemukan!")
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
    print("Membersihkan tabel di PostgreSQL...")
    tables = [
        'admin_logs', 'user_stores', 'piutang_bayar', 'transaksi_item',
        'transaksi', 'stok_log', 'kas', 'pengaturan', 'pengguna',
        'pelanggan', 'tutup_kasir', 'produk', 'stores', 'users'
    ]
    for table in tables:
        try:
            pg_cur.execute(f"DELETE FROM {table}")
            print(f"  {table} dibersihkan")
        except Exception as e:
            print(f"  {table} gagal: {e}")

def clean_value(value, col_name=None):
    if value == '':
        if col_name and col_name in ['waktu', 'void_at', 'dibuat', 'diubah', 'waktu_konfirmasi']:
            return None
        return value
    return value

def migrate_table_with_id(sqlite_cur, postgres_conn, table_name, columns):
    """Migrate dengan mempertahankan ID asli dari SQLite (OVERRIDING SYSTEM VALUE)"""
    print(f"\nMigrasi tabel: {table_name} (with ID)")
    
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
        
        for key in row_dict:
            row_dict[key] = clean_value(row_dict[key], key)
        
        # Insert dengan ID menggunakan OVERRIDING SYSTEM VALUE
        placeholders = ','.join(['%s'] * len(columns))
        col_names = ','.join(columns)
        # .get agar toleran bila SQLite belum punya kolom baru (mis. idempotency_key)
        values = [row_dict.get(c) for c in columns]
        
        query = f"INSERT INTO {table_name} ({col_names}) OVERRIDING SYSTEM VALUE VALUES ({placeholders})"
        
        try:
            pg_cur.execute("SAVEPOINT insert_sp")
            pg_cur.execute(query, values)
            pg_cur.execute("RELEASE SAVEPOINT insert_sp")
            success += 1
        except Exception as e:
            pg_cur.execute("ROLLBACK TO SAVEPOINT insert_sp")
            skipped += 1
            if len(error_log) < 3:
                error_log.append(str(e)[:100])
    
    postgres_conn.commit()
    pg_cur.close()
    print(f"  {success} baris dimigrasi, {skipped} baris di-skip")
    if error_log and skipped > 0:
        print(f"  Error sample: {error_log[0]}")

def migrate_table(sqlite_cur, postgres_conn, table_name, columns, has_id=True, conflict_column=None):
    """Migrate tanpa ID (auto-increment)"""
    print(f"\nMigrasi tabel: {table_name}")
    
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
        
        for key in row_dict:
            row_dict[key] = clean_value(row_dict[key], key)
        
        if has_id and 'id' in row_dict:
            cols = [c for c in columns if c != 'id']
            placeholders = ','.join(['%s'] * len(cols))
            col_names = ','.join(cols)
            values = [row_dict[c] for c in cols]
            
            query = f"INSERT INTO {table_name} ({col_names}) VALUES ({placeholders})"
            if conflict_column:
                query += f" ON CONFLICT ({conflict_column}) DO NOTHING"
            else:
                query += " ON CONFLICT DO NOTHING"
        else:
            placeholders = ','.join(['%s'] * len(columns))
            col_names = ','.join(columns)
            values = [row_dict.get(c) for c in columns]
            
            query = f"INSERT INTO {table_name} ({col_names}) VALUES ({placeholders})"
            if conflict_column:
                query += f" ON CONFLICT ({conflict_column}) DO NOTHING"
            else:
                query += " ON CONFLICT DO NOTHING"
        
        try:
            pg_cur.execute("SAVEPOINT insert_sp")
            pg_cur.execute(query, values)
            pg_cur.execute("RELEASE SAVEPOINT insert_sp")
            success += 1
        except Exception as e:
            pg_cur.execute("ROLLBACK TO SAVEPOINT insert_sp")
            skipped += 1
            if len(error_log) < 3:
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
    
    sqlite_conn = get_sqlite_connection()
    if not sqlite_conn:
        return
    
    sqlite_cur = sqlite_conn.cursor()
    
    postgres_conn = get_postgres_connection()
    if not postgres_conn:
        sqlite_conn.close()
        return
    
    pg_cur = postgres_conn.cursor()
    
    try:
        truncate_all_tables(pg_cur)
        postgres_conn.commit()
        
        # 1. USERS - dengan ID (parent)
        migrate_table_with_id(sqlite_cur, postgres_conn, 'users',
            ['id', 'username', 'nama', 'password', 'role', 'is_superadmin', 'aktif', 'dibuat']
        )
        
        # 2. STORES - dengan ID (parent)
        migrate_table_with_id(sqlite_cur, postgres_conn, 'stores',
            ['id', 'name', 'slug', 'address', 'phone', 'email', 'owner_id', 'is_active', 'dibuat']
        )
        
        # 3. PRODUK - dengan ID
        migrate_table_with_id(sqlite_cur, postgres_conn, 'produk',
            ['id', 'nama', 'harga', 'stok', 'emoji', 'kategori', 'aktif', 
             'harga_modal', 'stok_min', 'diskon', 'barcode', 'dibuat', 'diubah', 'store_id']
        )
        
        # 4. PELANGGAN - dengan ID
        migrate_table_with_id(sqlite_cur, postgres_conn, 'pelanggan',
            ['id', 'nama', 'telepon', 'alamat', 'catatan', 'dibuat', 'store_id']
        )
        
        # 5. PENGGUNA
        migrate_table(sqlite_cur, postgres_conn, 'pengguna',
            ['id', 'username', 'nama', 'password', 'role', 'aktif', 'dibuat'],
            conflict_column='username'
        )
        
        # 6. PENGATURAN (no ID) — sertakan store_id agar setting per toko
        # tidak runtuh jadi satu (PK PG: kunci + COALESCE(store_id,0))
        migrate_table(sqlite_cur, postgres_conn, 'pengaturan',
            ['kunci', 'nilai', 'store_id'],
            has_id=False,
            conflict_column=None
        )
        
        # 7. TUTUP_KASIR - dengan ID
        migrate_table_with_id(sqlite_cur, postgres_conn, 'tutup_kasir',
            ['id', 'waktu', 'total', 'total_tunai', 'total_transfer', 
             'total_qris', 'jumlah_trx', 'keterangan', 'status',
             'dibuat_oleh', 'dikonfirmasi_oleh', 'waktu_konfirmasi', 'store_id']
        )
        
        # 8. KAS - dengan ID
        migrate_table_with_id(sqlite_cur, postgres_conn, 'kas',
            ['id', 'tipe', 'jumlah', 'keterangan', 'waktu', 'metode', 'store_id']
        )
        
        # 9. TRANSAKSI - dengan ID
        migrate_table_with_id(sqlite_cur, postgres_conn, 'transaksi',
            ['id', 'no_trx', 'waktu', 'subtotal', 'diskon', 'diskon_val', 
             'diskon_tipe', 'total', 'bayar', 'kembalian', 'kasir', 
             'pelanggan_id', 'metode_bayar', 'tutup_kasir_id',
             'status', 'void_reason', 'void_by', 'void_at', 'is_lunas', 
             'terbayar', 'sisa_piutang', 'store_id']
        )
        
        # 10. TRANSAKSI_ITEM - dengan ID
        migrate_table_with_id(sqlite_cur, postgres_conn, 'transaksi_item',
            ['id', 'transaksi_id', 'produk_id', 'nama_produk', 'emoji', 
             'harga', 'qty', 'subtotal']
        )
        
        # 11. PIUTANG_BAYAR - dengan ID (termasuk idempotency_key P1-3)
        migrate_table_with_id(sqlite_cur, postgres_conn, 'piutang_bayar',
            ['id', 'transaksi_id', 'nominal', 'metode_bayar', 'catatan',
             'dibuat_oleh', 'waktu', 'store_id', 'idempotency_key']
        )
        
        # 12. STOK_LOG - dengan ID
        migrate_table_with_id(sqlite_cur, postgres_conn, 'stok_log',
            ['id', 'produk_id', 'tipe', 'jumlah', 'stok_sebelum', 'stok_sesudah',
             'alasan', 'keterangan', 'transaksi_id', 'dibuat_oleh', 'waktu', 'store_id']
        )
        
        # 13. USER_STORES - dengan ID
        migrate_table_with_id(sqlite_cur, postgres_conn, 'user_stores',
            ['id', 'user_id', 'store_id', 'role', 'dibuat']
        )
        
        # 14. ADMIN_LOGS - dengan ID
        migrate_table_with_id(sqlite_cur, postgres_conn, 'admin_logs',
            ['id', 'admin_id', 'store_id', 'action_type', 'target_table', 
             'target_id', 'old_value', 'new_value', 'ip_address', 'dibuat']
        )
        
        print("\n" + "=" * 60)
        print("  MIGRASI SELESAI!")
        print("=" * 60)
        print("\nData berhasil dipindahkan dari SQLite ke PostgreSQL")
        
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

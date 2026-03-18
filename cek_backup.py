import sqlite3

print("=" * 50)
print("CEK DATABASE BACKUP (.bak)")
print("=" * 50)

conn = sqlite3.connect('kasirtoko.db.bak')
c = conn.cursor()

# List tabel
c.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [t[0] for t in c.fetchall()]
print(f"\n[TABEL] {tables}")

# Hitung data
for table in ['produk', 'transaksi', 'pelanggan', 'pengguna', 'kas']:
    try:
        c.execute(f"SELECT COUNT(*) FROM {table}")
        count = c.fetchone()[0]
        print(f"  - {table}: {count} row")
    except:
        print(f"  - {table}: (tidak ada)")

conn.close()

print("\n" + "=" * 50)
print("CEK DATABASE AKTIF (.db)")
print("=" * 50)

conn2 = sqlite3.connect('kasirtoko.db')
c2 = conn2.cursor()

for table in ['produk', 'transaksi', 'pelanggan', 'pengguna', 'kas']:
    try:
        c2.execute(f"SELECT COUNT(*) FROM {table}")
        count = c2.fetchone()[0]
        print(f"  - {table}: {count} row")
    except:
        print(f"  - {table}: (tidak ada)")

conn2.close()

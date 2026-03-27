#!/usr/bin/env python3
import sqlite3

conn = sqlite3.connect('kasirtoko.db')
c = conn.cursor()

# 1. Tambah kolom store_id
try:
    c.execute('ALTER TABLE pengaturan ADD COLUMN store_id INTEGER REFERENCES stores(id) ON DELETE CASCADE')
    print('[OK] Kolom store_id ditambah')
except Exception as e:
    print('[SKIP]', str(e)[:50])

# 2. Index
try:
    c.execute('CREATE INDEX IF NOT EXISTS idx_pengaturan_store ON pengaturan(store_id)')
    print('[OK] Index dibuat')
except Exception as e:
    print('[SKIP]', str(e)[:50])

# 3. Fix slug KIOS ANGEL
c.execute("UPDATE stores SET slug = 'kios-angel' WHERE id = 1")
print('[OK] Slug KIOS ANGEL updated')

# 4. Cek hasil
c.execute('SELECT id, name, slug FROM stores')
print('\n=== STORES ===')
for row in c.fetchall():
    print(f"ID {row[0]}: {row[1]} (slug: {row[2]})")

conn.commit()
conn.close()
print('\n[DONE] Database updated')

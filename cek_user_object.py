import sqlite3
import sys
sys.path.insert(0, 'c:\\Users\\H\\Desktop\\PROJECT\\kasirtoko')

from app import get_current_user, row_to_dict

print("=" * 60)
print("CEK USER OBJECT (SIMULASI)")
print("=" * 60)

# Simulasi get_current_user untuk superadmin
conn = sqlite3.connect('kasirtoko.db')
conn.row_factory = sqlite3.Row
c = conn.cursor()

c.execute("SELECT id, username, nama, role, is_superadmin FROM users WHERE username='superadmin'")
user_row = c.fetchone()
print(f"\n[RAW DATA DARI SQLITE]")
print(f"  Type: {type(user_row)}")
print(f"  Data: {dict(user_row)}")
print(f"  is_superadmin type: {type(user_row['is_superadmin'])}")
print(f"  is_superadmin value: {user_row['is_superadmin']}")

# Simulasi row_to_dict
user_dict = row_to_dict(user_row)
print(f"\n[SETELAH row_to_dict]")
print(f"  Type: {type(user_dict)}")
print(f"  Data: {user_dict}")
print(f"  is_superadmin type: {type(user_dict['is_superadmin'])}")
print(f"  is_superadmin value: {user_dict['is_superadmin']}")

# Cek kondisi yang dipakai di template
print(f"\n[CEK KONDISI]")
print(f"  user.is_superadmin: {user_dict['is_superadmin']}")
print(f"  user.is_superadmin == 1: {user_dict['is_superadmin'] == 1}")
print(f"  user.is_superadmin == '1': {user_dict['is_superadmin'] == '1'}")
print(f"  user.is_superadmin == True: {user_dict['is_superadmin'] == True}")
print(f"  bool(user.is_superadmin): {bool(user_dict['is_superadmin'])}")

# Cek untuk pemilik
c.execute("SELECT id, username, nama, role, is_superadmin FROM users WHERE username='pemilik'")
pemilik_row = c.fetchone()
pemilik_dict = row_to_dict(pemilik_row)
print(f"\n[PEMILIK - BANDINGKAN]")
print(f"  is_superadmin: {pemilik_dict['is_superadmin']} (type: {type(pemilik_dict['is_superadmin'])})")

conn.close()

# KasirToko Multi-Tenant Draft

Sistem kasir dengan hierarki: **Superadmin → Owner → Karyawan**

---

## 1. Hierarki Akses

| Level | Role | Bisa Akses | Keterangan |
|-------|------|------------|------------|
| 1 | **Superadmin** | Semua toko (read/write) | Kamu, bisa edit bantu owner |
| 2 | **Owner** | Toko yang dimiliki saja | Bisa punya multiple toko |
| 3 | **Admin** | Toko ditugaskan | Manage produk, lihat laporan |
| 4 | **Kasir** | Toko ditugaskan | Cuma transaksi |

---

## 2. Database Schema

### 2.1 Users (Semua pengguna)

```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    name TEXT NOT NULL,
    email TEXT,
    phone TEXT,
    is_superadmin BOOLEAN DEFAULT 0,  -- Kamu (1 akun saja)
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_users_username ON users(username);
```

### 2.2 Stores (Toko/Cabang)

```sql
CREATE TABLE stores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    slug TEXT UNIQUE NOT NULL,        -- URL: /store/nama-toko
    address TEXT,
    phone TEXT,
    email TEXT,
    owner_id INTEGER NOT NULL,        -- Owner toko
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX idx_stores_owner ON stores(owner_id);
CREATE INDEX idx_stores_slug ON stores(slug);
```

### 2.3 User_Stores (Karyawan di toko)

Owner **tidak** masuk tabel ini (sudah ada `owner_id` di stores).

```sql
CREATE TABLE user_stores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    store_id INTEGER NOT NULL,
    role TEXT CHECK(role IN ('admin', 'kasir')) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (store_id) REFERENCES stores(id) ON DELETE CASCADE,
    UNIQUE(user_id, store_id)         -- 1 user, 1 role per toko
);

CREATE INDEX idx_user_stores_user ON user_stores(user_id);
CREATE INDEX idx_user_stores_store ON user_stores(store_id);
```

### 2.4 Products (Produk per toko)

```sql
CREATE TABLE products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    store_id INTEGER NOT NULL,        -- ISOLASI: tiap toko punya produk sendiri
    category_id INTEGER,
    sku TEXT,
    name TEXT NOT NULL,
    description TEXT,
    purchase_price INTEGER DEFAULT 0, -- harga beli
    selling_price INTEGER NOT NULL,   -- harga jual
    stock INTEGER DEFAULT 0,
    min_stock INTEGER DEFAULT 0,      -- alert stok rendah
    barcode TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (store_id) REFERENCES stores(id) ON DELETE CASCADE
);

CREATE INDEX idx_products_store ON products(store_id);
CREATE INDEX idx_products_barcode ON products(barcode);
```

### 2.5 Transactions (Transaksi per toko)

```sql
CREATE TABLE transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    store_id INTEGER NOT NULL,        -- ISOLASI
    invoice_number TEXT NOT NULL,
    cashier_id INTEGER NOT NULL,      -- User yang input
    customer_id INTEGER,              -- Optional
    total_amount INTEGER NOT NULL,
    discount_amount INTEGER DEFAULT 0,
    final_amount INTEGER NOT NULL,
    paid_amount INTEGER NOT NULL,
    change_amount INTEGER DEFAULT 0,
    payment_method TEXT DEFAULT 'cash',
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (store_id) REFERENCES stores(id) ON DELETE CASCADE,
    FOREIGN KEY (cashier_id) REFERENCES users(id),
    UNIQUE(store_id, invoice_number)  -- Invoice unik per toko
);

CREATE INDEX idx_transactions_store ON transactions(store_id);
CREATE INDEX idx_transactions_date ON transactions(created_at);
```

### 2.6 Admin_Logs (Audit trail)

```sql
CREATE TABLE admin_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    admin_id INTEGER NOT NULL,        -- Superadmin yang action
    store_id INTEGER NOT NULL,        -- Toko yang di-edit
    action_type TEXT NOT NULL,        -- edit_product, delete_transaction, dll
    target_table TEXT,
    target_id INTEGER,
    old_value TEXT,                   -- JSON data lama
    new_value TEXT,                   -- JSON data baru
    ip_address TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (admin_id) REFERENCES users(id),
    FOREIGN KEY (store_id) REFERENCES stores(id)
);
```

---

## 3. Permission Helper (Python)

```python
class PermissionHelper:
    """Cek permission user di toko tertentu"""
    
    @staticmethod
    def is_superadmin(user_id, db):
        result = db.execute(
            "SELECT is_superadmin FROM users WHERE id = ?",
            (user_id,)
        ).fetchone()
        return result and result['is_superadmin'] == 1
    
    @staticmethod
    def is_store_owner(user_id, store_id, db):
        result = db.execute(
            "SELECT 1 FROM stores WHERE id = ? AND owner_id = ?",
            (store_id, user_id)
        ).fetchone()
        return result is not None
    
    @staticmethod
    def can_access_store(user_id, store_id, db):
        """Superadmin: all | Owner: own store | Karyawan: assigned"""
        if PermissionHelper.is_superadmin(user_id, db):
            return True
        if PermissionHelper.is_store_owner(user_id, store_id, db):
            return True
        
        result = db.execute(
            "SELECT 1 FROM user_stores WHERE user_id = ? AND store_id = ?",
            (user_id, store_id)
        ).fetchone()
        return result is not None
    
    @staticmethod
    def can_manage_products(user_id, store_id, db):
        if PermissionHelper.is_superadmin(user_id, db):
            return True
        if PermissionHelper.is_store_owner(user_id, store_id, db):
            return True
        
        result = db.execute(
            "SELECT role FROM user_stores WHERE user_id = ? AND store_id = ?",
            (user_id, store_id)
        ).fetchone()
        return result and result['role'] == 'admin'
    
    @staticmethod
    def get_accessible_stores(user_id, db):
        """List semua toko yang bisa diakses user"""
        if PermissionHelper.is_superadmin(user_id, db):
            return db.execute("SELECT * FROM stores WHERE is_active = 1").fetchall()
        
        return db.execute("""
            SELECT DISTINCT s.* FROM stores s
            LEFT JOIN user_stores us ON s.id = us.store_id
            WHERE s.is_active = 1 
              AND (s.owner_id = ? OR us.user_id = ?)
        """, (user_id, user_id)).fetchall()
```

---

## 4. Flow Sistem

### 4.1 Login

```
User login → Cek is_superadmin
    ├── YA → Dashboard: List semua toko → Pilih toko → Masuk sebagai "ghost admin"
    └── TIDAK → Dashboard: List toko milik/assignment → Pilih toko
```

### 4.2 Superadmin Mode

```python
@app.route('/admin/select-store')
def admin_select_store():
    if not is_superadmin(current_user.id):
        abort(403)
    
    stores = get_all_stores()  # Semua toko
    return render_template('admin_select_store.html', stores=stores)

@app.route('/admin/manage-store/<int:store_id>')
def admin_manage_store(store_id):
    if not is_superadmin(current_user.id):
        abort(403)
    
    session['admin_viewing_store'] = store_id
    log_admin_action(current_user.id, store_id, 'view_store')
    return redirect('/dashboard')
```

### 4.3 Query dengan Isolasi

```python
def get_products(store_id=None):
    # Superadmin dengan store yang dipilih
    if is_superadmin(session['user_id']) and session.get('admin_viewing_store'):
        store_id = session['admin_viewing_store']
    
    # Owner/Karyawan dengan store default
    elif not store_id:
        store_id = session['current_store_id']
    
    return db.execute(
        "SELECT * FROM products WHERE store_id = ?",
        (store_id,)
    ).fetchall()
```

---

## 5. Decorator Flask

```python
def require_store_access(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        store_id = session.get('current_store_id')
        if not can_access_store(g.user_id, store_id, g.db):
            return {"error": "Access denied"}, 403
        return f(*args, **kwargs)
    return decorated

def require_superadmin(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not is_superadmin(g.user_id, g.db):
            return {"error": "Superadmin required"}, 403
        return f(*args, **kwargs)
    return decorated

# Usage
@app.route('/api/products', methods=['POST'])
@require_store_access
def create_product():
    # Cek bisa manage produk
    if not can_manage_products(g.user_id, session['store_id'], g.db):
        return {"error": "Permission denied"}, 403
    # ... create product
```

---

## 6. Initial Data

```sql
-- Superadmin default (ganti password!)
INSERT INTO users (username, password_hash, name, is_superadmin) 
VALUES ('superadmin', 'HASH_DISINI', 'Super Administrator', 1);

-- Toko contoh
INSERT INTO stores (name, slug, address, phone, owner_id)
VALUES ('Toko Contoh', 'toko-contoh', 'Jl. Contoh No. 1', '08123456789', 1);
```

---

## 7. Keunggulan Pattern Ini

1. **Isolasi sempurna**: Tiap toko data terpisah via `store_id`
2. **Flexible role**: Owner bisa punya banyak toko
3. **Superadmin power**: Bantu owner tanpa limit
4. **Audit trail**: Log semua action superadmin
5. **Scalable**: SQLite handle <10 toko dengan mudah

---

*Draft: 2026-03-18*

-- Fix database untuk v2.1.1
-- 1. Tambah kolom store_id ke pengaturan
ALTER TABLE pengaturan ADD COLUMN store_id INTEGER REFERENCES stores(id) ON DELETE CASCADE;

-- 2. Buat index
CREATE INDEX IF NOT EXISTS idx_pengaturan_store ON pengaturan(store_id);

-- 3. Fix slug KIOS ANGEL
UPDATE stores SET slug = 'kios-angel' WHERE id = 1 AND name = 'KIOS ANGEL';

-- 4. Set store_id default untuk pengaturan existing (jadi global settings)
UPDATE pengaturan SET store_id = NULL WHERE store_id IS NULL;

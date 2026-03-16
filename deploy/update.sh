#!/bin/bash
# ═══════════════════════════════════════════════════════
#  KasirToko — Update Script
#  Dijalankan saat kamu upload kode baru ke server
#  Jalankan: bash deploy/update.sh
# ═══════════════════════════════════════════════════════

APP_DIR="/home/$USER/kasirtoko"

echo "🔄 Update KasirToko..."

# Update dependensi jika requirements.txt berubah
source "$APP_DIR/venv/bin/activate"
pip install -r "$APP_DIR/requirements.txt" -q
deactivate

# Migrasi DB (init_db aman dijalankan berkali-kali)
"$APP_DIR/venv/bin/python3" -c "import sys; sys.path.insert(0,'$APP_DIR'); import app; app.init_db()"

# Restart app
sudo systemctl restart kasirtoko

echo "✅ Update selesai. App sudah berjalan dengan versi terbaru."
sudo systemctl status kasirtoko --no-pager -l

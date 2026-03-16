#!/bin/bash
# ═══════════════════════════════════════════════════════
#  KasirToko — Setup Script untuk Ubuntu Server
#  Jalankan: bash setup.sh
# ═══════════════════════════════════════════════════════

set -e  # Berhenti jika ada error

APP_DIR="/home/$USER/kasirtoko"
VENV_DIR="$APP_DIR/venv"
SERVICE_NAME="kasirtoko"

echo ""
echo "════════════════════════════════════"
echo "  KasirToko — Setup Ubuntu Server"
echo "  User: $USER"
echo "  Dir : $APP_DIR"
echo "════════════════════════════════════"
echo ""

# ─── 1. Update & install paket ───────────────────────
echo "[1/6] Install dependensi sistem..."
sudo apt-get update -qq
sudo apt-get install -y python3 python3-pip python3-venv nginx curl

# ─── 2. Buat virtual environment ─────────────────────
echo "[2/6] Buat virtual environment Python..."
cd "$APP_DIR"
python3 -m venv venv
source "$VENV_DIR/bin/activate"
pip install --upgrade pip -q
pip install -r requirements.txt -q
deactivate

# ─── 3. Buat folder logs ─────────────────────────────
echo "[3/6] Buat folder logs..."
mkdir -p "$APP_DIR/logs"

# ─── 4. Inisialisasi database ────────────────────────
echo "[4/6] Inisialisasi database..."
cd "$APP_DIR"
"$VENV_DIR/bin/python3" -c "import app; app.init_db()"

# ─── 5. Setup systemd service ────────────────────────
echo "[5/6] Setup systemd service..."

# Ganti placeholder 'ubuntu' dengan username aktual
sed "s/ubuntu/$USER/g" "$APP_DIR/deploy/kasirtoko.service" | \
    sudo tee /etc/systemd/system/kasirtoko.service > /dev/null

sudo systemctl daemon-reload
sudo systemctl enable kasirtoko
sudo systemctl restart kasirtoko

# ─── 6. Setup nginx ──────────────────────────────────
echo "[6/6] Setup nginx..."

# Ganti path sesuai user aktual
sed "s|/home/ubuntu|/home/$USER|g" "$APP_DIR/deploy/kasirtoko.nginx" | \
    sudo tee /etc/nginx/sites-available/kasirtoko > /dev/null

# Aktifkan site, nonaktifkan default
sudo ln -sf /etc/nginx/sites-available/kasirtoko /etc/nginx/sites-enabled/kasirtoko
sudo rm -f /etc/nginx/sites-enabled/default

# Test konfigurasi nginx
sudo nginx -t
sudo systemctl restart nginx
sudo systemctl enable nginx

# ─── Selesai ─────────────────────────────────────────
echo ""
echo "════════════════════════════════════"
echo "  ✅ Setup selesai!"
echo ""

# Tampilkan IP server
IP=$(hostname -I | awk '{print $1}')
echo "  Buka di browser: http://$IP"
echo "  atau            : http://$(hostname)"
echo ""
echo "  Perintah berguna:"
echo "  sudo systemctl status kasirtoko   (cek status app)"
echo "  sudo systemctl restart kasirtoko  (restart app)"
echo "  tail -f $APP_DIR/logs/error.log   (lihat log error)"
echo "════════════════════════════════════"
echo ""

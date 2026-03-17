#!/bin/bash
# KasirToko VPS Deployment Script
# Tested on: Ubuntu 20.04/22.04 LTS

set -e  # Exit on error

# Warna output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Konfigurasi
APP_NAME="kasirtoko"
APP_DIR="/opt/$APP_NAME"
APP_USER="kasirtoko"
DOMAIN="${1:-}"

# Logging
log() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
    exit 1
}

# Check root
if [[ $EUID -ne 0 ]]; then
   error "Script ini harus dijalankan sebagai root (gunakan sudo)"
fi

# Check domain
if [ -z "$DOMAIN" ]; then
    warn "Usage: ./deploy-vps.sh your-domain.com"
    warn "Contoh: ./deploy-vps.sh kasir.tokoku.com"
    exit 1
fi

log "🚀 Memulai deploy KasirToko ke $DOMAIN..."

# 1. Update System
log "📦 Updating system packages..."
apt-get update && apt-get upgrade -y

# 2. Install Dependencies
log "🔧 Installing dependencies..."
apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    nginx \
    supervisor \
    git \
    curl \
    certbot \
    python3-certbot-nginx \
    postgresql \
    postgresql-contrib \
    libpq-dev \
    build-essential

# 3. Setup PostgreSQL
log "🐘 Setting up PostgreSQL..."
sudo -u postgres psql << EOF
CREATE USER $APP_USER WITH PASSWORD 'kasirtoko_secure_password';
CREATE DATABASE $APP_NAME OWNER $APP_USER;
GRANT ALL PRIVILEGES ON DATABASE $APP_NAME TO $APP_USER;
\q
EOF

# 4. Create Application User
log "👤 Creating application user..."
if ! id "$APP_USER" &>/dev/null; then
    useradd -m -s /bin/bash $APP_USER
fi

# 5. Setup Application Directory
log "📁 Setting up application directory..."
mkdir -p $APP_DIR
mkdir -p $APP_DIR/backups
mkdir -p /var/log/$APP_NAME

# 6. Clone Repository (atau copy files)
log "📥 Downloading application..."
cd $APP_DIR

# Jika menggunakan git:
# git clone https://github.com/yourusername/kasirtoko.git .

# Atau copy dari local (asumsi script dijalankan dari direktori project)
if [ -f "../app.py" ]; then
    cp -r ../* .
else
    error "Tidak dapat menemukan file aplikasi. Pastikan menjalankan script dari direktori deploy/"
fi

# 7. Setup Python Virtual Environment
log "🐍 Setting up Python environment..."
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# 8. Generate Secret Key
SECRET_KEY=$(openssl rand -hex 32)

# 9. Create Environment File
cat > .env << EOF
SECRET_KEY=$SECRET_KEY
POSTGRES_URL=postgresql://$APP_USER:kasirtoko_secure_password@localhost:5432/$APP_NAME
FLASK_ENV=production
FLASK_DEBUG=0
EOF

# 10. Set Permissions
log "🔐 Setting permissions..."
chown -R $APP_USER:$APP_USER $APP_DIR
chmod -R 755 $APP_DIR
chown -R $APP_USER:$APP_USER /var/log/$APP_NAME

# 11. Setup Systemd Service
log "⚙️ Creating systemd service..."
cat > /etc/systemd/system/$APP_NAME.service << EOF
[Unit]
Description=KasirToko Flask Application
After=network.target postgresql.service

[Service]
Type=simple
User=$APP_USER
Group=$APP_USER
WorkingDirectory=$APP_DIR
Environment="PATH=$APP_DIR/venv/bin"
EnvironmentFile=$APP_DIR/.env
ExecStart=$APP_DIR/venv/bin/gunicorn -w 4 -b 127.0.0.1:5000 --access-logfile /var/log/$APP_NAME/access.log --error-logfile /var/log/$APP_NAME/error.log app:app
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

# 12. Setup Nginx
log "🌐 Configuring Nginx..."
cat > /etc/nginx/sites-available/$APP_NAME << EOF
server {
    listen 80;
    server_name $DOMAIN;

    client_max_body_size 64M;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }

    location /static {
        alias $APP_DIR/static;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
}
EOF

# Enable site
ln -sf /etc/nginx/sites-available/$APP_NAME /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

# Test nginx config
nginx -t

# 13. Setup SSL dengan Certbot
log "🔒 Setting up SSL certificate..."
systemctl start $APP_NAME
systemctl enable $APP_NAME

# Tunggu aplikasi start
sleep 5

# Get SSL certificate
certbot --nginx -d $DOMAIN --non-interactive --agree-tos --email admin@$DOMAIN

# 14. Setup Auto-Renewal SSL
log "🔄 Setting up auto-renewal..."
echo "0 12 * * * /usr/bin/certbot renew --quiet" | crontab -

# 15. Setup Backup Script
log "💾 Creating backup script..."
cat > $APP_DIR/backup.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/opt/kasirtoko/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Backup database
sudo -u postgres pg_dump kasirtoko > "$BACKUP_DIR/db_$TIMESTAMP.sql"

# Backup files
tar -czf "$BACKUP_DIR/files_$TIMESTAMP.tar.gz" -C /opt/kasirtoko .

# Hapus backup lama (keep 30 days)
find $BACKUP_DIR -name "*.sql" -mtime +30 -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +30 -delete

echo "Backup completed: $TIMESTAMP"
EOF
chmod +x $APP_DIR/backup.sh

# Cron job untuk backup harian
echo "0 2 * * * /opt/kasirtoko/backup.sh >> /var/log/kasirtoko/backup.log 2>&1" | crontab -

# 16. Start Services
log "🚀 Starting services..."
systemctl daemon-reload
systemctl enable $APP_NAME
systemctl restart $APP_NAME
systemctl restart nginx

# 17. Check Status
log "✅ Checking deployment status..."
sleep 3

if systemctl is-active --quiet $APP_NAME; then
    log "✅ Aplikasi berjalan!"
else
    error "❌ Aplikasi gagal start. Cek log: journalctl -u $APP_NAME"
fi

if systemctl is-active --quiet nginx; then
    log "✅ Nginx berjalan!"
else
    error "❌ Nginx gagal start"
fi

# 18. Output Info
echo ""
echo "=========================================="
echo "  🎉 DEPLOYMENT SELESAI!"
echo "=========================================="
echo ""
echo "🌐 Website: https://$DOMAIN"
echo "📁 App Dir: $APP_DIR"
echo "📊 Database: PostgreSQL (kasirtoko)"
echo ""
echo "🔧 Commands:"
echo "  Check status:  systemctl status $APP_NAME"
echo "  View logs:     journalctl -u $APP_NAME -f"
echo "  Restart app:   systemctl restart $APP_NAME"
echo "  Backup DB:     $APP_DIR/backup.sh"
echo ""
echo "🔐 Default Login:"
echo "  Username: pemilik"
echo "  Password: pemilik123"
echo ""
echo "⚠️  IMPORTANT:"
echo "  1. Ganti password default segera!"
echo "  2. Backup database secara berkala"
echo "  3. Keep server updated: apt update && apt upgrade"
echo ""
echo "=========================================="

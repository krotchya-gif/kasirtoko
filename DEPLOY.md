# 🚀 Panduan Deploy KasirToko

Panduan lengkap untuk deploy aplikasi KasirToko ke berbagai platform.

---

## 📋 Daftar Isi

1. [Deploy ke Vercel (Serverless)](#1-deploy-ke-vercel-serverless)
2. [Deploy dengan Docker](#2-deploy-dengan-docker)
3. [Deploy ke VPS (Ubuntu)](#3-deploy-ke-vps-ubuntu)
4. [Deploy ke Railway/Render](#4-deploy-ke-railwayrender)
5. [Konfigurasi Environment Variables](#konfigurasi-environment-variables)

---

## 1. Deploy ke Vercel (Serverless)

Vercel adalah pilihan terbaik untuk deploy gratis dengan PostgreSQL.

### 1.1 Setup Akun & Database

1. Buat akun [Vercel](https://vercel.com)
2. Buat akun [Neon PostgreSQL](https://neon.tech) atau [Supabase](https://supabase.com)
3. Dapatkan connection string PostgreSQL

### 1.2 Install Vercel CLI

```bash
npm i -g vercel
```

### 1.3 Deploy

```bash
# Login ke Vercel
vercel login

# Deploy
vercel --prod
```

Atau gunakan Git:

```bash
# Push ke GitHub, lalu import project di Vercel dashboard
```

### 1.4 Environment Variables

Set di Vercel Dashboard → Project Settings → Environment Variables:

```
POSTGRES_URL=postgresql://user:password@host/database
SECRET_KEY=your-secret-key-min-32-characters
```

---

## 2. Deploy dengan Docker

### 2.1 Build & Run Local

```bash
# Build image
docker build -t kasirtoko:latest .

# Run container
docker run -d \
  -p 5000:5000 \
  -e SECRET_KEY=your-secret-key \
  -v kasirtoko-data:/app/data \
  --name kasirtoko \
  kasirtoko:latest
```

### 2.2 Docker Compose (Recommended)

```bash
# Dengan PostgreSQL
docker-compose up -d
```

### 2.3 Deploy ke Docker Hub

```bash
# Login
docker login

# Tag
docker tag kasirtoko:latest yourusername/kasirtoko:latest

# Push
docker push yourusername/kasirtoko:latest
```

---

## 3. Deploy ke VPS (Ubuntu)

### 3.1 Setup VPS Baru

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install -y python3 python3-pip python3-venv nginx supervisor

# Install PostgreSQL (optional)
sudo apt install -y postgresql postgresql-contrib
```

### 3.2 Setup Aplikasi

```bash
# Buat user baru
sudo useradd -m -s /bin/bash kasirtoko
sudo usermod -aG sudo kasirtoko

# Login sebagai kasirtoko
sudo su - kasirtoko

# Clone repository
git clone https://github.com/yourusername/kasirtoko.git
cd kasirtoko

# Setup virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Setup environment
cp .env.example .env
nano .env  # Edit konfigurasi
```

### 3.3 Konfigurasi Systemd

Buat service file:

```bash
sudo nano /etc/systemd/system/kasirtoko.service
```

Isi:

```ini
[Unit]
Description=KasirToko Flask App
After=network.target

[Service]
User=kasirtoko
Group=kasirtoko
WorkingDirectory=/home/kasirtoko/kasirtoko
Environment="PATH=/home/kasirtoko/kasirtoko/venv/bin"
Environment="SECRET_KEY=your-secret-key"
Environment="POSTGRES_URL=postgresql://..."  # Optional
ExecStart=/home/kasirtoko/kasirtoko/venv/bin/gunicorn -w 4 -b 127.0.0.1:5000 app:app
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable & start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable kasirtoko
sudo systemctl start kasirtoko
sudo systemctl status kasirtoko
```

### 3.4 Konfigurasi Nginx

```bash
sudo nano /etc/nginx/sites-available/kasirtoko
```

Isi:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static {
        alias /home/kasirtoko/kasirtoko/static;
        expires 30d;
    }
}
```

Enable:

```bash
sudo ln -s /etc/nginx/sites-available/kasirtoko /etc/nginx/sites-enabled
sudo nginx -t
sudo systemctl restart nginx
```

### 3.5 Setup SSL (Let's Encrypt)

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

---

## 4. Deploy ke Railway/Render

### 4.1 Railway

1. Buat akun [Railway](https://railway.app)
2. New Project → Deploy from GitHub repo
3. Add PostgreSQL plugin
4. Environment variables otomatis ter-set

### 4.2 Render

1. Buat akun [Render](https://render.com)
2. New Web Service → Connect GitHub
3. Pilih repo KasirToko
4. Settings:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`
5. Add PostgreSQL database
6. Copy connection string ke environment variables

---

## Konfigurasi Environment Variables

### Required

| Variable | Deskripsi | Contoh |
|----------|-----------|--------|
| `SECRET_KEY` | Kunci enkripsi session | `your-secret-key-min-32-chars` |

### Optional (untuk PostgreSQL)

| Variable | Deskripsi | Contoh |
|----------|-----------|--------|
| `POSTGRES_URL` | Connection string PostgreSQL | `postgresql://user:pass@host/db` |
| `POSTGRES_PRISMA_URL` | Alternative URL format | `postgresql://user:pass@host/db` |

### File .env.example

```bash
# Flask Secret Key (WAJIB)
SECRET_KEY=ganti-dengan-random-string-panjang-minimal-32-karakter

# Database (Opsional - default SQLite)
# POSTGRES_URL=postgresql://username:password@hostname/database

# Flask Environment
FLASK_ENV=production
FLASK_DEBUG=0
```

---

## 🔧 Troubleshooting Deploy

### Database Locked (SQLite)

```bash
# Hapus lock file
rm kasirtoko.db-shm kasirtoko.db-wal
```

### Permission Denied

```bash
# Fix permission
sudo chown -R kasirtoko:kasirtoko /home/kasirtoko/kasirtoko
sudo chmod -R 755 /home/kasirtoko/kasirtoko
```

### Gunicorn Workers

```bash
# Formula: (2 x CPU cores) + 1
# Untuk VPS 1 CPU: -w 3
# Untuk VPS 2 CPU: -w 5
```

### Static Files tidak ter-load

```bash
# Pastikan nginx config benar
location /static {
    alias /path/to/kasirtoko/static;
}
```

---

## 📱 Akses Mobile setelah Deploy

Setelah deploy, untuk **scan barcode** di HP:

### Opsi 1: HTTPS (Recommended)
Domain dengan SSL otomatis support kamera.

### Opsi 2: ngrok (Development)
```bash
ngrok http 5000
```

### Opsi 3: ADB Reverse (Local dev)
```bash
adb reverse tcp:5000 tcp:5000
# Buka localhost:5000 di HP
```

---

## 🔄 Backup & Restore Database

### SQLite

```bash
# Backup
cp kasirtoko.db kasirtoko-backup-$(date +%Y%m%d).db

# Restore
cp kasirtoko-backup-20240317.db kasirtoko.db
```

### PostgreSQL

```bash
# Backup
pg_dump $POSTGRES_URL > backup.sql

# Restore
psql $POSTGRES_URL < backup.sql
```

---

*Terakhir diperbarui: Maret 2026*

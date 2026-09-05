"""Konfigurasi KasirToko — pindahan murni dari app.py (split Fase 2).

ROOT_DIR menunjuk ke root project (sejajar app.py), BUKAN folder paket,
agar DB_PATH/backups/template tetap di lokasi semula.
"""
import os

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(ROOT_DIR, 'kasirtoko.db')
BACKUP_DIR = os.path.join(ROOT_DIR, 'backups')

# Database configuration - PostgreSQL for Vercel, SQLite for local
POSTGRES_URL = (os.environ.get('POSTGRES_URL')
                or os.environ.get('DATABASE_URL')
                or os.environ.get('POSTGRES_PRISMA_URL'))
USE_POSTGRES = bool(POSTGRES_URL)

SECRET_KEY = os.environ.get('SECRET_KEY')
FLASK_ENV_IS_PROD = os.environ.get('FLASK_ENV') == 'production'

MAX_CONTENT_LENGTH = 2 * 1024 * 1024  # P2-6: batas upload 2 MB

# P2-1: batasi CORS ke origin aplikasi sendiri (default localhost).
ALLOWED_ORIGINS = [o.strip() for o in os.environ.get(
    'APP_URL', 'http://localhost:5000,http://127.0.0.1:5000').split(',') if o.strip()]

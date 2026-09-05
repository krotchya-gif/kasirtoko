"""KasirToko package — application factory (split Fase 2).

Semua logika tetap di modul masing-masing; file ini hanya merakit aplikasi.
"""
import os
from datetime import timedelta

from flask import Flask
from flask_cors import CORS

from . import config


def create_app():
    app = Flask(__name__,
                template_folder=os.path.join(config.ROOT_DIR, 'templates'),
                static_folder=os.path.join(config.ROOT_DIR, 'static'))
    # P2-6: batas ukuran upload (2 MB) agar CSV raksasa tidak menghabiskan memori
    app.config['MAX_CONTENT_LENGTH'] = config.MAX_CONTENT_LENGTH
    # P2-1: batasi CORS ke origin aplikasi sendiri (default localhost).
    # Set APP_URL=https://toko-anda.com di production bila diakses lintas origin.
    CORS(app, origins=config.ALLOWED_ORIGINS, supports_credentials=True)

    # Session — ganti SECRET_KEY di environment saat production (P2-2: fail-fast)
    if not config.SECRET_KEY and config.FLASK_ENV_IS_PROD:
        raise RuntimeError('SECRET_KEY wajib diset di production')
    app.secret_key = config.SECRET_KEY or 'dev-only-insecure-change-me'
    app.permanent_session_lifetime = timedelta(days=30)

    from .auth import too_large, not_found
    from .routes.pages import require_login
    app.before_request(require_login)
    app.register_error_handler(413, too_large)
    app.register_error_handler(404, not_found)

    from .routes import (pages, admin, produk, transaksi, piutang, kas,
                         laporan, pelanggan, pengguna, struk)
    for _bpmod in (pages, admin, produk, transaksi, piutang, kas,
                   laporan, pelanggan, pengguna, struk):
        app.register_blueprint(_bpmod.bp)

    # ── INIT DATABASE (SAAT IMPORT/STARTUP) ──
    from .models_init import init_db, warn_default_credentials
    try:
        init_db()
        print("[OK] Database initialized")
    except Exception as e:
        print(f"[WARN] Database init error (will retry on first request): {e}")
        import traceback
        print(traceback.format_exc())
        from .routes import pages as _pages
        _pages._db_init_error = e

    try:
        warn_default_credentials()
    except Exception as e:
        print(f"[WARN] Cek kredensial default gagal: {e}")

    return app

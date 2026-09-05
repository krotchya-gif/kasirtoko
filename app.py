"""
KasirToko — Backend Flask + SQLite/PostgreSQL
Jalankan: python app.py
Buka browser: http://localhost:5000

Pintu masuk aplikasi (split Fase 2). Seluruh logika ada di paket kasirtoko/.
Kompatibilitas: `from app import app` (Vercel api/index.py) tetap jalan.
"""

from kasirtoko import create_app

app = create_app()

# ─────────────────────────────────────
#  JALANKAN SERVER (LOCAL DEV)
# ─────────────────────────────────────
if __name__ == '__main__':
    print("\n" + "="*50)
    print("  [TOKO] KasirToko v2.3.0 — Python + Flask + SQLite")
    print("="*50)
    print("  * Fitur: Scan Barcode | Printer App | Multi User")
    print("")
    # Get IP address for mobile access
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
    except Exception:
        ip = "localhost"
    print("  [PC] Laptop:     http://localhost:5000")
    print(f"  [HP] Mobile:     http://{ip}:5000")
    print("")
    print("  [i]  Scan barcode butuh HTTPS/localhost (gunakan IP di atas)")
    print("  [OFF]   Tekan Ctrl+C untuk menghentikan server")
    print("="*50 + "\n")
    app.run(debug=False, host='0.0.0.0', port=5000)

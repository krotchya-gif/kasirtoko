# 🏪 KasirToko

Aplikasi kasir UMKM berbasis web dengan Python + Flask + SQLite.

[![Version](https://img.shields.io/badge/version-v1.11.3-blue.svg)](CHANGELOG.md)
[![Python](https://img.shields.io/badge/python-3.9+-green.svg)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-orange.svg)](LICENSE)

## ✨ Fitur Utama

| Fitur | Keterangan |
|-------|------------|
| 🛒 **Kasir** | Transaksi dengan keranjang belanja, diskon, metode pembayaran |
| 📱 **Scan Barcode** | Input produk via kamera HP (Chrome Android) |
| 🖨️ **Cetak Struk** | Thermal printer support: USB, Bluetooth, PDF |
| 📊 **Laporan** | Harian, rentang tanggal, top produk, stok rendah |
| 👥 **Pelanggan** | Manajemen pelanggan & riwayat belanja |
| 🔐 **Multi User** | Role-based: Pemilik (full) & Karyawan (kasir) |
| 💰 **Dompet/Kas** | Catat pemasukan & pengeluaran manual |
| 🔒 **Tutup Kasir** | End-of-day closing dengan approval |
| 📤 **Import/Export** | CSV produk |

## 🚀 Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Jalankan aplikasi
python app.py

# 3. Buka browser di laptop
http://localhost:5000

# 4. Akses dari HP (dalam WiFi yang sama)
# Lihat IP yang muncul di terminal, contoh:
http://192.168.1.12:5000
```

### 📱 Untuk Scan Barcode di HP:
Scan barcode memerlukan **HTTPS** atau **localhost**.
Gunakan salah satu metode:
- **ADB Reverse**: `adb reverse tcp:5000 tcp:5000` lalu buka `localhost:5000`
- **ngrok**: `ngrok http 5000` (dapat URL HTTPS)
- **LocalTunnel**: `lt --port 5000`

## 🔐 Login Default

| Username | Password | Role |
|----------|----------|------|
| `pemilik` | `pemilik123` | Full akses |
| `karyawan` | `karyawan123` | Kasir only |

## 🖨️ Printer Support

| Metode | Platform | Keterangan |
|--------|----------|------------|
| Browser Print | Semua | Via `window.print()` |
| RawBT | Android | Bluetooth thermal |
| Serial/USB | Chrome Desktop | ESC/POS via Web Serial API |
| PDF | Semua | Generate & share/download |
| **Custom App** | Android | Integrasi app printer sendiri |

## 📱 Scan Barcode

- **Browser**: Chrome/Edge Android (via BarcodeDetector API)
- **Format**: EAN-13, EAN-8, CODE-39, CODE-128, UPC-A, UPC-E, QR Code
- **Fallback**: Input manual jika kamera tidak tersedia

## 📋 Dokumentasi

- [CARA-PAKAI.md](CARA-PAKAI.md) — Panduan lengkap penggunaan
- [CHANGELOG.md](CHANGELOG.md) — Riwayat perubahan & versi

## 🗄️ Database

SQLite dengan tabel:
- `produk` — Data produk (dengan barcode)
- `transaksi` — Transaksi penjualan
- `transaksi_item` — Detail item
- `kas` — Arus kas manual
- `tutup_kasir` — Riwayat tutup kasir
- `pelanggan` — Data pelanggan
- `pengaturan` — Konfigurasi toko
- `pengguna` — Akun login

## 📝 Changelog

### v1.11.2 (2026-03-16)
- ✅ Fix scan barcode dengan library html5-qrcode (support lebih banyak browser)

### v1.11.0 (2026-03-16)
- ✅ Scan barcode via kamera HP
- ✅ Field barcode di produk

### v1.10.0 (2026-03-16)
- ✅ Pilihan aplikasi printer mobile (RawBT/Custom/PrintHand)
- ✅ Custom URI scheme untuk integrasi app sendiri

## 📄 License

MIT License — bebas digunakan untuk personal maupun komersial.

---

<div align="center">
  <sub>Dibuat dengan ❤️ untuk UMKM Indonesia</sub>
</div>

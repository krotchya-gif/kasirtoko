# 🏪 KasirToko

Aplikasi kasir UMKM berbasis web dengan Python + Flask + SQLite. Support multi-platform: Desktop, Tablet, dan Mobile.

[![Version](https://img.shields.io/badge/version-v2.0.0-blue.svg)](CHANGELOG.md)
[![Python](https://img.shields.io/badge/python-3.9+-green.svg)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-orange.svg)](LICENSE)

## ✨ Fitur Utama

| Fitur | Keterangan |
|-------|------------|
| 🛒 **Kasir** | Transaksi dengan keranjang belanja, diskon, metode pembayaran |
| 📱 **Scan Barcode** | Input produk via kamera HP (Chrome Android) |
| 🏷️ **Barcode Generator** | Generate & cetak label barcode (EAN13/Code128) |
| 🖨️ **Cetak Struk** | Thermal printer support: USB, Bluetooth, PDF |
| 📊 **Grafik Penjualan** | Visualisasi data (Chart.js) |
| 📄 **Export PDF** | Laporan dalam format PDF |
| 🗑️ **Void Transaksi** | Batalkan transaksi dengan pengembalian stok |
| 📦 **Riwayat Stok** | Tracking perubahan stok (masuk/keluar/adjust) |
| ⚖️ **Adjust Stok** | Penyesuaian stok dengan alasan |
| 📊 **Laporan** | Harian, rentang tanggal, top produk, stok rendah |
| 👥 **Pelanggan** | Manajemen pelanggan & riwayat belanja |
| 🔐 **Multi User** | Role-based: Pemilik (full) & Karyawan (kasir) |
| 💰 **Dompet/Kas** | Catat pemasukan & pengeluaran manual |
| 🔒 **Tutup Kasir** | End-of-day closing dengan approval pemilik |
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

## 🎯 Fitur Baru v2.0.0

### 🗑️ Void Transaksi
- Batalkan transaksi yang salah
- Stok otomatis dikembalikan
- Bisa di-restore jika perlu
- Alasan void wajib diisi

### 📦 Manajemen Stok Lengkap
- **Riwayat Stok Log**: Lihat semua perubahan stok
- **Adjust Stok**: Penyesuaian dengan alasan (rusak, expired, dll)
- **Tracking**: Masuk, keluar, void, adjust

### 📊 Grafik Penjualan
- Chart.js integration
- 3 tipe: Harian, Mingguan, Bulanan
- Dual axis: Omzet & Jumlah Transaksi

### 📄 Export PDF
- Laporan dalam format PDF
- Desain gelap (sesuai tema)
- ReportLab integration

### 🏷️ Barcode Generator
- Generate barcode otomatis (13 digit)
- Format: EAN13 & Code128
- Cetak label barcode (sheet PDF)
- Preview individual

## 🖨️ Printer Support

| Metode | Platform | Keterangan |
|--------|----------|------------|
| Browser Print | Semua | Via `window.print()` |
| RawBT | Android | Bluetooth thermal |
| Serial/USB | Chrome Desktop | ESC/POS via Web Serial API |
| PDF | Semua | Generate & share/download |
| **Custom App** | Android | Integrasi app printer sendiri |

## 📱 Scan Barcode

- **Browser**: Chrome/Edge Android (via html5-qrcode)
- **Format**: EAN-13, EAN-8, CODE-39, CODE-128, UPC-A, UPC-E, QR Code
- **Fallback**: Input manual jika kamera tidak tersedia

## 📋 Dokumentasi

- [DOKUMENTASI.md](DOKUMENTASI.md) — Dokumentasi teknis lengkap
- [CARA-PAKAI.md](CARA-PAKAI.md) — Panduan penggunaan
- [CHANGELOG.md](CHANGELOG.md) — Riwayat perubahan

## 🗄️ Database

SQLite dengan tabel:
- `produk` — Data produk (dengan barcode)
- `transaksi` — Transaksi penjualan (dengan status void)
- `transaksi_item` — Detail item
- `kas` — Arus kas manual
- `tutup_kasir` — Riwayat tutup kasir
- `pelanggan` — Data pelanggan
- `pengaturan` — Konfigurasi toko
- `pengguna` — Akun login
- `stok_log` — **(NEW)** Riwayat perubahan stok

## 🛠️ Tech Stack

| Komponen | Teknologi |
|----------|-----------|
| Backend | Flask 3.0+ (Python) |
| Database | SQLite (dev) / PostgreSQL (prod) |
| Template | Jinja2 |
| Styling | Custom CSS (Dark/Light mode) |
| Charts | Chart.js 4.4.1 |
| PDF Export | ReportLab 4.1.0 |
| Barcode | python-barcode 0.15.1 |
| QR Scanner | html5-qrcode 2.3.8 |

## 🚀 Deploy

### Quick Deploy

```bash
# Deploy ke Vercel (Gratis + PostgreSQL)
./deploy.sh vercel

# Deploy dengan Docker
./deploy.sh docker

# Deploy ke VPS Ubuntu
./deploy.sh vps kasir.tokoku.com

# Run local
./deploy.sh local
```

### Deploy Manual

**Vercel (Recommended):**
```bash
npm i -g vercel
vercel --prod
```

**Docker:**
```bash
docker-compose up -d
```

**VPS Ubuntu:**
```bash
bash deploy/deploy-vps.sh kasir.tokoku.com
```

📖 Lihat [DEPLOY.md](DEPLOY.md) untuk panduan lengkap.

## 📝 Changelog

### v2.0.0 (2026-03-17)
- ✅ **Void Transaksi** dengan pengembalian stok
- ✅ **Riwayat Stok Log** - Tracking perubahan stok
- ✅ **Adjust Stok Manual** dengan alasan
- ✅ **Grafik Penjualan** (Chart.js)
- ✅ **Export PDF Laporan**
- ✅ **Barcode Generator** & Print Sheet
- ✅ Restore transaksi yang di-void

### v1.11.3 (2026-03-16)
- ✅ Fix database init dengan kolom void & stok_log
- ✅ Update dokumentasi

### v1.11.0 (2026-03-16)
- ✅ Scan barcode via kamera HP
- ✅ Field barcode di produk

## 📄 License

MIT License — bebas digunakan untuk personal maupun komersial.

---

<div align="center">
  <sub>Dibuat dengan ❤️ untuk UMKM Indonesia</sub>
</div>

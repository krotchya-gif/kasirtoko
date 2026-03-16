# 🏪 KasirToko — Python + Flask + SQLite

Aplikasi kasir UMKM berbasis web yang berjalan di laptop sendiri.
Data tersimpan permanen di file `kasirtoko.db` (SQLite).

---

## ✅ CARA INSTALL & JALANKAN

### Langkah 1 — Install Python
Pastikan Python sudah terinstall.
Cek dengan buka Terminal / Command Prompt, ketik:
```
python --version
```
Kalau belum ada, download di: https://python.org/downloads
Pilih versi 3.9 ke atas. Centang "Add Python to PATH" saat install.

---

### Langkah 2 — Buka folder ini di Terminal

**Windows:**
- Buka folder `kasirtoko`
- Klik kanan di area kosong → "Open in Terminal" atau "Git Bash"
- Atau buka Command Prompt, ketik: `cd C:\path\ke\folder\kasirtoko`

**Mac/Linux:**
- Buka Terminal
- Ketik: `cd /path/ke/folder/kasirtoko`

---

### Langkah 3 — Install library yang dibutuhkan
Ketik perintah ini di Terminal:
```
pip install -r requirements.txt
```
Tunggu sampai selesai (butuh internet, cukup sekali saja).

---

### Langkah 4 — Jalankan aplikasi
```
python app.py
```

Akan muncul tulisan:
```
==================================================
  🏪 KasirToko — Python + Flask + SQLite
==================================================
  💻 Laptop:     http://localhost:5000
  📱 Mobile:     http://192.168.1.x:5000  (IP Anda)
==================================================
```

---

### Langkah 5 — Buka di browser

**Di Laptop:**
Buka browser, ketik:
```
http://localhost:5000
```

**Di HP/Mobile (Dalam Network Yang Sama):**
Pastikan HP dan laptop terhubung ke **WiFi yang sama**.
Ketik IP yang muncul di terminal, contoh:
```
http://192.168.1.12:5000
```

> **⚠️ Penting:** Fitur **Scan Barcode** memerlukan **HTTPS** atau **localhost**.
> Jika akses via IP (http://192.168.x.x), scan barcode **tidak akan berfungsi**.
> Lihat solusi di bawah untuk mengatasi ini.

🎉 Aplikasi kasir siap digunakan!

---

## 📱 AKSES DARI HP UNTUK SCAN BARCODE

Scan barcode memerlukan **HTTPS** atau **localhost** (security requirement browser).

### Opsi 1: ADB Reverse (Direkomendasikan untuk Development)

Cocok untuk testing scan barcode saat development:

**Langkah 1 — Install ADB (Android Debug Bridge):**
- Download Platform Tools: https://developer.android.com/studio/releases/platform-tools
- Extract dan tambahkan ke PATH

**Langkah 2 — Hubungkan HP ke Laptop:**
- Aktifkan **Developer Options** di HP (tap Build Number 7x)
- Aktifkan **USB Debugging**
- Hubungkan HP ke laptop via USB
- Buka CMD/PowerShell, ketik:
```
adb devices
```
Pastikan HP terdeteksi.

**Langkah 3 — Port Forwarding:**
```
adb reverse tcp:5000 tcp:5000
```

**Langkah 4 — Buka di HP:**
Buka Chrome di HP, ketik:
```
http://localhost:5000
```

> ✅ Sekarang scan barcode akan berfungsi!

---

### Opsi 2: Ngrok (Tunneling Internet)

Cocok untuk akses dari mana saja dengan HTTPS:

**Langkah 1 — Install ngrok:**
```
# Windows (dengan Chocolatey)
choco install ngrok

# Atau download dari https://ngrok.com/download
```

**Langkah 2 — Daftar & Auth:**
- Daftar di https://ngrok.com
- Copy authtoken
- Jalankan:
```
ngrok authtoken YOUR_TOKEN
```

**Langkah 3 — Jalankan Tunnel:**
```
ngrok http 5000
```

**Langkah 4 — Buka URL HTTPS:**
Akan muncul URL seperti:
```
https://abc123.ngrok-free.app
```

Buka URL tersebut di HP. ✅ Scan barcode akan berfungsi!

---

### Opsi 3: LocalTunnel (Gratis, Alternatif Ngrok)

```
# Install
global add localtunnel

# Jalankan
lt --port 5000
```

Buka URL yang diberikan di HP.

---

### Opsi 4: Deploy ke Server (Production)

Untuk penggunaan nyata, deploy ke server dengan domain + SSL:
- VPS (DigitalOcean, AWS, dll)
- Railway/Render (free tier)
- Lihat folder `deploy/` untuk panduan Ubuntu + Nginx

---

## 🔐 LOGIN PERTAMA KALI

Saat pertama buka, akan muncul halaman **Login**.

| Username | Password | Role |
|----------|----------|------|
| `pemilik` | `pemilik123` | Pemilik (akses penuh) |
| `karyawan` | `karyawan123` | Karyawan (kasir only) |

> **Penting:** Ganti password default setelah pertama kali login!
> Caranya: klik nama pengguna di pojok kanan atas → **Ganti Password**

**Hak Akses:**
- **Pemilik** — semua fitur: produk, laporan, dompet, tutup kasir, pengaturan, manajemen tim
- **Karyawan** — kasir, riwayat transaksi, pelanggan, proses tutup kasir

---

## 🖨️ CETAK KE PRINTER THERMAL

Di modal sukses transaksi, tersedia beberapa tombol cetak sesuai perangkat:

| Tombol | Platform | Keterangan |
|--------|----------|------------|
| 🖨️ Cetak | Semua | Print via browser (window.print) |
| 📱 RawBT | Android | Print Bluetooth tanpa dialog |
| 🔌 Serial/USB | Chrome Desktop | Print USB/COM port langsung |
| 📤 PDF | Semua | Generate PDF & share/download |

---

### 🖨️ Printer USB (Windows/Mac/Linux)

1. Pasang printer thermal via USB
2. Install driver printer (jika ada), atau gunakan sebagai "Generic / Text Only"
3. Set printer thermal sebagai **printer default**
4. Buka aplikasi di **Google Chrome**
5. Saat cetak struk → tombol **🖨️ Cetak** → pilih printer thermal
6. Pastikan ukuran kertas di Pengaturan Toko sesuai (58mm / 80mm)

**Tips Chrome (tanpa dialog print):**
Buka Chrome dengan flag kiosk-printing:
```
chrome.exe --kiosk-printing
```
Struk langsung tercetak ke printer default tanpa dialog.

---

### 🔌 Serial/USB via Web Serial API (Chrome Desktop)

Tombol **🔌 Serial/USB** tersedia otomatis jika browser mendukung Web Serial API (Google Chrome desktop).

1. Pasang printer thermal via USB
2. Buka aplikasi di **Google Chrome** (bukan Firefox/Safari)
3. Klik 🔌 Serial/USB → pertama kali: pilih port COM dari daftar
4. Port diingat otomatis untuk sesi berikutnya
5. Struk tercetak langsung ke printer (format ESC/POS)

> **Catatan:** Web Serial API hanya tersedia di Chrome/Edge desktop. Tidak tersedia di Firefox, Safari, atau browser mobile.

---

### 📱 Printer Bluetooth Android (RawBT / Custom App)

1. Install aplikasi **RawBT** (atau aplikasi printer custom Anda) dari Google Play Store
2. Buka RawBT → sambungkan ke printer Bluetooth thermal
3. Buka KasirToko di **browser Android** (Chrome)
4. Saat transaksi selesai → tombol **📱 RawBT**
5. Struk langsung tercetak ke printer tanpa dialog

**Printer Bluetooth yang kompatibel:** RPP02N, POS-5805, Xprinter, GOOJPRT, dll.

#### Mengganti Aplikasi Printer:
1. Buka **⚙️ Pengaturan Toko**
2. Pilih **📱 Aplikasi Printer Mobile**:
   - **RawBT** (default)
   - **Aplikasi Custom** — untuk app dengan scheme `myprinter`
   - **PrintHand** — untuk app PrintHand
   - **Lainnya** — input custom URI scheme
3. Simpan

> **Untuk Developer:** Bisa integrasikan aplikasi printer custom (Flutter, native, dll) dengan mendaftarkan URI scheme di Android Manifest. Lihat dokumentasi teknis untuk detailnya.
> 
> **Catatan:** RawBT adalah aplikasi gratis, mendukung printer Bluetooth Classic maupun BLE.

---

### 📤 Cetak via PDF (Semua Platform)

1. Saat transaksi selesai → tombol **📤 PDF**
2. PDF dibuat otomatis sesuai ukuran kertas (58mm / 80mm)
3. Android/iOS: muncul share sheet → pilih app printer atau simpan
4. Desktop: PDF didownload otomatis

---

## 📱 SCAN BARCODE (INPUT PRODUK VIA KAMERA)

Kasir bisa menambahkan produk ke keranjang dengan scan barcode via kamera HP.

### Cara Scan di Kasir:
1. Di halaman kasir, tap tombol **🔢 Scan** (sebelah kolom pencarian)
2. Izinkan akses kamera saat browser meminta
3. Arahkan kamera ke barcode produk
4. Produk otomatis terdeteksi dan masuk ke keranjang

### Cara Scan di Form Produk:
1. Saat tambah/edit produk, tap tombol **📷 Scan** di sebelah field barcode
2. Scan barcode produk
3. Nomor barcode otomatis terisi di form

### Persyaratan Scan Barcode:

| Syarat | Keterangan |
|--------|------------|
| **Browser** | Chrome Android, Edge Android, Safari iOS (support lebih luas) |
| **Library** | html5-qrcode (auto-load dari CDN) |
| **Koneksi** | HTTPS atau localhost (wajib untuk akses kamera) |
| **Izin** | Harus izinkan akses kamera saat diminta |
| **Kamera** | Kamera belakang (environment) |

### Troubleshooting Scan:

**"Browser tidak support scan"**
→ Gunakan **Chrome Android** atau **Edge Android**
→ Firefox, Safari, dan browser bawaan HP belum support

**"Izin kamera ditolak"**
→ Tap ikon 🔑 di address bar Chrome → Izinkan kamera
→ Atau buka Setting Chrome → Site Settings → Camera → Izinkan

**"Kamera tidak ditemukan"**
→ Pastikan kamera belakang HP tidak rusak
→ Tutup aplikasi lain yang pakai kamera

**"HTTPS diperlukan"**
→ Akses kasirtoko via **localhost** (untuk development)
→ Atau deploy dengan **HTTPS** (untuk production)

### Input Manual:
Kalau kamera tidak bisa digunakan, ketik barcode manual di bagian **Input Manual** di bawah modal scanner.

---

## 💳 METODE PEMBAYARAN

Saat proses bayar, kasir bisa memilih metode:
- **💵 Tunai** — input nominal bayar & hitung kembalian otomatis
- **🏦 Transfer** — nominal bayar otomatis = total, kembalian tidak ditampilkan
- **📱 QRIS** — nominal bayar otomatis = total, kembalian tidak ditampilkan

Metode tersimpan di database & tampil di struk.

---

## 🔒 TUTUP KASIR (END OF DAY)

Fitur untuk menutup shift penjualan dan mencatat pemasukan ke Kas/Dompet.

**Alur:**
1. Karyawan klik **🔒 Tutup Kasir** (topbar/drawer)
2. Preview transaksi yang belum ditutup tampil (breakdown per metode)
3. Karyawan isi catatan (opsional) → klik **Proses Tutup Kasir**
4. Status: *pending*, menunggu konfirmasi pemilik
5. Pemilik buka **🔒 Tutup Kasir** → lihat daftar pending → klik **✅ Konfirmasi**
6. Otomatis buat entri di Kas/Dompet (terpisah per metode: Tunai, Transfer, QRIS)

**Catatan:**
- Bisa tutup beberapa kali sehari (hanya transaksi belum ditutup yang ikut)
- Badge `!` merah muncul di tombol Tutup Kasir jika ada pending konfirmasi
- Setelah dikonfirmasi, transaksi yang sudah ditutup tidak ikut di tutup kasir berikutnya

---

## 📁 STRUKTUR FILE

```
kasirtoko/
├── app.py              ← Program utama (Flask backend)
├── requirements.txt    ← Daftar library Python
├── kasirtoko.db        ← Database SQLite (dibuat otomatis)
├── CARA-PAKAI.md       ← Panduan ini
├── CHANGELOG.md        ← Riwayat versi & perubahan
└── templates/
    ├── index.html      ← Tampilan aplikasi (frontend)
    └── login.html      ← Halaman login
```

---

## 💾 DATABASE

File `kasirtoko.db` dibuat otomatis saat pertama kali dijalankan.

| Tabel | Keterangan |
|-------|------------|
| `produk` | Data produk & stok (plus barcode) |
| `transaksi` | Header transaksi penjualan |
| `transaksi_item` | Detail item per transaksi |
| `kas` | Arus kas manual (dompet) |
| `tutup_kasir` | Riwayat tutup kasir harian |
| `pelanggan` | Data pelanggan |
| `pengaturan` | Konfigurasi toko (key-value) |
| `pengguna` | Akun login & role |

**Backup:** Cukup copy file `kasirtoko.db` ke tempat lain.
**Pindah laptop:** Copy seluruh folder `kasirtoko` ke laptop baru,
install Python & library, lalu jalankan seperti biasa.

---

## 🛑 CARA MENGHENTIKAN

Tekan `Ctrl + C` di Terminal.

---

## ❓ TROUBLESHOOTING

**"python tidak dikenal"**
→ Python belum terinstall atau belum ditambahkan ke PATH.
→ Coba ketik `python3 app.py` (untuk Mac/Linux)

**"pip tidak dikenal"**
→ Coba: `python -m pip install -r requirements.txt`

**Port 5000 sudah dipakai**
→ Edit baris terakhir di `app.py`, ganti port:
   `app.run(debug=False, host='0.0.0.0', port=5001)`
→ Lalu buka: http://localhost:5001

**Aplikasi lambat saat pertama kali**
→ Normal, browser loading font dari internet.
→ Setelah itu sudah cepat.

**Tombol 🔌 Serial/USB tidak muncul**
→ Web Serial API hanya tersedia di Chrome/Edge versi terbaru (desktop).
→ Pastikan menggunakan Google Chrome, bukan Firefox atau Safari.
→ Coba tombol 📤 PDF sebagai alternatif.

**Printer USB tidak terdeteksi saat Cetak**
→ Pastikan printer sudah diset sebagai printer default di sistem.
→ Coba cetak halaman test dari pengaturan printer Windows/Mac dulu.
→ Pastikan ukuran kertas di Pengaturan Toko sudah sesuai (58mm/80mm).

**RawBT tidak terbuka / printer tidak cetak**
→ Pastikan aplikasi RawBT sudah terinstall & printer sudah dipasang di RawBT.
→ Pastikan Bluetooth aktif & printer sudah di-pair di Android.
→ Coba tutup & buka ulang RawBT, lalu coba lagi dari KasirToko.

**Tidak bisa akses dari HP (http://192.168.x.x:5000)**
→ Pastikan HP dan laptop di **WiFi yang sama**
→ Pastikan **Windows Firewall** tidak memblokir Python (buka Port 5000)
→ Cek IP address laptop dengan `ipconfig` (Windows) atau `ifconfig` (Mac/Linux)
→ Coba akses dari laptop dulu: `http://localhost:5000`
→ Restart aplikasi dan coba lagi

**Tombol 🔢 Scan tidak berfungsi / kamera tidak muncul**
→ Pastikan menggunakan **Chrome Android**, **Edge Android**, atau **Safari iOS**
→ **WAJIB HTTPS atau localhost** (kamera tidak jalan via http://192.168.x.x!)
→ **Solusi:** Gunakan **ADB Reverse** atau **ngrok** (lihat panduan "Akses dari HP untuk Scan Barcode")
→ Tap ikon 🔑 di address bar Chrome → Pastikan kamera diizinkan
→ Tunggu library html5-qrcode load dari CDN (butuh koneksi internet)
→ Gunakan **input manual** di bagian bawah modal sebagai alternatif

**Scan barcode tidak menemukan produk**
→ Pastikan produk sudah ditambahkan dengan barcode yang sesuai
→ Cek di **⚙️ Kelola Produk** apakah barcode sudah terisi
→ Bisa juga ketik barcode manual di modal scanner untuk testing

**Tombol 📷 Scan di form produk tidak jalan**
→ Sama dengan troubleshooting di atas (kamera butuh HTTPS/localhost)
→ Bisa ketik barcode manual di field barcode tanpa scan

**Lupa password**
→ Minta pemilik reset password via menu 👥 Tim.
→ Atau edit database langsung (butuh SQLite tools).

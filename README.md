# Photo Station - Digital Display & Photobooth System

Sistem informasi digital terintegrasi dengan photobooth untuk Raspberry Pi 5.

## Fitur

- 📺 **Display Digital** - Tampilan agenda dengan foto/video
- 📰 **Running News** - Berita berjalan dari atas ke bawah
- 📸 **Photobooth** - Sistem foto interaktif dengan countdown
- 🗄️ **SQLite Database** - Penyimpanan data foto dan agenda
- 🎨 **Desain Modern** - Interface yang menarik dengan tema biru

## Struktur Folder

```
photo-station/
├── app.py                  # Aplikasi Flask utama
├── init_db.py             # Script inisialisasi database
├── photostation.db        # Database SQLite (akan dibuat otomatis)
├── requirements.txt       # Dependencies Python
├── static/
│   ├── css/
│   │   ├── style.css         # Style halaman utama
│   │   └── photobooth.css    # Style halaman photobooth
│   ├── js/
│   │   ├── script.js         # JavaScript halaman utama
│   │   └── photobooth.js     # JavaScript photobooth
│   ├── logos/
│   │   ├── logo1.png         # Logo kiri atas
│   │   ├── logo2.png         # Logo kanan atas
│   │   └── barcode.png       # QR Code/Barcode
│   └── uploads/
│       └── (foto/video akan disimpan di sini)
└── templates/
    ├── index.html         # Template halaman utama
    └── photobooth.html    # Template halaman photobooth
```

## Instalasi di Raspberry Pi 5

### 1. Persiapan Sistem

```bash
# Update sistem
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install -y python3-pip python3-venv sqlite3
```

### 2. Setup Project

```bash
# Buat folder project
mkdir ~/photo-station
cd ~/photo-station

# Clone atau copy semua file ke folder ini
# (copy semua file yang sudah dibuat)

# Buat virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies Python
pip install flask pillow
```

### 3. Inisialisasi Database

```bash
# Jalankan script inisialisasi database
python3 init_db.py
```

### 4. Tambahkan Logo dan QR Code

Letakkan file gambar logo dan QR code Anda di folder:
- `static/logos/logo1.png` - Logo kiri
- `static/logos/logo2.png` - Logo kanan  
- `static/logos/barcode.png` - QR Code

### 5. Jalankan Aplikasi

```bash
# Development mode
python3 app.py

# Atau untuk production dengan gunicorn:
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

Akses aplikasi di browser:
- Halaman utama: `http://[IP-RASPBERRY-PI]:5000`
- Photobooth: `http://[IP-RASPBERRY-PI]:5000/photobooth`

## Konfigurasi Auto-Start (Opsional)

Untuk menjalankan aplikasi otomatis saat Raspberry Pi boot:

### 1. Buat Service File

```bash
sudo nano /etc/systemd/system/photostation.service
```

### 2. Isi dengan:

```ini
[Unit]
Description=Photo Station Web App
After=network.target

[Service]
User=pi
WorkingDirectory=/home/pi/photo-station
Environment="PATH=/home/pi/photo-station/venv/bin"
ExecStart=/home/pi/photo-station/venv/bin/python3 /home/pi/photo-station/app.py

[Install]
WantedBy=multi-user.target
```

### 3. Enable dan Start Service

```bash
sudo systemctl daemon-reload
sudo systemctl enable photostation.service
sudo systemctl start photostation.service
sudo systemctl status photostation.service
```

## Penggunaan

### Halaman Utama

1. **Agenda Carousel** - Klik agenda di sidebar kiri untuk berganti tampilan
2. **Auto-Rotate** - Agenda berganti otomatis setiap 10 detik
3. **Running News** - Berita berjalan otomatis dari atas ke bawah
4. **Photobooth Button** - Klik untuk membuka halaman photobooth

### Photobooth

1. Kamera akan aktif otomatis saat halaman dibuka
2. Klik tombol "Ambil Foto"
3. Tunggu countdown 3 detik
4. Review foto hasil capture
5. Pilih "Simpan" untuk menyimpan atau "Ulangi" untuk foto ulang
6. Foto tersimpan di database dan folder uploads

## Mengelola Data

### Tambah/Edit Agenda

```python
import sqlite3

conn = sqlite3.connect('photostation.db')
cursor = conn.cursor()

# Tambah agenda baru
cursor.execute('''
    INSERT INTO agendas (position, title, description, media_type, media_path, event_date)
    VALUES (?, ?, ?, ?, ?, ?)
''', (1, 'AGENDA 1', 'Deskripsi agenda', 'photo', 'static/uploads/foto.jpg', 'Rabu, 04 Februari 2026'))

conn.commit()
conn.close()
```

### Tambah/Edit Berita

```python
import sqlite3

conn = sqlite3.connect('photostation.db')
cursor = conn.cursor()

# Tambah berita baru
cursor.execute('''
    INSERT INTO news (content, is_active)
    VALUES (?, ?)
''', ('Konten berita baru', 1))

conn.commit()
conn.close()
```

## Troubleshooting

### Kamera tidak terdeteksi
- Pastikan browser mendapat izin akses kamera
- Gunakan HTTPS atau localhost untuk akses kamera
- Cek apakah kamera USB/module camera sudah terhubung

### Port 5000 sudah digunakan
```bash
# Ganti port di app.py baris terakhir:
app.run(host='0.0.0.0', port=8080, debug=True)
```

### Database error
```bash
# Hapus dan buat ulang database
rm photostation.db
python3 init_db.py
```

## Catatan Penting

1. **Media Files**: Letakkan foto/video di folder `static/uploads/`
2. **Format Support**: 
   - Foto: JPG, PNG, WebP
   - Video: MP4 (H.264)
3. **Ukuran Maksimal**: 16MB per file
4. **Browser**: Gunakan Chrome/Chromium untuk performa terbaik
5. **Akses Kamera**: Hanya bekerja di HTTPS atau localhost

## Lisensi

MIT License - Bebas digunakan dan dimodifikasi

## Support

Untuk pertanyaan dan bantuan, silakan buka issue di repository atau hubungi developer.

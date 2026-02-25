#!/usr/bin/env python3
"""
Sample Data Script
Contoh script untuk menambahkan data agenda, berita, dan settings
Anda bisa memodifikasi script ini sesuai kebutuhan
"""

import sqlite3
from datetime import datetime

def add_sample_data():
    conn = sqlite3.connect('photostation.db')
    cursor = conn.cursor()
    
    print("Menambahkan sample data...")
    
    # Hapus data lama (opsional)
    # cursor.execute('DELETE FROM agendas')
    # cursor.execute('DELETE FROM news')
    
    # Contoh: Tambah agenda dengan foto
    agendas = [
        {
            'position': 1,
            'title': 'RAPAT KOORDINASI',
            'description': 'Rapat koordinasi bulanan dengan seluruh staff. Harap hadir tepat waktu.',
            'media_type': 'photo',
            'media_path': 'static/uploads/meeting.jpg',
            'event_date': 'Rabu, 14 Februari 2026'
        },
        {
            'position': 2,
            'title': 'TRAINING KARYAWAN',
            'description': 'Pelatihan penggunaan sistem baru untuk meningkatkan produktivitas.',
            'media_type': 'photo',
            'media_path': 'static/uploads/training.jpg',
            'event_date': 'Kamis, 15 Februari 2026'
        },
        {
            'position': 3,
            'title': 'COMPANY GATHERING',
            'description': 'Acara gathering tahunan di Taman Safari Bogor.',
            'media_type': 'video',
            'media_path': 'static/uploads/gathering.mp4',
            'event_date': 'Sabtu, 17 Februari 2026'
        }
    ]
    
    for agenda in agendas:
        cursor.execute('''
            INSERT INTO agendas (position, title, description, media_type, media_path, event_date, is_active)
            VALUES (?, ?, ?, ?, ?, ?, 1)
        ''', (agenda['position'], agenda['title'], agenda['description'], 
              agenda['media_type'], agenda['media_path'], agenda['event_date']))
    
    print(f"✓ {len(agendas)} agenda ditambahkan")
    
    # Contoh: Tambah berita
    news_items = [
        'Selamat datang di Photo Station v1.0 - Sistem informasi digital terintegrasi untuk Raspberry Pi',
        'Info: Kantor tutup pada tanggal 18 Februari 2026 (Hari Raya Idul Fitri)',
        'Pengumuman: Pendaftaran training online dibuka sampai tanggal 20 Februari 2026',
        'Update: Sistem keamanan baru telah diaktifkan di semua pintu masuk',
        'Reminder: Jangan lupa mengisi absensi digital setiap hari',
        'Info Penting: Meeting Zoom link akan dikirim via email 1 jam sebelum meeting',
        'Selamat kepada Tim Sales yang berhasil mencapai target bulan ini!',
        'Pengumuman: Parkir basement akan ditutup sementara untuk renovasi mulai besok'
    ]
    
    for news in news_items:
        cursor.execute('INSERT INTO news (content, is_active) VALUES (?, 1)', (news,))
    
    print(f"✓ {len(news_items)} berita ditambahkan")
    
    # Update settings (logo dan barcode paths)
    cursor.execute('''
        UPDATE settings 
        SET logo1_path = 'static/logos/logo1.png',
            logo2_path = 'static/logos/logo2.png',
            barcode_path = 'static/logos/barcode.png'
        WHERE id = 1
    ''')
    
    print("✓ Settings diupdate")
    
    conn.commit()
    conn.close()
    
    print("\n✓ Sample data berhasil ditambahkan!")
    print("\nCatatan:")
    print("- Pastikan file media (foto/video) sudah ada di folder static/uploads/")
    print("- Anda bisa mengedit data melalui manage.py")
    print("\nJalankan aplikasi dengan: python3 app.py")

def add_custom_agenda(position, title, description, media_type, media_path, event_date):
    """
    Fungsi helper untuk menambah agenda custom
    
    Contoh penggunaan:
    add_custom_agenda(
        position=1,
        title='AGENDA BARU',
        description='Deskripsi agenda',
        media_type='photo',
        media_path='static/uploads/foto.jpg',
        event_date='Senin, 18 Februari 2026'
    )
    """
    conn = sqlite3.connect('photostation.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO agendas (position, title, description, media_type, media_path, event_date, is_active)
        VALUES (?, ?, ?, ?, ?, ?, 1)
    ''', (position, title, description, media_type, media_path, event_date))
    
    conn.commit()
    conn.close()
    print(f"✓ Agenda '{title}' berhasil ditambahkan!")

def add_custom_news(content):
    """
    Fungsi helper untuk menambah berita custom
    
    Contoh penggunaan:
    add_custom_news('Ini adalah berita baru yang penting')
    """
    conn = sqlite3.connect('photostation.db')
    cursor = conn.cursor()
    
    cursor.execute('INSERT INTO news (content, is_active) VALUES (?, 1)', (content,))
    
    conn.commit()
    conn.close()
    print(f"✓ Berita berhasil ditambahkan!")

def bulk_add_news_from_file(filename):
    """
    Menambah berita dari file teks (satu berita per baris)
    
    Contoh penggunaan:
    bulk_add_news_from_file('berita.txt')
    """
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            news_list = [line.strip() for line in f if line.strip()]
        
        conn = sqlite3.connect('photostation.db')
        cursor = conn.cursor()
        
        for news in news_list:
            cursor.execute('INSERT INTO news (content, is_active) VALUES (?, 1)', (news,))
        
        conn.commit()
        conn.close()
        
        print(f"✓ {len(news_list)} berita dari {filename} berhasil ditambahkan!")
    except FileNotFoundError:
        print(f"✗ File {filename} tidak ditemukan!")
    except Exception as e:
        print(f"✗ Error: {e}")

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == '--help':
            print("Penggunaan:")
            print("  python3 sample_data.py           - Tambah sample data default")
            print("  python3 sample_data.py --custom  - Gunakan fungsi custom (edit script)")
        elif sys.argv[1] == '--custom':
            # Contoh penggunaan fungsi custom
            # Uncomment dan edit sesuai kebutuhan
            
            # add_custom_agenda(
            #     position=1,
            #     title='MEETING PENTING',
            #     description='Meeting dengan klien besar',
            #     media_type='photo',
            #     media_path='static/uploads/meeting.jpg',
            #     event_date='Senin, 20 Februari 2026'
            # )
            
            # add_custom_news('Pengumuman: Meeting dengan klien dijadwalkan besok pagi')
            
            # bulk_add_news_from_file('berita.txt')
            
            print("Edit script ini untuk menambahkan data custom")
    else:
        add_sample_data()

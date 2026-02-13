import sqlite3
from datetime import datetime

def init_db():
    conn = sqlite3.connect('photostation.db')
    cursor = conn.cursor()
    
    # Create agendas table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS agendas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            position INTEGER NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            media_type TEXT CHECK(media_type IN ('photo', 'video')),
            media_path TEXT,
            event_date TEXT,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create news table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS news (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT NOT NULL,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create photos table (for photobooth captures)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS photos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            filepath TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create settings table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            id INTEGER PRIMARY KEY,
            logo1_path TEXT,
            logo2_path TEXT,
            barcode_path TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Insert default settings
    cursor.execute('''
        INSERT OR IGNORE INTO settings (id, logo1_path, logo2_path, barcode_path)
        VALUES (1, 'static/logos/logo1.png', 'static/logos/logo2.png', 'static/logos/barcode.png')
    ''')
    
    # Insert sample agendas
    sample_agendas = [
        (1, 'AGENDA 1', 'Lorem ipsum dolor sit amet, consectetur adipiscing elit.', 'photo', 'static/uploads/default1.jpg', 'Rabu, 04 Februari 2026'),
        (2, 'AGENDA 2', 'Lorem ipsum dolor sit amet, consectetur adipiscing elit.', 'photo', 'static/uploads/default2.jpg', 'Rabu, 04 Februari 2026'),
        (3, 'AGENDA 3', 'Lorem ipsum dolor sit amet, consectetur adipiscing elit.', 'video', 'static/uploads/default3.mp4', 'Rabu, 04 Februari 2026')
    ]
    
    for agenda in sample_agendas:
        cursor.execute('''
            INSERT OR IGNORE INTO agendas (position, title, description, media_type, media_path, event_date)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', agenda)
    
    # Insert sample news
    sample_news = [
        ('Selamat datang di Photo Station - Sistem informasi digital terintegrasi',),
        ('Agenda hari ini: Pertemuan koordinasi pukul 14.00 WIB',),
        ('Informasi penting: Harap mengikuti protokol kesehatan',),
        ('Update terbaru sistem akan dilakukan pada hari Jumat',),
    ]
    
    for news in sample_news:
        cursor.execute('INSERT OR IGNORE INTO news (content) VALUES (?)', news)
    
    conn.commit()
    conn.close()
    print("Database initialized successfully!")

if __name__ == '__main__':
    init_db()

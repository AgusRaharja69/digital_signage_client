#!/usr/bin/env python3
"""
Database Initialization Script for Digital Signage Client
Creates signage.db with complete schema for dynamic template system
"""

import sqlite3
from datetime import datetime, timedelta
import os

def init_db():
    """Initialize database with complete schema"""
    
    db_path = os.path.join(os.path.dirname(__file__), 'db', 'signage.db')
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    print("="*70)
    print("INITIALIZING DIGITAL SIGNAGE DATABASE")
    print("="*70)
    print(f"\nDatabase: {db_path}\n")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # ========================
    # CONFIGURATION TABLE
    # ========================
    print("Creating config table...")
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS config (
            key TEXT PRIMARY KEY,
            value TEXT,
            description TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Insert default config
    default_configs = [
        ('device_id', 'RPI_CLIENT_001', 'Unique device identifier'),
        ('device_name', 'Digital Signage Display 1', 'Device display name'),
        ('mqtt_broker', '192.168.1.100', 'MQTT broker IP address'),
        ('mqtt_port', '1883', 'MQTT broker port'),
        ('mqtt_topic', 'signage/client/001', 'MQTT topic for this device'),
        ('mqtt_username', '', 'MQTT username (optional)'),
        ('mqtt_password', '', 'MQTT password (optional)'),
        ('display_width', '1920', 'Display width in pixels'),
        ('display_height', '1080', 'Display height in pixels'),
        ('display_orientation', 'landscape', 'Display orientation'),
        ('last_sync', datetime.now().isoformat(), 'Last sync timestamp'),
    ]
    
    for key, value, desc in default_configs:
        cursor.execute('''
            INSERT OR IGNORE INTO config (key, value, description) 
            VALUES (?, ?, ?)
        ''', (key, value, desc))
    
    print("✓ Config table created with default values")
    
    # ========================
    # TEMPLATES TABLE
    # ========================
    print("\nCreating templates table...")
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            template_type TEXT NOT NULL CHECK(template_type IN ('html', 'image', 'video')),
            template_name TEXT NOT NULL,
            file_path TEXT,
            duration INTEGER DEFAULT 10,
            is_active INTEGER DEFAULT 1,
            display_order INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Insert sample templates
    sample_templates = [
        ('html', 'Agenda Template', 'templates/agenda.html', 15, 1, 1),
        ('image', 'Banner Promo', 'static/uploads/promo.jpg', 10, 1, 2),
        ('video', 'Company Profile', 'static/uploads/profile.mp4', 20, 1, 3),
    ]
    
    for tpl in sample_templates:
        cursor.execute('''
            INSERT INTO templates (template_type, template_name, file_path, duration, is_active, display_order)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', tpl)
    
    print("✓ Templates table created with 3 sample templates")
    
    # ========================
    # ADVERTISEMENTS TABLE
    # ========================
    print("\nCreating advertisements table...")
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS advertisements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ad_name TEXT NOT NULL,
            ad_type TEXT NOT NULL CHECK(ad_type IN ('image', 'video')),
            file_path TEXT NOT NULL,
            duration INTEGER DEFAULT 10,
            position TEXT DEFAULT 'bottom-right' CHECK(position IN ('bottom-right', 'bottom-left', 'top-right', 'top-left')),
            trigger_time INTEGER DEFAULT 10,
            is_active INTEGER DEFAULT 1,
            display_order INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Insert sample ads
    sample_ads = [
        ('Developer Ad 1', 'image', 'static/uploads/ads/ad1.jpg', 8, 'bottom-right', 10, 1, 1),
        ('Developer Ad 2', 'video', 'static/uploads/ads/ad2.mp4', 10, 'bottom-right', 15, 1, 2),
    ]
    
    for ad in sample_ads:
        cursor.execute('''
            INSERT INTO advertisements (ad_name, ad_type, file_path, duration, position, trigger_time, is_active, display_order)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', ad)
    
    print("✓ Advertisements table created")
    
    # ========================
    # AGENDAS TABLE (untuk HTML template)
    # ========================
    print("\nCreating agendas table...")
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
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Sample agendas
    sample_agendas = [
        (1, 'RAPAT KOORDINASI', 'Rapat koordinasi bulanan dengan seluruh staff', 'photo', 'static/uploads/meeting.jpg', 'Rabu, 14 Februari 2026'),
        (2, 'TRAINING KARYAWAN', 'Pelatihan sistem baru', 'photo', 'static/uploads/training.jpg', 'Kamis, 15 Februari 2026'),
        (3, 'COMPANY GATHERING', 'Gathering tahunan', 'video', 'static/uploads/gathering.mp4', 'Sabtu, 17 Februari 2026'),
    ]
    
    for agenda in sample_agendas:
        cursor.execute('''
            INSERT INTO agendas (position, title, description, media_type, media_path, event_date, is_active)
            VALUES (?, ?, ?, ?, ?, ?, 1)
        ''', agenda)
    
    print("✓ Agendas table created")
    
    # ========================
    # NEWS TABLE (untuk running text)
    # ========================
    print("\nCreating news table...")
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS news (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT NOT NULL,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Sample news
    sample_news = [
        ('🎉 Selamat datang di Digital Signage v2.0'),
        ('📢 Info: Kantor tutup tanggal 18 Februari 2026'),
        ('📝 Pengumuman: Pendaftaran training dibuka hingga 20 Februari'),
        ('⏰ Reminder: Isi absensi digital setiap hari'),
        ('🏆 Selamat kepada Tim Sales yang mencapai target!'),
    ]
    
    for news in sample_news:
        cursor.execute('INSERT INTO news (content, is_active) VALUES (?, 1)', (news,))
    
    print("✓ News table created")
    
    # ========================
    # PHOTOS TABLE (untuk photobooth)
    # ========================
    print("\nCreating photos table...")
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS photos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            filepath TEXT NOT NULL,
            session_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    print("✓ Photos table created")
    
    # ========================
    # SYNC LOGS TABLE
    # ========================
    print("\nCreating sync_logs table...")
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sync_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action TEXT NOT NULL,
            details TEXT,
            status TEXT CHECK(status IN ('success', 'error', 'pending')),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        INSERT INTO sync_logs (action, details, status)
        VALUES ('database_init', 'Database initialized with sample data', 'success')
    ''')
    
    print("✓ Sync logs table created")
    
    # Create indexes
    print("\nCreating indexes...")
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_templates_active ON templates(is_active, display_order)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_ads_active ON advertisements(is_active, display_order)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_agendas_active ON agendas(is_active, position)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_news_active ON news(is_active)')
    print("✓ Indexes created")
    
    conn.commit()
    
    # Show summary
    print("\n" + "="*70)
    print("DATABASE SUMMARY")
    print("="*70)
    
    cursor.execute('SELECT COUNT(*) FROM templates WHERE is_active = 1')
    print(f"Active templates: {cursor.fetchone()[0]}")
    
    cursor.execute('SELECT COUNT(*) FROM advertisements WHERE is_active = 1')
    print(f"Active advertisements: {cursor.fetchone()[0]}")
    
    cursor.execute('SELECT COUNT(*) FROM agendas WHERE is_active = 1')
    print(f"Active agendas: {cursor.fetchone()[0]}")
    
    cursor.execute('SELECT COUNT(*) FROM news WHERE is_active = 1')
    print(f"Active news: {cursor.fetchone()[0]}")
    
    cursor.execute('SELECT COUNT(*) FROM config')
    print(f"Config entries: {cursor.fetchone()[0]}")
    
    print("\n" + "="*70)
    print("MQTT CONFIGURATION")
    print("="*70)
    cursor.execute("SELECT key, value FROM config WHERE key LIKE 'mqtt%' OR key LIKE 'device%'")
    for row in cursor.fetchall():
        print(f"{row[0]:20s}: {row[1]}")
    
    print("="*70)
    
    conn.close()
    
    print(f"\n✅ Database created successfully!")
    print(f"📁 Location: {db_path}")
    print(f"📊 Size: {os.path.getsize(db_path)} bytes")
    
    return db_path

if __name__ == '__main__':
    try:
        init_db()
        print("\n✅ Setup complete! Run: python3 app.py")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

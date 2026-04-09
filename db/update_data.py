#!/usr/bin/env python3
"""
Update Data Script — Digital Signage
SMAN 1 TABANAN / Universitas Warmadewa

Mengganti data pada tabel:
  - advertisements  : hanya 1 iklan (sipenmaru)
  - agendas         : 10 agenda April–Mei 2026
  - config          : device_id, mqtt_topic, barcode, school_name, wifi, webhook
  - news            : 2 berita
  - templates       : 3 template video
"""

import sqlite3

DB_NAME = 'photostation.db'


def get_conn():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


# ══════════════════════════════════════════════════════════════════════════════
# FUNGSI UTAMA
# ══════════════════════════════════════════════════════════════════════════════

def update_all():
    conn = get_conn()
    c = conn.cursor()

    update_advertisements(c)
    update_agendas(c)
    update_config(c)
    update_news(c)
    update_templates(c)

    conn.commit()
    conn.close()

    print("\n✓ Semua data berhasil diupdate!")
    print("\nJalankan aplikasi dengan: python3 app.py")


def update_advertisements(c):
    """Hapus semua iklan, isi dengan 1 iklan sipenmaru."""
    c.execute('DELETE FROM advertisements')

    c.execute('''
        INSERT INTO advertisements
            (ad_name, ad_type, file_path, duration, position, trigger_time, is_active, display_order)
        VALUES (?, ?, ?, 5, 'bottom-right', 10, 1, 1)
    ''', ('sipenmaru', 'image', 'static/uploads/ads/ad1.webp'))

    print("  ✓ advertisements: 1 iklan (sipenmaru) ditambahkan")


def update_agendas(c):
    """Hapus semua agenda, isi dengan 10 agenda baru."""
    c.execute('DELETE FROM agendas')

    agendas = [
        (1,  'Yudisium ke-30 Pascasarjana',                              '', 'photo', '', 'Sabtu, 11 April 2026',   '09:00'),
        (2,  'Seminar Unwar bersama NatGeo',                             '', 'photo', '', 'Selasa, 14 April 2026',  '09:00'),
        (3,  'Yudisium ke-80 FISIP Unwar',                               '', 'photo', '', 'Rabu, 15 April 2026',    '09:00'),
        (4,  'Donor Darah dalam rangka HUT Mapala Citta Mandala Unwar',  '', 'photo', '', 'Rabu, 15 April 2026',    '09:00'),
        (5,  'Yudisium ke-77 FTP Unwar',                                 '', 'photo', '', 'Jumat, 17 April 2026',   '09:00'),
        (6,  'Malam Puncak HUT Mapala Citta Mandala Unwar',              '', 'photo', '', 'Jumat, 17 April 2026',   '09:00'),
        (7,  'Yudisium ke-81 FH Unwar',                                  '', 'photo', '', 'Selasa, 21 April 2026',  '09:00'),
        (8,  'Yudisium ke-80 FEB Unwar',                                 '', 'photo', '', 'Jumat, 24 April 2026',   '09:00'),
        (9,  'Wisuda ke 80 Universitas Warmadewa',                       '', 'photo', '', 'Sabtu, 2 Mei 2026',      '09:00'),
        (10, 'Hari Pendidikan Nasional',                                 '', 'photo', '', 'Sabtu, 2 Mei 2026',      '09:00'),
    ]

    c.executemany('''
        INSERT INTO agendas
            (position, title, description, media_type, media_path, event_date, event_time, is_active)
        VALUES (?, ?, ?, ?, ?, ?, ?, 1)
    ''', agendas)

    print(f"  ✓ agendas: {len(agendas)} agenda ditambahkan")


def update_config(c):
    """Update nilai-nilai config tertentu (tidak menghapus key lain)."""
    config_updates = {
        'device_id':           'client_1',
        'mqtt_topic':          'signage/sma-n-1-tabanan/',
        'barcode_boot':        'static/imgs/barcode.png',
        'school_name':         'SMAN 1 TABANAN',
        'wifi_ssid':           'awlr_wifi',
        'wifi_password':       'Warmadewa2025',
        'photo_drive_webhook': 'https://script.google.com/macros/s/AKfycbwp5U6C7j9BTBrOjYIXgEiXJ2XJn6N1u9Ex6SUU3ccMQM4FaD9GDye2haZ7Pp4KOboRMg/exec',
    }

    for key, value in config_updates.items():
        c.execute('''
            INSERT OR REPLACE INTO config (key, value, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
        ''', (key, value))
        print(f"  ✓ config: {key} = {value}")


def update_news(c):
    """Hapus semua berita, isi dengan 2 berita baru."""
    c.execute('DELETE FROM news')

    news_items = [
        'Info Tentang Penerimaan Mahasiswa Baru Universitas Warmadewa www.sipenmaru.warmadewa.ac.id',
        'Univeritas Warmadewa telah terakreditasi "UNGGUL" dari Badan Akreditasi Nasional Perguruan Tinggi (BAN PT)',
    ]

    for content in news_items:
        c.execute('INSERT INTO news (content, is_active) VALUES (?, 1)', (content,))

    print(f"  ✓ news: {len(news_items)} berita ditambahkan")


def update_templates(c):
    """Hapus semua template, isi dengan 3 template video baru."""
    c.execute('DELETE FROM templates')

    templates = [
        ('video', 'profile sekolah', 'static/uploads/profile.mp4',       30, 1, 1),
        ('video', 'profile UNWAR',   'static/uploads/profile-warma.mp4',  30, 1, 2),
        ('video', 'jinggle UNWAR',   'static/uploads/jinggle-warma.mp4',  30, 1, 3),
    ]

    c.executemany('''
        INSERT INTO templates
            (template_type, template_name, file_path, duration, is_active, display_order)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', templates)

    print(f"  ✓ templates: {len(templates)} template ditambahkan")


# ══════════════════════════════════════════════════════════════════════════════
# FUNGSI SHOW / VERIFY
# ══════════════════════════════════════════════════════════════════════════════

def show_all():
    """Tampilkan isi semua tabel yang diupdate."""
    conn = get_conn()

    print("\n── advertisements ────────────────────────")
    for r in conn.execute('SELECT id, ad_name, ad_type, file_path FROM advertisements'):
        print(f"  [{r['id']}] {r['ad_name']} ({r['ad_type']}) → {r['file_path']}")

    print("\n── agendas ───────────────────────────────")
    for r in conn.execute('SELECT position, title, event_date, event_time FROM agendas ORDER BY position'):
        print(f"  {r['position']:>2}. {r['event_date']} {r['event_time']}  {r['title']}")

    print("\n── config (yang diupdate) ────────────────")
    keys = ['device_id', 'mqtt_topic', 'barcode_boot', 'school_name',
            'wifi_ssid', 'wifi_password', 'photo_drive_webhook']
    for key in keys:
        row = conn.execute('SELECT value FROM config WHERE key=?', (key,)).fetchone()
        val = row['value'] if row else '(tidak ada)'
        print(f"  {key:25s} = {val}")

    print("\n── news ──────────────────────────────────")
    for r in conn.execute('SELECT id, content FROM news'):
        print(f"  [{r['id']}] {r['content']}")

    print("\n── templates ─────────────────────────────")
    for r in conn.execute('SELECT id, template_name, file_path FROM templates'):
        print(f"  [{r['id']}] {r['template_name']} → {r['file_path']}")

    conn.close()
    print()


# ══════════════════════════════════════════════════════════════════════════════
# MAIN CLI
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    import sys

    if len(sys.argv) > 1:
        cmd = sys.argv[1]

        if cmd == '--help':
            print("""Penggunaan:
  python3 update_data.py              Jalankan semua update sekaligus
  python3 update_data.py --show       Tampilkan isi tabel setelah update
  python3 update_data.py --ads        Update hanya tabel advertisements
  python3 update_data.py --agendas    Update hanya tabel agendas
  python3 update_data.py --config     Update hanya tabel config
  python3 update_data.py --news       Update hanya tabel news
  python3 update_data.py --templates  Update hanya tabel templates
""")

        elif cmd == '--show':
            show_all()

        elif cmd == '--ads':
            conn = get_conn()
            update_advertisements(conn.cursor())
            conn.commit(); conn.close()

        elif cmd == '--agendas':
            conn = get_conn()
            update_agendas(conn.cursor())
            conn.commit(); conn.close()

        elif cmd == '--config':
            conn = get_conn()
            update_config(conn.cursor())
            conn.commit(); conn.close()

        elif cmd == '--news':
            conn = get_conn()
            update_news(conn.cursor())
            conn.commit(); conn.close()

        elif cmd == '--templates':
            conn = get_conn()
            update_templates(conn.cursor())
            conn.commit(); conn.close()

        else:
            print(f"Perintah tidak dikenal: {cmd}. Gunakan --help")

    else:
        update_all()
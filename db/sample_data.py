#!/usr/bin/env python3
"""
Sample Data Script — Digital Signage
Versi update dengan dukungan:
  - event_time (jam acara) pada agenda
  - config: main_color, secondary_color, time_on, time_off, date_off
  - Auto-isi hari Minggu untuk date_off
"""

import sqlite3
import calendar
from datetime import date, datetime

DB_NAME = 'photostation.db'

def get_conn():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


# ══════════════════════════════════════════════════════════════════════════════
# MIGRASI — tambah kolom baru jika belum ada
# ══════════════════════════════════════════════════════════════════════════════

def run_migrations():
    """Jalankan ini sekali untuk menambah kolom baru ke tabel yang sudah ada."""
    conn = get_conn()
    c = conn.cursor()

    # Tabel config (buat jika belum ada)
    c.execute('''CREATE TABLE IF NOT EXISTS config (
        key        TEXT PRIMARY KEY,
        value      TEXT,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')

    # Kolom event_time di tabel agendas
    try:
        c.execute('ALTER TABLE agendas ADD COLUMN event_time TEXT')
        print('  migrated: agendas.event_time ditambahkan')
    except sqlite3.OperationalError:
        pass  # kolom sudah ada

    # Default config (INSERT OR IGNORE = tidak menimpa nilai yang sudah ada)
    defaults = [
        ('main_color',      '#4ecca3'),
        ('secondary_color', '#00b4d8'),
        ('bg_color',        '#060a12'),
        ('time_on',         '07:00'),
        ('time_off',        '17:00'),
        ('date_off',        ''),
        ('logo_univ',       'static/imgs/logo1.png'),
        ('logo_sekolah',    'static/imgs/logo2.png'),
        ('barcode_boot',    'static/imgs/barcode.jpeg'),
        ('school_name',     'SMKN 1 DENPASAR'),
        ('wifi_ssid',       ''),
        ('wifi_password',   ''),
        # URL Google Apps Script Web App (bukan link folder Drive langsung)
        # Setup: script.google.com → deploy sebagai Web App → copy URL
        ('photo_drive_webhook', ''),
    ]
    for key, value in defaults:
        c.execute('INSERT OR IGNORE INTO config (key, value) VALUES (?, ?)', (key, value))

    conn.commit()
    conn.close()


# ══════════════════════════════════════════════════════════════════════════════
# SAMPLE DATA UTAMA
# ══════════════════════════════════════════════════════════════════════════════

def add_sample_data():
    run_migrations()

    conn = get_conn()
    cursor = conn.cursor()

    print("Menambahkan sample data...")

    # Hapus data lama (opsional)
    # cursor.execute('DELETE FROM agendas')
    # cursor.execute('DELETE FROM news')

    # Agenda dengan event_time
    agendas = [
        {
            'position':   1,
            'title':      'RAPAT KOORDINASI',
            'description':'Rapat koordinasi bulanan dengan seluruh staff. Harap hadir tepat waktu.',
            'media_type': 'photo',
            'media_path': 'static/uploads/meeting.jpg',
            'event_date': 'Rabu, 14 Februari 2026',
            'event_time': '08:00',
        },
        {
            'position':   2,
            'title':      'TRAINING KARYAWAN',
            'description':'Pelatihan penggunaan sistem baru untuk meningkatkan produktivitas.',
            'media_type': 'photo',
            'media_path': 'static/uploads/training.jpg',
            'event_date': 'Kamis, 15 Februari 2026',
            'event_time': '09:30',
        },
        {
            'position':   3,
            'title':      'COMPANY GATHERING',
            'description':'Acara gathering tahunan di Taman Safari Bogor.',
            'media_type': 'video',
            'media_path': 'static/uploads/gathering.mp4',
            'event_date': 'Sabtu, 17 Februari 2026',
            'event_time': '13:00',
        },
    ]

    for agenda in agendas:
        cursor.execute('''
            INSERT INTO agendas
                (position, title, description, media_type, media_path, event_date, event_time, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, 1)
        ''', (agenda['position'], agenda['title'], agenda['description'],
              agenda['media_type'], agenda['media_path'],
              agenda['event_date'], agenda['event_time']))

    print(f"  {len(agendas)} agenda ditambahkan")

    # Berita
    news_items = [
        'Selamat datang di Digital Signage v2.0 - Sistem informasi digital terintegrasi',
        'Info: Kantor tutup pada tanggal 18 Februari 2026 (Hari Raya Idul Fitri)',
        'Pengumuman: Pendaftaran training online dibuka sampai tanggal 20 Februari 2026',
        'Update: Sistem keamanan baru telah diaktifkan di semua pintu masuk',
        'Reminder: Jangan lupa mengisi absensi digital setiap hari',
        'Info Penting: Meeting Zoom link akan dikirim via email 1 jam sebelum meeting',
        'Selamat kepada Tim Sales yang berhasil mencapai target bulan ini!',
        'Pengumuman: Parkir basement akan ditutup sementara untuk renovasi mulai besok',
    ]

    for news in news_items:
        cursor.execute('INSERT INTO news (content, is_active) VALUES (?, 1)', (news,))

    print(f"  {len(news_items)} berita ditambahkan")

    # Settings logo (tabel lama)
    try:
        cursor.execute('''
            UPDATE settings
            SET logo1_path   = 'static/logos/logo1.png',
                logo2_path   = 'static/logos/logo2.png',
                barcode_path = 'static/logos/barcode.png'
            WHERE id = 1
        ''')
        print("  Settings logo/barcode diupdate")
    except Exception:
        pass

    # Config warna, jadwal, dan path foto/logo
    config_values = {
        # Warna tema
        'main_color':      '#4ecca3',
        'secondary_color': '#00b4d8',
        'bg_color':        '#060a12',
        # Jadwal layar
        'time_on':         '07:00',
        'time_off':        '17:00',
        # Path logo & barcode
        'logo_univ':       'static/imgs/logo1.png',
        'logo_sekolah':    'static/imgs/logo2.png',
        'barcode_boot':    'static/imgs/barcode.jpeg',
        # Nama sekolah (tampil di frame photobooth)
        'school_name':     'SMKN 1 DENPASAR',
        # WiFi — dipakai program background untuk auto-connect
        'wifi_ssid':            '',
        'wifi_password':        '',
        # Google Apps Script Web App URL untuk upload foto ke Drive
        # (tidak butuh autentikasi — script berjalan sebagai akun pemilik)
        'photo_drive_webhook':  'https://script.google.com/macros/s/AKfycbwvyG5wXwfGGiVDrDWCTR_p-QdWvLC40h6IgcrsRqRsdBntxQs9z77uIdFgqI0wwbBCuA/exec',
    }
    for key, value in config_values.items():
        cursor.execute('''
            INSERT OR REPLACE INTO config (key, value, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
        ''', (key, value))

    print("  Config warna, jadwal, dan path logo disimpan")

    # date_off: hari Minggu bulan ini otomatis
    # sundays = get_sundays_this_month()
    # _save_date_off(cursor, sundays)
    # print(f"  date_off hari Minggu bulan ini: {', '.join(sundays)}")

    conn.commit()
    conn.close()

    print("\n✓ Sample data berhasil ditambahkan!")
    print("\nCatatan:")
    print("  - Pastikan file media sudah ada di folder static/uploads/")
    print("  - Lihat config: python3 sample_data.py --config")
    print("  - Update warna: python3 sample_data.py --color '#ff0000' '#0000ff'")
    print("  - Update jadwal: python3 sample_data.py --schedule 07:00 17:00")
    print("  - Hari Minggu bulan baru: python3 sample_data.py --sundays")
    print("\nJalankan aplikasi dengan: python3 app.py")


# ══════════════════════════════════════════════════════════════════════════════
# FUNGSI HELPER
# ══════════════════════════════════════════════════════════════════════════════

def add_custom_agenda(position, title, description, media_type, media_path,
                      event_date, event_time=''):
    """
    Tambah agenda custom dengan jam.

    Contoh penggunaan:
    add_custom_agenda(
        position=1,
        title='SEMINAR NASIONAL',
        description='Seminar teknologi AI',
        media_type='photo',
        media_path='static/uploads/seminar.jpg',
        event_date='Senin, 20 Februari 2026',
        event_time='09:00',
    )
    """
    run_migrations()
    conn = get_conn()
    conn.execute('''
        INSERT INTO agendas
            (position, title, description, media_type, media_path, event_date, event_time, is_active)
        VALUES (?, ?, ?, ?, ?, ?, ?, 1)
    ''', (position, title, description, media_type, media_path, event_date, event_time))
    conn.commit()
    conn.close()
    print(f"✓ Agenda '{title}' ({event_date} {event_time}) berhasil ditambahkan!")


def add_custom_news(content):
    """
    Fungsi helper untuk menambah berita custom.

    Contoh penggunaan:
    add_custom_news('Ini adalah berita baru yang penting')
    """
    conn = get_conn()
    conn.execute('INSERT INTO news (content, is_active) VALUES (?, 1)', (content,))
    conn.commit()
    conn.close()
    print("✓ Berita berhasil ditambahkan!")


def bulk_add_news_from_file(filename):
    """
    Menambah berita dari file teks (satu berita per baris).

    Contoh penggunaan:
    bulk_add_news_from_file('berita.txt')
    """
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            news_list = [line.strip() for line in f if line.strip()]
        conn = get_conn()
        for news in news_list:
            conn.execute('INSERT INTO news (content, is_active) VALUES (?, 1)', (news,))
        conn.commit()
        conn.close()
        print(f"✓ {len(news_list)} berita dari {filename} berhasil ditambahkan!")
    except FileNotFoundError:
        print(f"✗ File {filename} tidak ditemukan!")


def set_colors(main_color, secondary_color, bg_color=None):
    """
    Update warna tema layar.

    Contoh:
        set_colors('#e63946', '#457b9d')
        set_colors('#ff6b35', '#004e89', bg_color='#1a1a2e')
    """
    run_migrations()
    conn = get_conn()
    updates = {'main_color': main_color, 'secondary_color': secondary_color}
    if bg_color:
        updates['bg_color'] = bg_color
    for k, v in updates.items():
        conn.execute('''
            INSERT OR REPLACE INTO config (key, value, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
        ''', (k, v))
    conn.commit()
    conn.close()
    print(f"✓ Warna diupdate: main={main_color}, secondary={secondary_color}")


def set_schedule(time_on, time_off):
    """
    Update jam layar menyala dan mati.

    Contoh:
        set_schedule('06:30', '18:00')
    """
    run_migrations()
    conn = get_conn()
    conn.execute("INSERT OR REPLACE INTO config (key,value,updated_at) VALUES ('time_on',?,CURRENT_TIMESTAMP)", (time_on,))
    conn.execute("INSERT OR REPLACE INTO config (key,value,updated_at) VALUES ('time_off',?,CURRENT_TIMESTAMP)", (time_off,))
    conn.commit()
    conn.close()
    print(f"✓ Jadwal: ON={time_on}, OFF={time_off}")


def set_logo_paths(logo_univ=None, logo_sekolah=None, barcode_boot=None):
    """
    Update path logo dan barcode di config.

    Path relatif terhadap root project (digital_signage_client/).

    Contoh:
        set_logo_paths(
            logo_univ    = 'static/imgs/logo1.png',
            logo_sekolah = 'static/imgs/logo2.png',
            barcode_boot = 'static/imgs/barcode.jpeg',
        )
    """
    run_migrations()
    conn = get_conn()
    updates = {}
    if logo_univ    is not None: updates['logo_univ']    = logo_univ
    if logo_sekolah is not None: updates['logo_sekolah'] = logo_sekolah
    if barcode_boot is not None: updates['barcode_boot'] = barcode_boot
    for k, v in updates.items():
        conn.execute('''
            INSERT OR REPLACE INTO config (key, value, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
        ''', (k, v))
    conn.commit()
    conn.close()
    for k, v in updates.items():
        print(f"✓ {k} = {v}")


def auto_populate_sundays(year=None, month=None):
    """
    Isi date_off dengan semua hari Minggu di bulan tertentu.
    Default: bulan berjalan.

    Contoh:
        auto_populate_sundays()           # bulan ini
        auto_populate_sundays(2026, 4)    # April 2026
    """
    run_migrations()
    today = date.today()
    year  = year  or today.year
    month = month or today.month

    sundays = get_sundays(year, month)

    conn = get_conn()
    cursor = conn.cursor()
    # Gabungkan dengan date_off yang sudah ada
    row = cursor.execute("SELECT value FROM config WHERE key='date_off'").fetchone()
    existing = set(row['value'].split(',')) if row and row['value'] else set()
    existing.update(sundays)
    existing.discard('')

    _save_date_off(cursor, list(existing))
    conn.commit()
    conn.close()

    print(f"✓ date_off hari Minggu {month}/{year} ditambahkan:")
    for d in sorted(sundays):
        print(f"   {d}")


def add_date_off(date_str):
    """
    Tambah tanggal libur/off manual (format: YYYY-MM-DD).

    Contoh:
        add_date_off('2026-03-22')   # Hari Raya / libur khusus
    """
    run_migrations()
    conn = get_conn()
    cursor = conn.cursor()
    row = cursor.execute("SELECT value FROM config WHERE key='date_off'").fetchone()
    existing = set(row['value'].split(',')) if row and row['value'] else set()
    existing.add(date_str)
    existing.discard('')
    _save_date_off(cursor, list(existing))
    conn.commit()
    conn.close()
    print(f"✓ Tanggal OFF ditambahkan: {date_str}")


def show_config():
    """Tampilkan semua nilai config saat ini."""
    run_migrations()
    conn = get_conn()
    rows = conn.execute('SELECT key, value, updated_at FROM config ORDER BY key').fetchall()
    conn.close()
    print("\n── Konfigurasi saat ini ──────────────────")
    for row in rows:
        print(f"  {row['key']:20s} = {row['value']}")
    print()


# ══════════════════════════════════════════════════════════════════════════════
# INTERNAL HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _save_date_off(cursor, date_list):
    value = ','.join(sorted(set(d for d in date_list if d)))
    cursor.execute('''
        INSERT OR REPLACE INTO config (key, value, updated_at)
        VALUES ('date_off', ?, CURRENT_TIMESTAMP)
    ''', (value,))


def get_sundays_this_month():
    today = date.today()
    return get_sundays(today.year, today.month)


def get_sundays(year, month):
    _, days_in_month = calendar.monthrange(year, month)
    return [
        date(year, month, d).strftime('%Y-%m-%d')
        for d in range(1, days_in_month + 1)
        if date(year, month, d).weekday() == 6
    ]


# ══════════════════════════════════════════════════════════════════════════════
# MAIN CLI
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    import sys

    if len(sys.argv) > 1:
        cmd = sys.argv[1]

        if cmd == '--help':
            print("""Penggunaan:
  python3 sample_data.py                        Tambah semua sample data
  python3 sample_data.py --migrate              Hanya jalankan migrasi database
  python3 sample_data.py --config               Tampilkan konfigurasi saat ini
  python3 sample_data.py --sundays              Isi date_off hari Minggu bulan ini
  python3 sample_data.py --sundays 2026 4       Isi date_off hari Minggu April 2026
  python3 sample_data.py --color #ff0000 #0000ff
  python3 sample_data.py --color #ff0000 #0000ff #1a1a2e  (+ background)
  python3 sample_data.py --schedule 07:00 17:00
  python3 sample_data.py --logo                 Update path logo & barcode ke default
  python3 sample_data.py --custom               Edit dan jalankan fungsi custom
""")

        elif cmd == '--migrate':
            run_migrations()
            print("✓ Migrasi selesai")

        elif cmd == '--config':
            show_config()

        elif cmd == '--sundays':
            if len(sys.argv) == 4:
                auto_populate_sundays(int(sys.argv[2]), int(sys.argv[3]))
            else:
                auto_populate_sundays()

        elif cmd == '--date-off' and len(sys.argv) >= 3:
            add_date_off(sys.argv[2])

        elif cmd == '--color' and len(sys.argv) >= 4:
            bg = sys.argv[4] if len(sys.argv) > 4 else None
            set_colors(sys.argv[2], sys.argv[3], bg)

        elif cmd == '--schedule' and len(sys.argv) >= 4:
            set_schedule(sys.argv[2], sys.argv[3])

        elif cmd == '--logo':
            set_logo_paths(
                logo_univ    = 'static/imgs/logo1.png',
                logo_sekolah = 'static/imgs/logo2.png',
                barcode_boot = 'static/imgs/barcode.jpeg',
            )

        elif cmd == '--custom':
            # ── Edit bagian ini untuk kebutuhan custom ──────────────────────
            # add_custom_agenda(
            #     position=1,
            #     title='SEMINAR AI',
            #     description='Seminar kecerdasan buatan nasional',
            #     media_type='photo',
            #     media_path='static/uploads/seminar.jpg',
            #     event_date='Senin, 20 Februari 2026',
            #     event_time='09:00',
            # )
            # add_custom_news('Pengumuman penting hari ini')
            # set_colors('#e63946', '#457b9d')
            # set_schedule('06:30', '18:00')
            # add_date_off('2026-03-22')
            print("Edit bagian --custom di script ini sesuai kebutuhan")

        else:
            print(f"Perintah tidak dikenal: {cmd}. Gunakan --help")
    else:
        add_sample_data()
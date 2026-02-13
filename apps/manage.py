#!/usr/bin/env python3
"""
Admin Management Script untuk Photo Station
Gunakan script ini untuk mengelola agenda dan berita dengan mudah
"""

import sqlite3
from datetime import datetime
import os

def get_db():
    conn = sqlite3.connect('photostation.db')
    conn.row_factory = sqlite3.Row
    return conn

def clear_screen():
    os.system('clear' if os.name == 'posix' else 'cls')

def show_menu():
    print("\n" + "="*60)
    print("   PHOTO STATION - ADMIN MANAGEMENT")
    print("="*60)
    print("\n1. Lihat Semua Agenda")
    print("2. Tambah Agenda Baru")
    print("3. Edit Agenda")
    print("4. Hapus Agenda")
    print("5. Toggle Aktif/Nonaktif Agenda")
    print("\n6. Lihat Semua Berita")
    print("7. Tambah Berita Baru")
    print("8. Edit Berita")
    print("9. Hapus Berita")
    print("10. Toggle Aktif/Nonaktif Berita")
    print("\n11. Lihat Semua Foto")
    print("12. Hapus Foto")
    print("\n0. Keluar")
    print("="*60)

def view_agendas():
    conn = get_db()
    agendas = conn.execute('SELECT * FROM agendas ORDER BY position').fetchall()
    conn.close()
    
    print("\n" + "="*60)
    print("DAFTAR AGENDA")
    print("="*60)
    
    if not agendas:
        print("\nTidak ada agenda.")
        return
    
    for agenda in agendas:
        status = "✓ Aktif" if agenda['is_active'] else "✗ Nonaktif"
        print(f"\nID: {agenda['id']} - Position: {agenda['position']} - {status}")
        print(f"Judul: {agenda['title']}")
        print(f"Deskripsi: {agenda['description']}")
        print(f"Media: {agenda['media_type']} - {agenda['media_path']}")
        print(f"Tanggal: {agenda['event_date']}")
        print("-" * 60)

def add_agenda():
    print("\n" + "="*60)
    print("TAMBAH AGENDA BARU")
    print("="*60)
    
    position = int(input("\nPosisi (1-3): "))
    title = input("Judul: ")
    description = input("Deskripsi: ")
    media_type = input("Tipe Media (photo/video): ")
    media_path = input("Path Media (contoh: static/uploads/foto.jpg): ")
    event_date = input("Tanggal Event (contoh: Rabu, 04 Februari 2026): ")
    
    conn = get_db()
    conn.execute('''
        INSERT INTO agendas (position, title, description, media_type, media_path, event_date)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (position, title, description, media_type, media_path, event_date))
    conn.commit()
    conn.close()
    
    print("\n✓ Agenda berhasil ditambahkan!")

def edit_agenda():
    view_agendas()
    
    agenda_id = int(input("\nMasukkan ID agenda yang ingin diedit: "))
    
    conn = get_db()
    agenda = conn.execute('SELECT * FROM agendas WHERE id = ?', (agenda_id,)).fetchone()
    
    if not agenda:
        print("\n✗ Agenda tidak ditemukan!")
        conn.close()
        return
    
    print("\nTekan Enter untuk melewati field yang tidak ingin diubah")
    
    position = input(f"Posisi [{agenda['position']}]: ") or agenda['position']
    title = input(f"Judul [{agenda['title']}]: ") or agenda['title']
    description = input(f"Deskripsi [{agenda['description']}]: ") or agenda['description']
    media_type = input(f"Tipe Media [{agenda['media_type']}]: ") or agenda['media_type']
    media_path = input(f"Path Media [{agenda['media_path']}]: ") or agenda['media_path']
    event_date = input(f"Tanggal [{agenda['event_date']}]: ") or agenda['event_date']
    
    conn.execute('''
        UPDATE agendas 
        SET position=?, title=?, description=?, media_type=?, media_path=?, event_date=?
        WHERE id=?
    ''', (position, title, description, media_type, media_path, event_date, agenda_id))
    conn.commit()
    conn.close()
    
    print("\n✓ Agenda berhasil diupdate!")

def delete_agenda():
    view_agendas()
    
    agenda_id = int(input("\nMasukkan ID agenda yang ingin dihapus: "))
    confirm = input(f"Yakin ingin menghapus agenda ID {agenda_id}? (y/n): ")
    
    if confirm.lower() == 'y':
        conn = get_db()
        conn.execute('DELETE FROM agendas WHERE id = ?', (agenda_id,))
        conn.commit()
        conn.close()
        print("\n✓ Agenda berhasil dihapus!")
    else:
        print("\n✗ Penghapusan dibatalkan.")

def toggle_agenda():
    view_agendas()
    
    agenda_id = int(input("\nMasukkan ID agenda: "))
    
    conn = get_db()
    agenda = conn.execute('SELECT is_active FROM agendas WHERE id = ?', (agenda_id,)).fetchone()
    
    if agenda:
        new_status = 0 if agenda['is_active'] else 1
        conn.execute('UPDATE agendas SET is_active = ? WHERE id = ?', (new_status, agenda_id))
        conn.commit()
        status_text = "diaktifkan" if new_status else "dinonaktifkan"
        print(f"\n✓ Agenda berhasil {status_text}!")
    else:
        print("\n✗ Agenda tidak ditemukan!")
    
    conn.close()

def view_news():
    conn = get_db()
    news_list = conn.execute('SELECT * FROM news ORDER BY created_at DESC').fetchall()
    conn.close()
    
    print("\n" + "="*60)
    print("DAFTAR BERITA")
    print("="*60)
    
    if not news_list:
        print("\nTidak ada berita.")
        return
    
    for news in news_list:
        status = "✓ Aktif" if news['is_active'] else "✗ Nonaktif"
        print(f"\nID: {news['id']} - {status}")
        print(f"Konten: {news['content']}")
        print(f"Dibuat: {news['created_at']}")
        print("-" * 60)

def add_news():
    print("\n" + "="*60)
    print("TAMBAH BERITA BARU")
    print("="*60)
    
    content = input("\nKonten berita: ")
    
    conn = get_db()
    conn.execute('INSERT INTO news (content) VALUES (?)', (content,))
    conn.commit()
    conn.close()
    
    print("\n✓ Berita berhasil ditambahkan!")

def edit_news():
    view_news()
    
    news_id = int(input("\nMasukkan ID berita yang ingin diedit: "))
    
    conn = get_db()
    news = conn.execute('SELECT * FROM news WHERE id = ?', (news_id,)).fetchone()
    
    if not news:
        print("\n✗ Berita tidak ditemukan!")
        conn.close()
        return
    
    print(f"\nKonten saat ini: {news['content']}")
    new_content = input("Konten baru: ")
    
    conn.execute('UPDATE news SET content = ? WHERE id = ?', (new_content, news_id))
    conn.commit()
    conn.close()
    
    print("\n✓ Berita berhasil diupdate!")

def delete_news():
    view_news()
    
    news_id = int(input("\nMasukkan ID berita yang ingin dihapus: "))
    confirm = input(f"Yakin ingin menghapus berita ID {news_id}? (y/n): ")
    
    if confirm.lower() == 'y':
        conn = get_db()
        conn.execute('DELETE FROM news WHERE id = ?', (news_id,))
        conn.commit()
        conn.close()
        print("\n✓ Berita berhasil dihapus!")
    else:
        print("\n✗ Penghapusan dibatalkan.")

def toggle_news():
    view_news()
    
    news_id = int(input("\nMasukkan ID berita: "))
    
    conn = get_db()
    news = conn.execute('SELECT is_active FROM news WHERE id = ?', (news_id,)).fetchone()
    
    if news:
        new_status = 0 if news['is_active'] else 1
        conn.execute('UPDATE news SET is_active = ? WHERE id = ?', (new_status, news_id))
        conn.commit()
        status_text = "diaktifkan" if new_status else "dinonaktifkan"
        print(f"\n✓ Berita berhasil {status_text}!")
    else:
        print("\n✗ Berita tidak ditemukan!")
    
    conn.close()

def view_photos():
    conn = get_db()
    photos = conn.execute('SELECT * FROM photos ORDER BY created_at DESC LIMIT 20').fetchall()
    conn.close()
    
    print("\n" + "="*60)
    print("DAFTAR FOTO (20 Terbaru)")
    print("="*60)
    
    if not photos:
        print("\nTidak ada foto.")
        return
    
    for photo in photos:
        print(f"\nID: {photo['id']}")
        print(f"Filename: {photo['filename']}")
        print(f"Path: {photo['filepath']}")
        print(f"Dibuat: {photo['created_at']}")
        print("-" * 60)

def delete_photo():
    view_photos()
    
    photo_id = int(input("\nMasukkan ID foto yang ingin dihapus: "))
    confirm = input(f"Yakin ingin menghapus foto ID {photo_id}? (y/n): ")
    
    if confirm.lower() == 'y':
        conn = get_db()
        photo = conn.execute('SELECT filepath FROM photos WHERE id = ?', (photo_id,)).fetchone()
        
        if photo:
            # Delete from database
            conn.execute('DELETE FROM photos WHERE id = ?', (photo_id,))
            conn.commit()
            
            # Delete file
            try:
                if os.path.exists(photo['filepath']):
                    os.remove(photo['filepath'])
                print("\n✓ Foto berhasil dihapus!")
            except Exception as e:
                print(f"\n⚠ Foto dihapus dari database, tapi file tidak dapat dihapus: {e}")
        else:
            print("\n✗ Foto tidak ditemukan!")
        
        conn.close()
    else:
        print("\n✗ Penghapusan dibatalkan.")

def main():
    if not os.path.exists('photostation.db'):
        print("\n✗ Database tidak ditemukan! Jalankan init_db.py terlebih dahulu.")
        return
    
    while True:
        show_menu()
        choice = input("\nPilih menu (0-12): ")
        
        try:
            if choice == '0':
                print("\nTerima kasih! Sampai jumpa.")
                break
            elif choice == '1':
                view_agendas()
            elif choice == '2':
                add_agenda()
            elif choice == '3':
                edit_agenda()
            elif choice == '4':
                delete_agenda()
            elif choice == '5':
                toggle_agenda()
            elif choice == '6':
                view_news()
            elif choice == '7':
                add_news()
            elif choice == '8':
                edit_news()
            elif choice == '9':
                delete_news()
            elif choice == '10':
                toggle_news()
            elif choice == '11':
                view_photos()
            elif choice == '12':
                delete_photo()
            else:
                print("\n✗ Pilihan tidak valid!")
            
            input("\nTekan Enter untuk melanjutkan...")
        except Exception as e:
            print(f"\n✗ Error: {e}")
            input("\nTekan Enter untuk melanjutkan...")

if __name__ == '__main__':
    main()

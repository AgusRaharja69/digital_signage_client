#!/usr/bin/env python3
"""
Digital Signage Data Manager
Program CLI untuk Add, Update, Delete data templates, advertisements, dan agendas
"""

import sqlite3
import os
import sys
from datetime import datetime

# Database path
DB_PATH = os.path.join(os.path.dirname(__file__), 'db', 'signage.db')

def get_db():
    """Get database connection"""
    if not os.path.exists(DB_PATH):
        print(f"\n❌ Database not found: {DB_PATH}")
        print("Please run: python3 init_db.py\n")
        sys.exit(1)
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def clear_screen():
    """Clear terminal screen"""
    os.system('clear' if os.name == 'posix' else 'cls')

# ========================================
# MENU SYSTEM
# ========================================

def show_main_menu():
    """Display main menu"""
    print("\n" + "="*70)
    print("   DIGITAL SIGNAGE DATA MANAGER")
    print("="*70)
    print("\n📋 TEMPLATE MANAGEMENT")
    print("  1. View All Templates")
    print("  2. Add New Template")
    print("  3. Update Template")
    print("  4. Delete Template")
    print("  5. Toggle Active/Inactive Template")
    
    print("\n📢 ADVERTISEMENT MANAGEMENT")
    print("  6. View All Advertisements")
    print("  7. Add New Advertisement")
    print("  8. Update Advertisement")
    print("  9. Delete Advertisement")
    print(" 10. Toggle Active/Inactive Advertisement")
    
    print("\n📅 AGENDA MANAGEMENT")
    print(" 11. View All Agendas")
    print(" 12. Add New Agenda")
    print(" 13. Update Agenda")
    print(" 14. Delete Agenda")
    print(" 15. Toggle Active/Inactive Agenda")
    
    print("\n📰 NEWS MANAGEMENT")
    print(" 16. View All News")
    print(" 17. Add New News")
    print(" 18. Update News")
    print(" 19. Delete News")
    print(" 20. Toggle Active/Inactive News")
    
    print("\n⚙️  SYSTEM")
    print(" 21. View Configuration")
    print(" 22. Update Configuration")
    
    print("\n  0. Exit")
    print("="*70)

# ========================================
# TEMPLATE MANAGEMENT
# ========================================

def view_templates():
    """View all templates"""
    conn = get_db()
    templates = conn.execute('SELECT * FROM templates ORDER BY display_order').fetchall()
    conn.close()
    
    print("\n" + "="*70)
    print("TEMPLATES LIST")
    print("="*70)
    
    if not templates:
        print("\n❌ No templates found.")
        return
    
    for tpl in templates:
        status = "✓ Active" if tpl['is_active'] else "✗ Inactive"
        print(f"\nID: {tpl['id']} | Order: {tpl['display_order']} | {status}")
        print(f"Type: {tpl['template_type']}")
        print(f"Name: {tpl['template_name']}")
        print(f"File: {tpl['file_path']}")
        print(f"Duration: {tpl['duration']} seconds")
        print(f"Created: {tpl['created_at']}")
        print("-" * 70)

def add_template():
    """Add new template"""
    print("\n" + "="*70)
    print("ADD NEW TEMPLATE")
    print("="*70)
    
    print("\nTemplate Types:")
    print("  1. html   - HTML layout (custom template)")
    print("  2. image  - Full screen image")
    print("  3. video  - Full screen video")
    
    template_type = input("\nSelect type (1-3): ").strip()
    
    type_map = {'1': 'html', '2': 'image', '3': 'video'}
    if template_type not in type_map:
        print("❌ Invalid selection!")
        return
    
    template_type = type_map[template_type]
    
    template_name = input("Template Name: ").strip()
    if not template_name:
        print("❌ Name is required!")
        return
    
    file_path = input(f"File Path (e.g., {'templates/custom.html' if template_type=='html' else 'static/uploads/file.jpg'}): ").strip()
    
    duration = input("Duration (seconds, default 10): ").strip()
    duration = int(duration) if duration.isdigit() else 10
    
    display_order = input("Display Order (default 99): ").strip()
    display_order = int(display_order) if display_order.isdigit() else 99
    
    # Insert
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO templates (template_type, template_name, file_path, duration, is_active, display_order)
        VALUES (?, ?, ?, ?, 1, ?)
    ''', (template_type, template_name, file_path, duration, display_order))
    
    template_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    print(f"\n✅ Template added successfully! ID: {template_id}")

def update_template():
    """Update existing template"""
    view_templates()
    
    template_id = input("\nEnter Template ID to update: ").strip()
    if not template_id.isdigit():
        print("❌ Invalid ID!")
        return
    
    conn = get_db()
    template = conn.execute('SELECT * FROM templates WHERE id = ?', (template_id,)).fetchone()
    
    if not template:
        print("\n❌ Template not found!")
        conn.close()
        return
    
    print("\n📝 Current values shown in [brackets]. Press Enter to skip.")
    
    template_name = input(f"Name [{template['template_name']}]: ").strip() or template['template_name']
    file_path = input(f"File Path [{template['file_path']}]: ").strip() or template['file_path']
    duration = input(f"Duration [{template['duration']}]: ").strip()
    duration = int(duration) if duration.isdigit() else template['duration']
    display_order = input(f"Display Order [{template['display_order']}]: ").strip()
    display_order = int(display_order) if display_order.isdigit() else template['display_order']
    
    conn.execute('''
        UPDATE templates 
        SET template_name=?, file_path=?, duration=?, display_order=?, updated_at=CURRENT_TIMESTAMP
        WHERE id=?
    ''', (template_name, file_path, duration, display_order, template_id))
    
    conn.commit()
    conn.close()
    
    print("\n✅ Template updated successfully!")

def delete_template():
    """Delete template"""
    view_templates()
    
    template_id = input("\nEnter Template ID to delete: ").strip()
    if not template_id.isdigit():
        print("❌ Invalid ID!")
        return
    
    confirm = input(f"⚠️  Delete template ID {template_id}? (yes/no): ").strip().lower()
    
    if confirm == 'yes':
        conn = get_db()
        conn.execute('DELETE FROM templates WHERE id = ?', (template_id,))
        conn.commit()
        conn.close()
        print("\n✅ Template deleted!")
    else:
        print("\n❌ Cancelled.")

def toggle_template():
    """Toggle template active status"""
    view_templates()
    
    template_id = input("\nEnter Template ID to toggle: ").strip()
    if not template_id.isdigit():
        print("❌ Invalid ID!")
        return
    
    conn = get_db()
    template = conn.execute('SELECT is_active FROM templates WHERE id = ?', (template_id,)).fetchone()
    
    if template:
        new_status = 0 if template['is_active'] else 1
        conn.execute('UPDATE templates SET is_active = ?, updated_at=CURRENT_TIMESTAMP WHERE id = ?', 
                    (new_status, template_id))
        conn.commit()
        status_text = "activated" if new_status else "deactivated"
        print(f"\n✅ Template {status_text}!")
    else:
        print("\n❌ Template not found!")
    
    conn.close()

# ========================================
# ADVERTISEMENT MANAGEMENT
# ========================================

def view_advertisements():
    """View all advertisements"""
    conn = get_db()
    ads = conn.execute('SELECT * FROM advertisements ORDER BY display_order').fetchall()
    conn.close()
    
    print("\n" + "="*70)
    print("ADVERTISEMENTS LIST")
    print("="*70)
    
    if not ads:
        print("\n❌ No advertisements found.")
        return
    
    for ad in ads:
        status = "✓ Active" if ad['is_active'] else "✗ Inactive"
        print(f"\nID: {ad['id']} | Order: {ad['display_order']} | {status}")
        print(f"Name: {ad['ad_name']}")
        print(f"Type: {ad['ad_type']}")
        print(f"File: {ad['file_path']}")
        print(f"Duration: {ad['duration']} seconds")
        print(f"Trigger Time: {ad['trigger_time']} seconds before template ends")
        print(f"Position: {ad['position']}")
        print(f"Created: {ad['created_at']}")
        print("-" * 70)

def add_advertisement():
    """Add new advertisement"""
    print("\n" + "="*70)
    print("ADD NEW ADVERTISEMENT")
    print("="*70)
    
    print("\nAdvertisement Types:")
    print("  1. image  - Image advertisement")
    print("  2. video  - Video advertisement")
    
    ad_type = input("\nSelect type (1-2): ").strip()
    type_map = {'1': 'image', '2': 'video'}
    
    if ad_type not in type_map:
        print("❌ Invalid selection!")
        return
    
    ad_type = type_map[ad_type]
    
    ad_name = input("Advertisement Name: ").strip()
    if not ad_name:
        print("❌ Name is required!")
        return
    
    file_path = input("File Path (e.g., static/uploads/ads/ad1.jpg): ").strip()
    
    duration = input("Duration (seconds, default 10): ").strip()
    duration = int(duration) if duration.isdigit() else 10
    
    print("\nPositions:")
    print("  1. bottom-right")
    print("  2. bottom-left")
    print("  3. top-right")
    print("  4. top-left")
    
    position = input("Select position (1-4, default 1): ").strip()
    position_map = {
        '1': 'bottom-right',
        '2': 'bottom-left',
        '3': 'top-right',
        '4': 'top-left'
    }
    position = position_map.get(position, 'bottom-right')
    
    trigger_time = input("Trigger Time (seconds before template ends, default 10): ").strip()
    trigger_time = int(trigger_time) if trigger_time.isdigit() else 10
    
    display_order = input("Display Order (default 99): ").strip()
    display_order = int(display_order) if display_order.isdigit() else 99
    
    # Insert
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO advertisements 
        (ad_name, ad_type, file_path, duration, position, trigger_time, is_active, display_order)
        VALUES (?, ?, ?, ?, ?, ?, 1, ?)
    ''', (ad_name, ad_type, file_path, duration, position, trigger_time, display_order))
    
    ad_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    print(f"\n✅ Advertisement added successfully! ID: {ad_id}")

def update_advertisement():
    """Update existing advertisement"""
    view_advertisements()
    
    ad_id = input("\nEnter Advertisement ID to update: ").strip()
    if not ad_id.isdigit():
        print("❌ Invalid ID!")
        return
    
    conn = get_db()
    ad = conn.execute('SELECT * FROM advertisements WHERE id = ?', (ad_id,)).fetchone()
    
    if not ad:
        print("\n❌ Advertisement not found!")
        conn.close()
        return
    
    print("\n📝 Current values shown in [brackets]. Press Enter to skip.")
    
    ad_name = input(f"Name [{ad['ad_name']}]: ").strip() or ad['ad_name']
    file_path = input(f"File Path [{ad['file_path']}]: ").strip() or ad['file_path']
    duration = input(f"Duration [{ad['duration']}]: ").strip()
    duration = int(duration) if duration.isdigit() else ad['duration']
    trigger_time = input(f"Trigger Time [{ad['trigger_time']}]: ").strip()
    trigger_time = int(trigger_time) if trigger_time.isdigit() else ad['trigger_time']
    
    print(f"\nCurrent position: {ad['position']}")
    print("Positions: bottom-right, bottom-left, top-right, top-left")
    position = input(f"New position (Enter to skip): ").strip() or ad['position']
    
    display_order = input(f"Display Order [{ad['display_order']}]: ").strip()
    display_order = int(display_order) if display_order.isdigit() else ad['display_order']
    
    conn.execute('''
        UPDATE advertisements 
        SET ad_name=?, file_path=?, duration=?, position=?, trigger_time=?, display_order=?, 
            updated_at=CURRENT_TIMESTAMP
        WHERE id=?
    ''', (ad_name, file_path, duration, position, trigger_time, display_order, ad_id))
    
    conn.commit()
    conn.close()
    
    print("\n✅ Advertisement updated successfully!")

def delete_advertisement():
    """Delete advertisement"""
    view_advertisements()
    
    ad_id = input("\nEnter Advertisement ID to delete: ").strip()
    if not ad_id.isdigit():
        print("❌ Invalid ID!")
        return
    
    confirm = input(f"⚠️  Delete advertisement ID {ad_id}? (yes/no): ").strip().lower()
    
    if confirm == 'yes':
        conn = get_db()
        conn.execute('DELETE FROM advertisements WHERE id = ?', (ad_id,))
        conn.commit()
        conn.close()
        print("\n✅ Advertisement deleted!")
    else:
        print("\n❌ Cancelled.")

def toggle_advertisement():
    """Toggle advertisement active status"""
    view_advertisements()
    
    ad_id = input("\nEnter Advertisement ID to toggle: ").strip()
    if not ad_id.isdigit():
        print("❌ Invalid ID!")
        return
    
    conn = get_db()
    ad = conn.execute('SELECT is_active FROM advertisements WHERE id = ?', (ad_id,)).fetchone()
    
    if ad:
        new_status = 0 if ad['is_active'] else 1
        conn.execute('UPDATE advertisements SET is_active = ?, updated_at=CURRENT_TIMESTAMP WHERE id = ?', 
                    (new_status, ad_id))
        conn.commit()
        status_text = "activated" if new_status else "deactivated"
        print(f"\n✅ Advertisement {status_text}!")
    else:
        print("\n❌ Advertisement not found!")
    
    conn.close()

# ========================================
# AGENDA MANAGEMENT
# ========================================

def view_agendas():
    """View all agendas"""
    conn = get_db()
    agendas = conn.execute('SELECT * FROM agendas ORDER BY position').fetchall()
    conn.close()
    
    print("\n" + "="*70)
    print("AGENDAS LIST")
    print("="*70)
    
    if not agendas:
        print("\n❌ No agendas found.")
        return
    
    for agenda in agendas:
        status = "✓ Active" if agenda['is_active'] else "✗ Inactive"
        print(f"\nID: {agenda['id']} | Position: {agenda['position']} | {status}")
        print(f"Title: {agenda['title']}")
        print(f"Description: {agenda['description'][:50]}...")
        print(f"Media: {agenda['media_type']} - {agenda['media_path']}")
        print(f"Event Date: {agenda['event_date']}")
        print(f"Created: {agenda['created_at']}")
        print("-" * 70)

def add_agenda():
    """Add new agenda"""
    print("\n" + "="*70)
    print("ADD NEW AGENDA")
    print("="*70)
    
    position = input("\nPosition (1-3): ").strip()
    if not position.isdigit() or int(position) < 1 or int(position) > 3:
        print("❌ Position must be 1-3!")
        return
    
    title = input("Title: ").strip()
    if not title:
        print("❌ Title is required!")
        return
    
    description = input("Description: ").strip()
    
    print("\nMedia Types:")
    print("  1. photo")
    print("  2. video")
    
    media_type = input("Select media type (1-2): ").strip()
    media_type = 'photo' if media_type == '1' else 'video'
    
    media_path = input(f"Media Path (e.g., static/uploads/{'photo.jpg' if media_type=='photo' else 'video.mp4'}): ").strip()
    
    event_date = input("Event Date (e.g., Senin, 20 Februari 2026): ").strip()
    
    # Insert
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO agendas (position, title, description, media_type, media_path, event_date, is_active)
        VALUES (?, ?, ?, ?, ?, ?, 1)
    ''', (position, title, description, media_type, media_path, event_date))
    
    agenda_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    print(f"\n✅ Agenda added successfully! ID: {agenda_id}")

def update_agenda():
    """Update existing agenda"""
    view_agendas()
    
    agenda_id = input("\nEnter Agenda ID to update: ").strip()
    if not agenda_id.isdigit():
        print("❌ Invalid ID!")
        return
    
    conn = get_db()
    agenda = conn.execute('SELECT * FROM agendas WHERE id = ?', (agenda_id,)).fetchone()
    
    if not agenda:
        print("\n❌ Agenda not found!")
        conn.close()
        return
    
    print("\n📝 Current values shown in [brackets]. Press Enter to skip.")
    
    title = input(f"Title [{agenda['title']}]: ").strip() or agenda['title']
    description = input(f"Description [{agenda['description'][:30]}...]: ").strip() or agenda['description']
    media_path = input(f"Media Path [{agenda['media_path']}]: ").strip() or agenda['media_path']
    event_date = input(f"Event Date [{agenda['event_date']}]: ").strip() or agenda['event_date']
    
    conn.execute('''
        UPDATE agendas 
        SET title=?, description=?, media_path=?, event_date=?, updated_at=CURRENT_TIMESTAMP
        WHERE id=?
    ''', (title, description, media_path, event_date, agenda_id))
    
    conn.commit()
    conn.close()
    
    print("\n✅ Agenda updated successfully!")

def delete_agenda():
    """Delete agenda"""
    view_agendas()
    
    agenda_id = input("\nEnter Agenda ID to delete: ").strip()
    if not agenda_id.isdigit():
        print("❌ Invalid ID!")
        return
    
    confirm = input(f"⚠️  Delete agenda ID {agenda_id}? (yes/no): ").strip().lower()
    
    if confirm == 'yes':
        conn = get_db()
        conn.execute('DELETE FROM agendas WHERE id = ?', (agenda_id,))
        conn.commit()
        conn.close()
        print("\n✅ Agenda deleted!")
    else:
        print("\n❌ Cancelled.")

def toggle_agenda():
    """Toggle agenda active status"""
    view_agendas()
    
    agenda_id = input("\nEnter Agenda ID to toggle: ").strip()
    if not agenda_id.isdigit():
        print("❌ Invalid ID!")
        return
    
    conn = get_db()
    agenda = conn.execute('SELECT is_active FROM agendas WHERE id = ?', (agenda_id,)).fetchone()
    
    if agenda:
        new_status = 0 if agenda['is_active'] else 1
        conn.execute('UPDATE agendas SET is_active = ?, updated_at=CURRENT_TIMESTAMP WHERE id = ?', 
                    (new_status, agenda_id))
        conn.commit()
        status_text = "activated" if new_status else "deactivated"
        print(f"\n✅ Agenda {status_text}!")
    else:
        print("\n❌ Agenda not found!")
    
    conn.close()

# ========================================
# NEWS MANAGEMENT
# ========================================

def view_news():
    """View all news"""
    conn = get_db()
    news_list = conn.execute('SELECT * FROM news ORDER BY created_at DESC').fetchall()
    conn.close()
    
    print("\n" + "="*70)
    print("NEWS LIST")
    print("="*70)
    
    if not news_list:
        print("\n❌ No news found.")
        return
    
    for news in news_list:
        status = "✓ Active" if news['is_active'] else "✗ Inactive"
        print(f"\nID: {news['id']} | {status}")
        print(f"Content: {news['content']}")
        print(f"Created: {news['created_at']}")
        print("-" * 70)

def add_news():
    """Add new news"""
    print("\n" + "="*70)
    print("ADD NEW NEWS")
    print("="*70)
    
    content = input("\nNews Content: ").strip()
    if not content:
        print("❌ Content is required!")
        return
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO news (content, is_active) VALUES (?, 1)', (content,))
    
    news_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    print(f"\n✅ News added successfully! ID: {news_id}")

def update_news():
    """Update existing news"""
    view_news()
    
    news_id = input("\nEnter News ID to update: ").strip()
    if not news_id.isdigit():
        print("❌ Invalid ID!")
        return
    
    conn = get_db()
    news = conn.execute('SELECT * FROM news WHERE id = ?', (news_id,)).fetchone()
    
    if not news:
        print("\n❌ News not found!")
        conn.close()
        return
    
    print(f"\n📝 Current: {news['content']}")
    new_content = input("New Content: ").strip()
    
    if not new_content:
        print("❌ Content cannot be empty!")
        conn.close()
        return
    
    conn.execute('UPDATE news SET content = ?, updated_at=CURRENT_TIMESTAMP WHERE id = ?', 
                (new_content, news_id))
    conn.commit()
    conn.close()
    
    print("\n✅ News updated successfully!")

def delete_news():
    """Delete news"""
    view_news()
    
    news_id = input("\nEnter News ID to delete: ").strip()
    if not news_id.isdigit():
        print("❌ Invalid ID!")
        return
    
    confirm = input(f"⚠️  Delete news ID {news_id}? (yes/no): ").strip().lower()
    
    if confirm == 'yes':
        conn = get_db()
        conn.execute('DELETE FROM news WHERE id = ?', (news_id,))
        conn.commit()
        conn.close()
        print("\n✅ News deleted!")
    else:
        print("\n❌ Cancelled.")

def toggle_news():
    """Toggle news active status"""
    view_news()
    
    news_id = input("\nEnter News ID to toggle: ").strip()
    if not news_id.isdigit():
        print("❌ Invalid ID!")
        return
    
    conn = get_db()
    news = conn.execute('SELECT is_active FROM news WHERE id = ?', (news_id,)).fetchone()
    
    if news:
        new_status = 0 if news['is_active'] else 1
        conn.execute('UPDATE news SET is_active = ?, updated_at=CURRENT_TIMESTAMP WHERE id = ?', 
                    (new_status, news_id))
        conn.commit()
        status_text = "activated" if new_status else "deactivated"
        print(f"\n✅ News {status_text}!")
    else:
        print("\n❌ News not found!")
    
    conn.close()

# ========================================
# CONFIGURATION MANAGEMENT
# ========================================

def view_config():
    """View system configuration"""
    conn = get_db()
    configs = conn.execute('SELECT * FROM config ORDER BY key').fetchall()
    conn.close()
    
    print("\n" + "="*70)
    print("SYSTEM CONFIGURATION")
    print("="*70)
    
    for cfg in configs:
        print(f"\n{cfg['key']:20s}: {cfg['value']}")
        if cfg['description']:
            print(f"{'':20s}  ({cfg['description']})")
    
    print("-" * 70)

def update_config():
    """Update configuration"""
    view_config()
    
    key = input("\nEnter config key to update: ").strip()
    if not key:
        print("❌ Key is required!")
        return
    
    conn = get_db()
    cfg = conn.execute('SELECT * FROM config WHERE key = ?', (key,)).fetchone()
    
    if not cfg:
        print(f"\n❌ Config key '{key}' not found!")
        conn.close()
        return
    
    print(f"\n📝 Current value: {cfg['value']}")
    new_value = input("New value: ").strip()
    
    if not new_value:
        print("❌ Value cannot be empty!")
        conn.close()
        return
    
    conn.execute('''
        UPDATE config 
        SET value = ?, updated_at=CURRENT_TIMESTAMP 
        WHERE key = ?
    ''', (new_value, key))
    
    conn.commit()
    conn.close()
    
    print(f"\n✅ Config '{key}' updated successfully!")

# ========================================
# MAIN PROGRAM
# ========================================

def main():
    """Main program loop"""
    
    # Check database
    if not os.path.exists(DB_PATH):
        print(f"\n❌ Database not found: {DB_PATH}")
        print("Please run: python3 init_db.py\n")
        sys.exit(1)
    
    # Menu mapping
    menu_functions = {
        '1': view_templates,
        '2': add_template,
        '3': update_template,
        '4': delete_template,
        '5': toggle_template,
        '6': view_advertisements,
        '7': add_advertisement,
        '8': update_advertisement,
        '9': delete_advertisement,
        '10': toggle_advertisement,
        '11': view_agendas,
        '12': add_agenda,
        '13': update_agenda,
        '14': delete_agenda,
        '15': toggle_agenda,
        '16': view_news,
        '17': add_news,
        '18': update_news,
        '19': delete_news,
        '20': toggle_news,
        '21': view_config,
        '22': update_config,
    }
    
    while True:
        show_main_menu()
        choice = input("\nSelect menu (0-22): ").strip()
        
        try:
            if choice == '0':
                print("\n👋 Goodbye!\n")
                break
            
            elif choice in menu_functions:
                menu_functions[choice]()
            
            else:
                print("\n❌ Invalid choice!")
            
            input("\nPress Enter to continue...")
        
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!\n")
            break
        
        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()
            input("\nPress Enter to continue...")

if __name__ == '__main__':
    main()

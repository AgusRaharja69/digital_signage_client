#!/usr/bin/env python3
"""
mqtt_update.py — Digital Signage MQTT Update Handler
Format payload TUNGGAL untuk semua tabel.

Field → Kolom database:
  title       → template_name (templates) | ad_name (advertisements) | title (agendas)
  content     → content (news) | value (config, alias)
  media_type  → template_type | ad_type | media_type  [text|image|video]
  media_path  → file_path (templates/ads) | media_path (agendas)
  key+value   → key+value (config)
"""

import paho.mqtt.client as mqtt
import sqlite3
import json
import os
import sys
import time
import configparser
from datetime import datetime

# ── Config ────────────────────────────────────────────────────────────────────
_cfg = configparser.ConfigParser()
_cfg.read(os.path.join(os.path.dirname(__file__), 'config.ini'))

BROKER    = _cfg['DEFAULT']['Broker']
PORT      = int(_cfg['DEFAULT']['Port'])
USERNAME  = _cfg['DEFAULT']['UserID']
PASSWORD  = _cfg['DEFAULT']['Pass']
KEEPALIVE = int(_cfg['DEFAULT']['KAI'])

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'photostation.db')

TOPIC = "signage/sma-n-1-denpasar/content"


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ── Download media jika ada media_url ────────────────────────────────────────
def maybe_download_media(p: dict) -> str:
    media_url  = p.get('media_url')
    media_path = p.get('media_path') or ''
    if not media_url:
        return media_path
    if not media_path:
        ext        = media_url.split('?')[0].rsplit('.', 1)[-1].lower() or 'jpg'
        media_path = f"static/uploads/media_{int(time.time())}.{ext}"
    full_path = os.path.join(os.path.dirname(DB_PATH), media_path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    try:
        import urllib.request
        print(f'[MQTT] Download: {media_url} → {media_path}')
        urllib.request.urlretrieve(media_url, full_path)
        print(f'[MQTT] Download OK: {media_path}')
    except Exception as e:
        print(f'[MQTT] Download gagal: {e}')
    return media_path


# ══════════════════════════════════════════════════════════════════════════════
# HANDLERS
# ══════════════════════════════════════════════════════════════════════════════

def handle_news(p: dict, action: str) -> str:
    """
    Tabel  : news
    Kolom  : id | content | is_active | created_at
    Payload: content_id, content, is_active
    """
    conn = get_db()
    try:
        if action == 'add':
            content = p.get('content', '')
            if not content:
                return "news add gagal: content kosong"
            conn.execute(
                'INSERT INTO news (content, is_active) VALUES (?, ?)',
                (content, p.get('is_active', 1))
            )
            conn.commit()
            return f'news added: "{content[:60]}"'

        elif action == 'update':
            cid = p.get('content_id')
            if not cid:
                return "news update gagal: content_id null"
            conn.execute('''
                UPDATE news SET
                    content   = COALESCE(?, content),
                    is_active = COALESCE(?, is_active)
                WHERE id = ?
            ''', (p.get('content'), p.get('is_active'), cid))
            conn.commit()
            return f"news {cid} updated"

        elif action == 'delete':
            cid = p.get('content_id')
            if not cid:
                return "news delete gagal: content_id null"
            conn.execute('UPDATE news SET is_active=0 WHERE id=?', (cid,))
            conn.commit()
            return f"news {cid} deleted"

        elif action == 'clear_all':
            conn.execute('UPDATE news SET is_active=0')
            conn.commit()
            return "semua news dinonaktifkan"

        return f"news: action '{action}' tidak dikenal"
    finally:
        conn.close()


def handle_agenda(p: dict, action: str) -> str:
    """
    Tabel  : agendas
    Kolom  : id | position | title | description | media_type | media_path
             | event_date | event_time | is_active | created_at
    Payload: content_id, title, description, media_type, media_path,
             media_url, event_date, event_time, position, is_active
    """
    media_path = maybe_download_media(p)
    conn = get_db()
    try:
        if action == 'add':
            conn.execute('''
                INSERT INTO agendas
                    (position, title, description, media_type,
                     media_path, event_date, event_time, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                p.get('position', 99),
                p.get('title', 'Agenda Baru'),
                p.get('description', ''),
                p.get('media_type', 'text'),
                media_path,
                p.get('event_date', ''),
                p.get('event_time', ''),
                p.get('is_active', 1),
            ))
            conn.commit()
            return f"agenda added: \"{p.get('title')}\""

        elif action == 'update':
            cid = p.get('content_id')
            if not cid:
                return "agenda update gagal: content_id null"
            conn.execute('''
                UPDATE agendas SET
                    position    = COALESCE(?, position),
                    title       = COALESCE(?, title),
                    description = COALESCE(?, description),
                    media_type  = COALESCE(?, media_type),
                    media_path  = COALESCE(?, media_path),
                    event_date  = COALESCE(?, event_date),
                    event_time  = COALESCE(?, event_time),
                    is_active   = COALESCE(?, is_active)
                WHERE id = ?
            ''', (
                p.get('position'), p.get('title'), p.get('description'),
                p.get('media_type'), media_path or None,
                p.get('event_date'), p.get('event_time'),
                p.get('is_active'), cid,
            ))
            conn.commit()
            return f"agenda {cid} updated"

        elif action == 'delete':
            cid = p.get('content_id')
            if not cid:
                return "agenda delete gagal: content_id null"
            conn.execute('UPDATE agendas SET is_active=0 WHERE id=?', (cid,))
            conn.commit()
            return f"agenda {cid} deleted"

        return f"agenda: action '{action}' tidak dikenal"
    finally:
        conn.close()


def handle_template(p: dict, action: str) -> str:
    """
    Tabel  : templates
    Kolom  : id | template_name | template_type | file_path | duration
             | display_order | is_active | created_at
    Payload: content_id, title→template_name, media_type→template_type,
             media_path→file_path, media_url, duration, display_order, is_active
    """
    media_path = maybe_download_media(p)
    conn = get_db()
    try:
        if action == 'add':
            conn.execute('''
                INSERT INTO templates
                    (template_name, template_type, file_path,
                     duration, display_order, is_active)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                p.get('title', 'Template Baru'),
                p.get('media_type', 'image'),
                media_path,
                p.get('duration', 10),
                p.get('display_order', 99),
                p.get('is_active', 1),
            ))
            conn.commit()
            return f"template added: \"{p.get('title')}\""

        elif action == 'update':
            cid = p.get('content_id')
            if not cid:
                return "template update gagal: content_id null"
            conn.execute('''
                UPDATE templates SET
                    template_name = COALESCE(?, template_name),
                    template_type = COALESCE(?, template_type),
                    file_path     = COALESCE(?, file_path),
                    duration      = COALESCE(?, duration),
                    display_order = COALESCE(?, display_order),
                    is_active     = COALESCE(?, is_active)
                WHERE id = ?
            ''', (
                p.get('title'), p.get('media_type'),
                media_path or None, p.get('duration'),
                p.get('display_order'), p.get('is_active'), cid,
            ))
            conn.commit()
            return f"template {cid} updated"

        elif action == 'delete':
            cid = p.get('content_id')
            if not cid:
                return "template delete gagal: content_id null"
            conn.execute('UPDATE templates SET is_active=0 WHERE id=?', (cid,))
            conn.commit()
            return f"template {cid} deleted"

        return f"template: action '{action}' tidak dikenal"
    finally:
        conn.close()


def handle_advertisement(p: dict, action: str) -> str:
    """
    Tabel  : advertisements
    Kolom  : id | ad_name | ad_type | file_path | duration | trigger_time
             | display_order | is_active | created_at
    Payload: content_id, title→ad_name, media_type→ad_type,
             media_path→file_path, media_url, duration, trigger_time,
             display_order, is_active
    """
    media_path = maybe_download_media(p)
    conn = get_db()
    try:
        if action == 'add':
            conn.execute('''
                INSERT INTO advertisements
                    (ad_name, ad_type, file_path, duration,
                     trigger_time, display_order, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                p.get('title', 'Iklan Baru'),
                p.get('media_type', 'image'),
                media_path,
                p.get('duration', 10),
                p.get('trigger_time', 10),
                p.get('display_order', 99),
                p.get('is_active', 1),
            ))
            conn.commit()
            return f"advertisement added: \"{p.get('title')}\""

        elif action == 'update':
            cid = p.get('content_id')
            if not cid:
                return "advertisement update gagal: content_id null"
            conn.execute('''
                UPDATE advertisements SET
                    ad_name       = COALESCE(?, ad_name),
                    ad_type       = COALESCE(?, ad_type),
                    file_path     = COALESCE(?, file_path),
                    duration      = COALESCE(?, duration),
                    trigger_time  = COALESCE(?, trigger_time),
                    display_order = COALESCE(?, display_order),
                    is_active     = COALESCE(?, is_active)
                WHERE id = ?
            ''', (
                p.get('title'), p.get('media_type'),
                media_path or None, p.get('duration'),
                p.get('trigger_time'), p.get('display_order'),
                p.get('is_active'), cid,
            ))
            conn.commit()
            return f"advertisement {cid} updated"

        elif action == 'delete':
            cid = p.get('content_id')
            if not cid:
                return "advertisement delete gagal: content_id null"
            conn.execute('UPDATE advertisements SET is_active=0 WHERE id=?', (cid,))
            conn.commit()
            return f"advertisement {cid} deleted"

        return f"advertisement: action '{action}' tidak dikenal"
    finally:
        conn.close()


def handle_config(p: dict, action: str) -> str:
    """
    Tabel  : config
    Kolom  : key | value | updated_at
    Payload: key, value (atau content sebagai alias value)

    Keys tersedia:
      main_color, secondary_color, bg_color
      time_on, time_off, date_off
      logo_univ, logo_sekolah, barcode_boot, school_name
      wifi_ssid, wifi_password
      photo_drive_webhook
    """
    conn = get_db()
    try:
        if action in ('add', 'update'):
            key = p.get('key')
            val = p.get('value') if p.get('value') is not None else p.get('content')
            if not key:
                return "config update gagal: key null"
            conn.execute('''
                INSERT OR REPLACE INTO config (key, value, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
            ''', (key, str(val) if val is not None else ''))
            conn.commit()
            return f"config updated: {key} = {val}"

        elif action == 'delete':
            key = p.get('key')
            if not key:
                return "config delete gagal: key null"
            conn.execute('DELETE FROM config WHERE key=?', (key,))
            conn.commit()
            return f"config deleted: {key}"

        return f"config: action '{action}' tidak dikenal"
    finally:
        conn.close()


def handle_system(p: dict, action: str) -> str:
    """
    Perintah sistem (tidak menyentuh database).
    action=reload → tulis .reload_signal untuk trigger browser refresh
    """
    if action == 'reload':
        path = os.path.join(os.path.dirname(DB_PATH), '.reload_signal')
        with open(path, 'w') as f:
            f.write(datetime.now().isoformat())
        return "reload signal written"
    return f"system: action '{action}' tidak dikenal"


# ── Router ────────────────────────────────────────────────────────────────────
HANDLERS = {
    'news':          handle_news,
    'text':          handle_news,
    'agenda':        handle_agenda,
    'template':      handle_template,
    'advertisement': handle_advertisement,
    'ads':           handle_advertisement,
    'config':        handle_config,
    'system':        handle_system,
}


# ══════════════════════════════════════════════════════════════════════════════
# MQTT
# ══════════════════════════════════════════════════════════════════════════════

def on_connect(client, userdata, flags, rc):
    codes = {0:'OK',1:'Bad protocol',2:'Client ID rejected',
             3:'Unavailable',4:'Bad credentials',5:'Not authorized'}
    print(f"[MQTT] Connect: {codes.get(rc, rc)}")
    if rc == 0:
        client.subscribe(TOPIC, qos=1)
        print(f"[MQTT] Subscribed: {TOPIC}")


def on_disconnect(client, userdata, rc):
    print(f"[MQTT] Disconnected rc={rc}")


def on_message(client, userdata, msg):
    ts  = datetime.now().strftime('%H:%M:%S')
    raw = msg.payload.decode('utf-8')
    print(f"\n[{ts}] 📩 {msg.topic}")
    print(f"  {raw[:180]}{'...' if len(raw)>180 else ''}")

    try:
        p = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"  ❌ JSON error: {e}"); return

    msg_type = str(p.get('type',   '')).lower().strip()
    action   = str(p.get('action', 'add')).lower().strip()
    handler  = HANDLERS.get(msg_type)

    if not handler:
        print(f"  ⚠ type '{msg_type}' tidak dikenal. Tersedia: {list(HANDLERS)}")
        return

    try:
        result = handler(p, action)
        print(f"  ✅ {result}")
    except Exception as e:
        print(f"  ❌ Error: {e}")
        import traceback; traceback.print_exc()


if __name__ == '__main__':
    print("="*60)
    print("  Digital Signage — MQTT Handler")
    print(f"  Broker : {BROKER}:{PORT}")
    print(f"  Topic  : {TOPIC}")
    print(f"  DB     : {DB_PATH}")
    print("="*60)

    if not os.path.exists(DB_PATH):
        print(f"❌ DB tidak ada: {DB_PATH}")
        print("   python3 sample_data.py --migrate")
        sys.exit(1)

    client = mqtt.Client(protocol=mqtt.MQTTv311)
    client.username_pw_set(USERNAME, PASSWORD)
    client.on_connect    = on_connect
    client.on_disconnect = on_disconnect
    client.on_message    = on_message

    try:
        client.connect(BROKER, PORT, KEEPALIVE)
    except Exception as e:
        print(f"❌ Koneksi gagal: {e}"); sys.exit(1)

    try:
        client.loop_forever()
    except KeyboardInterrupt:
        print("\n🛑 Dihentikan")
        client.disconnect()
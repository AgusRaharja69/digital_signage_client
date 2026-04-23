#!/usr/bin/env python3
"""
mqtt_update.py — Digital Signage MQTT Update Handler v2
Format payload TUNGGAL untuk semua tabel.

Field → Kolom database:
  title       → template_name (templates) | ad_name (advertisements) | title (agendas)
  content     → content (news) | value (config, alias)
  media_type  → template_type | ad_type | media_type  [text|image|video]
  media_path  → file_path (templates/ads) | media_path (agendas)
  media_url   → download otomatis jika media_path kosong
  key+value   → key+value (config)

Contoh payload:
  {
    "id": "uuid",
    "content_id": 3,
    "type": "image",
    "title": "Ini Sekolah Kami",
    "content": "Deskripsi",
    "media_path": null,
    "media_url": "https://example.com/foto.png",
    "duration": 10,
    "action": "add",
    "publisher": "school",
    "event_date": null
  }
"""

import paho.mqtt.client as mqtt
import sqlite3
import json
import os
import sys
import time
import configparser
import threading
import subprocess
from datetime import datetime

# ── Config ────────────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_cfg = configparser.ConfigParser()
_cfg_path = os.path.join(BASE_DIR, 'config.ini')

if not os.path.exists(_cfg_path):
    print(f"[MQTT] config.ini tidak ditemukan: {_cfg_path}")
    print("[MQTT] Membuat config.ini default...")
    _cfg['DEFAULT'] = {
        'Broker':   'broker.hivemq.com',
        'Port':     '1883',
        'UserID':   '',
        'Pass':     '',
        'KAI':      '60',
        'Topic':    'signage/default',
    }
    with open(_cfg_path, 'w') as f:
        _cfg.write(f)
    print(f"[MQTT] Edit {_cfg_path} lalu jalankan ulang.")
    sys.exit(1)

_cfg.read(_cfg_path)

BROKER    = _cfg['DEFAULT'].get('Broker',  'broker.hivemq.com')
PORT      = int(_cfg['DEFAULT'].get('Port', '1883'))
USERNAME  = _cfg['DEFAULT'].get('UserID', '')
PASSWORD  = _cfg['DEFAULT'].get('Pass',   '')
KEEPALIVE = int(_cfg['DEFAULT'].get('KAI', '60'))
TOPIC     = _cfg['DEFAULT'].get('Topic',  'signage/default')
# TOPIC = "signage/sma-n-1-tabanan/"

DB_PATH = os.path.abspath(os.path.join(BASE_DIR, '..', 'db', 'photostation.db'))

# ── Reconnect state ───────────────────────────────────────────────────────────
_reconnect_delay = 5   # detik, naik eksponensial sampai 120s
_connected       = False


# ── DB helper ─────────────────────────────────────────────────────────────────
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ── Download media ────────────────────────────────────────────────────────────
def maybe_download_media(p: dict) -> str:
    """
    Download file dari media_url jika ada.
    Return media_path yang akan disimpan ke DB.
    """
    media_url  = p.get('media_url')
    media_path = p.get('media_path') or ''

    if not media_url:
        return media_path

    if not media_path:
        ext        = media_url.split('?')[0].rsplit('.', 1)[-1].lower() or 'jpg'
        ts         = int(time.time())
        media_path = f"static/uploads/media_{ts}.{ext}"

    full_path = os.path.join(BASE_DIR, '..', media_path)
    full_path = os.path.normpath(full_path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)

    # try:
    #     import urllib.request
    #     import urllib.error
    #     print(f'[MQTT] Download: {media_url}')
    #     print(f'[MQTT]        → {media_path}')

    #     req = urllib.request.Request(
    #         media_url,
    #         headers={'User-Agent': 'DigitalSignage/2.0'}
    #     )
    #     with urllib.request.urlopen(req, timeout=30) as resp:
    #         with open(full_path, 'wb') as f:
    #             f.write(resp.read())
    #     print(f'[MQTT] Download OK ({os.path.getsize(full_path)//1024} KB)')

    # except Exception as e:
    #     print(f'[MQTT] Download gagal: {e}')
    #     media_path = p.get('media_path') or ''

    def _do_download():
        """Download di thread terpisah agar tidak block MQTT loop."""
        try:
            import urllib.request
            import urllib.error

            print(f'[MQTT] Download start: {os.path.basename(media_url)}')

            req = urllib.request.Request(
                media_url,
                headers={'User-Agent': 'DigitalSignage/2.0'}
            )

            # Timeout besar untuk file besar — 10 menit
            with urllib.request.urlopen(req, timeout=800) as resp:
                total = int(resp.headers.get('Content-Length', 0))
                downloaded = 0
                chunk_size = 512 * 1024  # 512KB per chunk

                with open(full_path, 'wb') as f:
                    while True:
                        chunk = resp.read(chunk_size)
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded += len(chunk)

                        # Progress setiap 5MB
                        if total and downloaded % (5 * 1024 * 1024) < chunk_size:
                            pct = downloaded / total * 100
                            print(f'[MQTT] Download {pct:.0f}% ({downloaded//1024//1024}MB/{total//1024//1024}MB)')

            size_mb = os.path.getsize(full_path) / 1024 / 1024
            print(f'[MQTT] ✅ Download selesai: {media_path} ({size_mb:.1f} MB)')

        except Exception as e:
            print(f'[MQTT] ❌ Download gagal: {e}')
            # Hapus file parsial jika ada
            if os.path.exists(full_path):
                os.remove(full_path)

    # Jalankan download di background thread
    # MQTT loop tidak terputus meski file besar
    import threading
    t = threading.Thread(target=_do_download, daemon=True)
    t.start()

    return media_path


# ── Reload browser signal ─────────────────────────────────────────────────────
def trigger_reload():
    """Tulis .reload_signal agar Flask/browser tahu ada update."""
    try:
        path = os.path.join(BASE_DIR, '..', '.reload_signal')
        with open(os.path.normpath(path), 'w') as f:
            f.write(datetime.now().isoformat())
        print('[MQTT] Reload signal written')
    except Exception as e:
        print(f'[MQTT] Reload signal error: {e}')


# ══════════════════════════════════════════════════════════════════════════════
# HANDLERS
# ══════════════════════════════════════════════════════════════════════════════

def handle_news(p: dict, action: str) -> str:
    conn = get_db()
    try:
        if action == 'add':
            content = p.get('content', p.get('title', ''))
            if not content:
                return "news add gagal: content kosong"
            conn.execute(
                'INSERT INTO news (content, is_active) VALUES (?, ?)',
                (content, p.get('is_active', 1))
            )
            conn.commit()
            trigger_reload()
            return f'news added: "{content[:60]}"'

        elif action == 'update':
            cid = p.get('content_id')
            if not cid:
                return "news update gagal: content_id null"
            content = p.get('content', p.get('title'))
            conn.execute('''
                UPDATE news SET
                    content   = COALESCE(?, content),
                    is_active = COALESCE(?, is_active)
                WHERE id = ?
            ''', (content, p.get('is_active'), cid))
            conn.commit()
            trigger_reload()
            return f"news {cid} updated"

        elif action == 'delete':
            cid = p.get('content_id')
            if not cid:
                return "news delete gagal: content_id null"
            conn.execute('UPDATE news SET is_active=0 WHERE id=?', (cid,))
            conn.commit()
            trigger_reload()
            return f"news {cid} deleted"

        elif action == 'clear_all':
            conn.execute('UPDATE news SET is_active=0')
            conn.commit()
            trigger_reload()
            return "semua news dinonaktifkan"

        return f"news: action '{action}' tidak dikenal"
    finally:
        conn.close()


def handle_agenda(p: dict, action: str) -> str:
    media_path = maybe_download_media(p)
    conn = get_db()
    try:
        media_type = p.get('media_type', 'text')

        # mapping biar sesuai DB
        if media_type == 'image':
            media_type = 'photo'
        elif media_type not in ('photo', 'video'):
            media_type = 'photo'

        if action == 'add':
            conn.execute('''
                INSERT INTO agendas
                    (position, title, description, media_type,
                     media_path, event_date, event_time, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                p.get('position', 99),
                p.get('title', 'Agenda Baru'),
                p.get('description', p.get('content', '')),
                media_type,
                media_path,
                p.get('event_date', ''),
                p.get('event_time', ''),
                p.get('is_active', 1),
            ))
            conn.commit()
            trigger_reload()
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
                p.get('position'), p.get('title'),
                p.get('description', p.get('content')),
                p.get('media_type'), media_path or None,
                p.get('event_date'), p.get('event_time'),
                p.get('is_active'), cid,
            ))
            conn.commit()
            trigger_reload()
            return f"agenda {cid} updated"

        elif action == 'delete':
            cid = p.get('content_id')
            if not cid:
                return "agenda delete gagal: content_id null"
            conn.execute('UPDATE agendas SET is_active=0 WHERE id=?', (cid,))
            conn.commit()
            trigger_reload()
            return f"agenda {cid} deleted"

        return f"agenda: action '{action}' tidak dikenal"
    finally:
        conn.close()


def handle_template(p: dict, action: str) -> str:
    media_path = maybe_download_media(p)
    conn = get_db()
    try:
        cid      = p.get('content_id')
        existing = conn.execute('SELECT id FROM templates WHERE id=?', (cid,)).fetchone() if cid else None

        if action == 'delete':
            if not cid:
                return "template delete gagal: content_id null"
            conn.execute('UPDATE templates SET is_active=0 WHERE id=?', (cid,))
            conn.commit()
            trigger_reload()
            return f"template {cid} deleted"

        # add / update / apapun → UPSERT
        if cid and existing:
            # Update row yang sudah ada
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
            trigger_reload()
            return f"template {cid} updated"

        else:
            # Insert baru — pakai content_id sebagai id jika ada
            if cid:
                conn.execute('''
                    INSERT INTO templates (id, template_name, template_type, file_path, duration, display_order, is_active)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    cid,
                    p.get('title', 'Template Baru'),
                    p.get('media_type', 'image'),
                    media_path,
                    p.get('duration', 10),
                    p.get('display_order', 99),
                    p.get('is_active', 1),
                ))
            else:
                conn.execute('''
                    INSERT INTO templates (template_name, template_type, file_path, duration, display_order, is_active)
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
            trigger_reload()
            return f"template {cid or 'new'} inserted"

    finally:
        conn.close()


def handle_advertisement(p: dict, action: str) -> str:
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
            trigger_reload()
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
            trigger_reload()
            return f"advertisement {cid} updated"

        elif action == 'delete':
            cid = p.get('content_id')
            if not cid:
                return "advertisement delete gagal: content_id null"
            conn.execute('UPDATE advertisements SET is_active=0 WHERE id=?', (cid,))
            conn.commit()
            trigger_reload()
            return f"advertisement {cid} deleted"

        return f"advertisement: action '{action}' tidak dikenal"
    finally:
        conn.close()


def handle_config(p: dict, action: str) -> str:
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
            trigger_reload()
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
    if action == 'reload':
        trigger_reload()
        return "reload signal written"

    elif action == 'restart_browser':
        subprocess.Popen(
            ['bash', '-c', 'sleep 2 && pkill -f chromium'],
            shell=False
        )
        return "browser restart triggered"

    elif action == 'reboot':
        subprocess.Popen(['sudo', 'reboot'], shell=False)
        return "system reboot triggered"

    return f"system: action '{action}' tidak dikenal"


# ── Router ────────────────────────────────────────────────────────────────────
HANDLERS = {
    'news':          handle_news,
    'text':          handle_news,
    'agenda':        handle_agenda,
    'template':      handle_template,
    'image':         handle_template,   # type=image → template
    'video':         handle_template,   # type=video → template
    'advertisement': handle_advertisement,
    'ads':           handle_advertisement,
    'config':        handle_config,
    'system':        handle_system,
}


# ══════════════════════════════════════════════════════════════════════════════
# MQTT CALLBACKS
# ══════════════════════════════════════════════════════════════════════════════

def on_connect(client, userdata, flags, rc):
    global _reconnect_delay, _connected
    codes = {
        0: 'OK', 1: 'Bad protocol', 2: 'Client ID rejected',
        3: 'Broker unavailable', 4: 'Bad credentials', 5: 'Not authorized'
    }
    status = codes.get(rc, f'Unknown rc={rc}')
    if rc == 0:
        _connected       = True
        _reconnect_delay = 5
        print(f"[MQTT] ✅ Connected to {BROKER}:{PORT}")
        client.subscribe(TOPIC, qos=1)
        print(f"[MQTT] Subscribed: {TOPIC}")
    else:
        _connected = False
        print(f"[MQTT] ❌ Connect gagal: {status}")


def on_disconnect(client, userdata, rc):
    global _connected
    _connected = False
    if rc == 0:
        print("[MQTT] Disconnected (clean)")
    else:
        print(f"[MQTT] ⚠ Disconnected unexpectedly rc={rc}, akan reconnect...")


def on_message(client, userdata, msg):
    ts  = datetime.now().strftime('%H:%M:%S')
    raw = msg.payload.decode('utf-8', errors='replace')

    print(f"\n{'='*60}")
    print(f"[{ts}] 📩 Topic : {msg.topic}")
    print(f"  Payload: {raw[:200]}{'...' if len(raw) > 200 else ''}")

    try:
        p = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"  ❌ JSON parse error: {e}")
        return

    msg_type = str(p.get('type',   '')).lower().strip()
    action   = str(p.get('action', 'add')).lower().strip()
    msg_id   = p.get('id', '-')

    print(f"  Type   : {msg_type}")
    print(f"  Action : {action}")
    print(f"  ID     : {msg_id}")

    handler = HANDLERS.get(msg_type)
    if not handler:
        print(f"  ⚠ type '{msg_type}' tidak dikenal.")
        print(f"  Tersedia: {list(HANDLERS.keys())}")
        return

    try:
        result = handler(p, action)
        print(f"  ✅ {result}")
    except Exception as e:
        print(f"  ❌ Handler error: {e}")
        import traceback
        traceback.print_exc()


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

# def create_client() -> mqtt.Client:
#     client = mqtt.Client(
#         client_id=f"signage_{os.uname().nodename}_{int(time.time())}",
#         protocol=mqtt.MQTTv311,
#         clean_session=True,
#     )
#     if USERNAME:
#         client.username_pw_set(USERNAME, PASSWORD)

#     client.on_connect    = on_connect
#     client.on_disconnect = on_disconnect
#     client.on_message    = on_message

#     # Last Will — kirim status offline jika koneksi putus tidak bersih
#     will_payload = json.dumps({
#         'device': os.uname().nodename,
#         'status': 'offline',
#         'ts':     datetime.now().isoformat(),
#     })
#     client.will_set(f"{TOPIC}/status", will_payload, qos=1, retain=True)

#     return client


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

    import platform
    device_name = platform.node()

    client = mqtt.Client(
        client_id=f"signage_{device_name}",
        protocol=mqtt.MQTTv311
    )

    if USERNAME:
        client.username_pw_set(USERNAME, PASSWORD)

    client.on_connect    = on_connect
    client.on_disconnect = on_disconnect
    client.on_message    = on_message

    try:
        client.connect(BROKER, PORT, KEEPALIVE)
    except Exception as e:
        print(f"❌ Koneksi gagal: {e}")
        sys.exit(1)

    try:
        client.loop_forever()
    except KeyboardInterrupt:
        print("\n🛑 Dihentikan")
        client.disconnect()
#!/usr/bin/env python3
"""
mqtt_test.py — Digital Signage MQTT Payload Tester
Testing semua jenis payload ke topic signage.

Usage:
  python3 mqtt_test.py                    # menu interaktif
  python3 mqtt_test.py --list             # tampilkan semua payload contoh
  python3 mqtt_test.py --send template    # kirim payload template
  python3 mqtt_test.py --send all         # kirim semua payload sekaligus
"""

import paho.mqtt.client as mqtt
import json
import time
import sys
import os
import argparse
import configparser
from datetime import datetime, timezone

# ── Config ────────────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_cfg = configparser.ConfigParser()
_cfg_path = os.path.join(BASE_DIR, 'config.ini')
_cfg.read(_cfg_path)

BROKER    = _cfg['DEFAULT'].get('Broker',  'broker.hivemq.com')
PORT      = int(_cfg['DEFAULT'].get('Port', '1883'))
USERNAME  = _cfg['DEFAULT'].get('UserID', '')
PASSWORD  = _cfg['DEFAULT'].get('Pass',   '')
# TOPIC     = _cfg['DEFAULT'].get('Topic',  'signage/default')
TOPIC = "signage/sma-n-2-mengwi/"

# ── Warna terminal ────────────────────────────────────────────────────────────
GREEN  = '\033[92m'
RED    = '\033[91m'
YELLOW = '\033[93m'
CYAN   = '\033[96m'
BOLD   = '\033[1m'
RESET  = '\033[0m'

# ══════════════════════════════════════════════════════════════════════════════
# PAYLOAD LIBRARY
# Semua contoh payload yang valid untuk sistem signage
# ══════════════════════════════════════════════════════════════════════════════

def _ts():
    return datetime.now(timezone.utc).isoformat()

def _uid():
    import uuid
    return str(uuid.uuid4())


PAYLOADS = {

    # ── Template (image) ──────────────────────────────────────────────────────
    'template_image_add': {
        'name': 'Template Image — Add',
        'payload': {
            "id":         _uid(),
            "content_id": None,
            "type":       "image",
            "title":      "Selamat Datang di Kampus",
            "content":    "Gambar selamat datang",
            "media_path": None,
            "media_url":  "https://digital-signage.warmadewa.ac.id/uploads/sma-n-1-denpasar/1772039965586-a0i76qkf5dt.png",
            "duration":   10,
            "display_order": 1,
            "action":     "add",
            "publisher":  "admin",
            "_sentAt":    _ts(),
        }
    },

    'template_image_update': {
        'name': 'Template Image — Update',
        'payload': {
            "id":         _uid(),
            "content_id": 1,
            "type":       "image",
            "title":      "Selamat Datang (Updated)",
            "duration":   15,
            "is_active":  1,
            "action":     "update",
            "publisher":  "admin",
            "_sentAt":    _ts(),
        }
    },

    'template_image_delete': {
        'name': 'Template Image — Delete',
        'payload': {
            "id":         _uid(),
            "content_id": 1,
            "type":       "image",
            "action":     "delete",
            "publisher":  "admin",
            "_sentAt":    _ts(),
        }
    },

    # ── Template (video) ──────────────────────────────────────────────────────
    'template_video_add': {
        'name': 'Template Video — Add',
        'payload': {
            "id":         _uid(),
            "content_id": None,
            "type":       "video",
            "title":      "Profil Sekolah",
            "media_path": None,
            "media_url":  "https://www.w3schools.com/html/mov_bbb.mp4",
            "duration":   30,
            "display_order": 2,
            "action":     "add",
            "publisher":  "admin",
            "_sentAt":    _ts(),
        }
    },

    # ── News ──────────────────────────────────────────────────────────────────
    'news_add': {
        'name': 'News — Add',
        'payload': {
            "id":         _uid(),
            "content_id": None,
            "type":       "news",
            "content":    f"Berita terbaru: Kegiatan kampus hari ini {datetime.now().strftime('%d/%m/%Y')}",
            "is_active":  1,
            "action":     "add",
            "publisher":  "admin",
            "_sentAt":    _ts(),
        }
    },

    'news_update': {
        'name': 'News — Update',
        'payload': {
            "id":         _uid(),
            "content_id": 1,
            "type":       "news",
            "content":    "Berita diperbarui: Info terbaru kampus",
            "is_active":  1,
            "action":     "update",
            "publisher":  "admin",
            "_sentAt":    _ts(),
        }
    },

    'news_delete': {
        'name': 'News — Delete (soft)',
        'payload': {
            "id":         _uid(),
            "content_id": 1,
            "type":       "news",
            "action":     "delete",
            "publisher":  "admin",
            "_sentAt":    _ts(),
        }
    },

    'news_clear_all': {
        'name': 'News — Clear All',
        'payload': {
            "id":      _uid(),
            "type":    "news",
            "action":  "clear_all",
            "publisher": "admin",
            "_sentAt": _ts(),
        }
    },

    # ── Agenda ────────────────────────────────────────────────────────────────
    'agenda_add': {
        'name': 'Agenda — Add',
        'payload': {
            "id":          _uid(),
            "content_id":  None,
            "type":        "agenda",
            "title":       "Seminar Nasional AI",
            "description": "Seminar tentang kecerdasan buatan di era modern",
            "media_type":  "image",
            "media_path":  None,
            "media_url":   "https://digital-signage.warmadewa.ac.id/uploads/sma-n-1-denpasar/1772039965586-a0i76qkf5dt.png",
            "event_date":  "2026-05-20",
            "event_time":  "09:00",
            "position":    1,
            "is_active":   1,
            "action":      "add",
            "publisher":   "admin",
            "_sentAt":     _ts(),
        }
    },

    'agenda_update': {
        'name': 'Agenda — Update',
        'payload': {
            "id":          _uid(),
            "content_id":  1,
            "type":        "agenda",
            "title":       "Seminar Nasional AI (Updated)",
            "event_date":  "2026-05-21",
            "event_time":  "10:00",
            "action":      "update",
            "publisher":   "admin",
            "_sentAt":     _ts(),
        }
    },

    'agenda_delete': {
        'name': 'Agenda — Delete',
        'payload': {
            "id":         _uid(),
            "content_id": 1,
            "type":       "agenda",
            "action":     "delete",
            "publisher":  "admin",
            "_sentAt":    _ts(),
        }
    },

    # ── Advertisement ─────────────────────────────────────────────────────────
    'ads_add': {
        'name': 'Advertisement — Add',
        'payload': {
            "id":            _uid(),
            "content_id":    None,
            "type":          "advertisement",
            "title":         "Promo Kantin Kampus",
            "media_type":    "image",
            "media_path":    None,
            "media_url":     "https://digital-signage.warmadewa.ac.id/uploads/sma-n-1-denpasar/1772039965586-a0i76qkf5dt.png",
            "duration":      10,
            "trigger_time":  8,
            "display_order": 1,
            "is_active":     1,
            "action":        "add",
            "publisher":     "admin",
            "_sentAt":       _ts(),
        }
    },

    # ── Config ────────────────────────────────────────────────────────────────
    'config_color': {
        'name': 'Config — Ganti Warna Utama',
        'payload': {
            "id":        _uid(),
            "type":      "config",
            "key":       "main_color",
            "value":     "#4ecca3",
            "action":    "update",
            "publisher": "admin",
            "_sentAt":   _ts(),
        }
    },

    'config_schedule': {
        'name': 'Config — Set Jadwal On/Off',
        'payload': {
            "id":        _uid(),
            "type":      "config",
            "key":       "time_on",
            "value":     "07:00",
            "action":    "update",
            "publisher": "admin",
            "_sentAt":   _ts(),
        }
    },

    'config_wifi': {
        'name': 'Config — Update WiFi',
        'payload': {
            "id":        _uid(),
            "type":      "config",
            "key":       "wifi_ssid",
            "value":     "SMAN 2 MENGWI",
            "action":    "update",
            "publisher": "admin",
            "_sentAt":   _ts(),
        }
    },

    'config_wifi_pass': {
        'name': 'Config — Update WiFi Pass',
        'payload': {
            "id":        _uid(),
            "type":      "config",
            "key":       "wifi_password",
            "value":     "",
            "action":    "update",
            "publisher": "admin",
            "_sentAt":   _ts(),
        }
    },

    # ── System ────────────────────────────────────────────────────────────────
    'system_reload': {
        'name': 'System — Reload Browser',
        'payload': {
            "id":        _uid(),
            "type":      "system",
            "action":    "reload",
            "publisher": "admin",
            "_sentAt":   _ts(),
        }
    },

    'system_restart_browser': {
        'name': 'System — Restart Chromium',
        'payload': {
            "id":        _uid(),
            "type":      "system",
            "action":    "restart_browser",
            "publisher": "admin",
            "_sentAt":   _ts(),
        }
    },
}


# ══════════════════════════════════════════════════════════════════════════════
# MQTT CLIENT
# ══════════════════════════════════════════════════════════════════════════════

_publish_ok   = False
_publish_error = None

def create_client() -> mqtt.Client:
    global _publish_ok, _publish_error
    _publish_ok    = False
    _publish_error = None

    client = mqtt.Client(
        client_id=f"signage_tester_{int(time.time())}",
        protocol=mqtt.MQTTv311,
    )
    if USERNAME:
        client.username_pw_set(USERNAME, PASSWORD)

    def on_connect(c, ud, flags, rc):
        if rc == 0:
            print(f"{GREEN}✅ Connected ke {BROKER}:{PORT}{RESET}")
        else:
            print(f"{RED}❌ Connect gagal rc={rc}{RESET}")

    def on_publish(c, ud, mid):
        global _publish_ok
        _publish_ok = True

    def on_disconnect(c, ud, rc):
        pass

    client.on_connect    = on_connect
    client.on_publish    = on_publish
    client.on_disconnect = on_disconnect

    return client


def send_payload(key: str, payload: dict, client: mqtt.Client = None) -> bool:
    """Kirim satu payload. Return True jika berhasil."""
    global _publish_ok

    should_disconnect = False
    if client is None:
        client = create_client()
        try:
            client.connect(BROKER, PORT, 60)
            client.loop_start()
            time.sleep(1.5)
        except Exception as e:
            print(f"{RED}❌ Koneksi gagal: {e}{RESET}")
            return False
        should_disconnect = True

    # Refresh _sentAt dan id sebelum kirim
    payload['_sentAt'] = _ts()
    payload['id']      = _uid()

    raw = json.dumps(payload, ensure_ascii=False)
    _publish_ok = False

    info = client.publish(TOPIC, raw, qos=1)
    info.wait_for_publish(timeout=5)

    time.sleep(0.5)

    if should_disconnect:
        client.loop_stop()
        client.disconnect()

    return _publish_ok


def print_payload(key: str, entry: dict):
    """Tampilkan payload dengan format yang rapi."""
    print(f"\n{CYAN}{'─'*60}{RESET}")
    print(f"{BOLD}  [{key}] {entry['name']}{RESET}")
    print(f"{CYAN}{'─'*60}{RESET}")
    print(json.dumps(entry['payload'], indent=2, ensure_ascii=False))


# ══════════════════════════════════════════════════════════════════════════════
# CLI
# ══════════════════════════════════════════════════════════════════════════════

def menu_interactive(client: mqtt.Client):
    """Menu interaktif untuk memilih dan mengirim payload."""
    keys = list(PAYLOADS.keys())

    while True:
        print(f"\n{BOLD}{'='*60}{RESET}")
        print(f"{BOLD}  MQTT PAYLOAD TESTER{RESET}")
        print(f"  Broker : {BROKER}:{PORT}")
        print(f"  Topic  : {TOPIC}")
        print(f"{BOLD}{'='*60}{RESET}")

        for i, key in enumerate(keys, 1):
            print(f"  {CYAN}{i:2d}{RESET}. {PAYLOADS[key]['name']}")

        print(f"\n  {YELLOW} 0{RESET}. Kirim SEMUA payload")
        print(f"  {YELLOW} l{RESET}. Tampilkan JSON payload")
        print(f"  {YELLOW} q{RESET}. Keluar")

        choice = input(f"\n{BOLD}Pilih [1-{len(keys)}/0/l/q]: {RESET}").strip().lower()

        if choice == 'q':
            break

        elif choice == '0':
            print(f"\n{YELLOW}Mengirim {len(keys)} payload...{RESET}")
            ok = err = 0
            for key in keys:
                entry = PAYLOADS[key]
                success = send_payload(key, entry['payload'], client)
                status = f"{GREEN}✅{RESET}" if success else f"{RED}❌{RESET}"
                print(f"  {status} {entry['name']}")
                if success:
                    ok += 1
                else:
                    err += 1
                time.sleep(0.3)
            print(f"\n{GREEN}Selesai: {ok} berhasil, {err} gagal{RESET}")

        elif choice == 'l':
            sub = input(f"Tampilkan payload key (kosong=semua): ").strip()
            if sub and sub in PAYLOADS:
                print_payload(sub, PAYLOADS[sub])
            else:
                for k, v in PAYLOADS.items():
                    print_payload(k, v)

        elif choice.isdigit() and 1 <= int(choice) <= len(keys):
            idx   = int(choice) - 1
            key   = keys[idx]
            entry = PAYLOADS[key]
            print_payload(key, entry)
            confirm = input(f"\n{BOLD}Kirim payload ini? [y/N]: {RESET}").strip().lower()
            if confirm == 'y':
                success = send_payload(key, entry['payload'], client)
                if success:
                    print(f"{GREEN}✅ Payload terkirim ke {TOPIC}{RESET}")
                else:
                    print(f"{RED}❌ Gagal mengirim{RESET}")
        else:
            print(f"{RED}Pilihan tidak valid{RESET}")


def main():
    parser = argparse.ArgumentParser(description='MQTT Payload Tester untuk Digital Signage')
    parser.add_argument('--list',   action='store_true', help='Tampilkan semua payload')
    parser.add_argument('--send',   metavar='KEY',       help='Kirim payload by key, atau "all"')
    parser.add_argument('--broker', metavar='HOST',      help='Override broker host')
    parser.add_argument('--topic',  metavar='TOPIC',     help='Override topic')
    args = parser.parse_args()

    global BROKER, TOPIC
    if args.broker:
        BROKER = args.broker
    if args.topic:
        TOPIC = args.topic

    if args.list:
        for key, entry in PAYLOADS.items():
            print_payload(key, entry)
        return

    print(f"\n{BOLD}  MQTT Payload Tester — Digital Signage{RESET}")
    print(f"  Broker : {BROKER}:{PORT}")
    print(f"  Topic  : {TOPIC}\n")

    client = create_client()
    try:
        client.connect(BROKER, PORT, 60)
        client.loop_start()
        time.sleep(1.5)
    except Exception as e:
        print(f"{RED}❌ Tidak bisa connect ke broker: {e}{RESET}")
        sys.exit(1)

    if args.send:
        if args.send == 'all':
            ok = err = 0
            for key, entry in PAYLOADS.items():
                success = send_payload(key, entry['payload'], client)
                status  = f"{GREEN}✅{RESET}" if success else f"{RED}❌{RESET}"
                print(f"  {status} {entry['name']}")
                if success: ok += 1
                else:       err += 1
                time.sleep(0.3)
            print(f"\n{GREEN}Selesai: {ok} berhasil, {err} gagal{RESET}")
        elif args.send in PAYLOADS:
            entry   = PAYLOADS[args.send]
            success = send_payload(args.send, entry['payload'], client)
            if success:
                print(f"{GREEN}✅ Terkirim: {entry['name']}{RESET}")
            else:
                print(f"{RED}❌ Gagal: {entry['name']}{RESET}")
        else:
            print(f"{RED}Key tidak ditemukan: {args.send}{RESET}")
            print(f"Tersedia: {', '.join(PAYLOADS.keys())}")
    else:
        menu_interactive(client)

    client.loop_stop()
    client.disconnect()
    print(f"\n{YELLOW}Bye!{RESET}")


if __name__ == '__main__':
    main()
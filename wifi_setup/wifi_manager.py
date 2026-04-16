#!/usr/bin/env python3
"""
wifi_manager.py — Digital Signage WiFi Auto-Connect Service

Logika:
  1. Baca wifi_ssid + wifi_password dari tabel config di database
  2. Coba connect ke SSID tersebut
  3. Jika gagal atau tidak ada di config → coba SSID fallback dari config.ini
  4. Cek koneksi internet setiap CHECK_INTERVAL detik
  5. Jika koneksi putus → ulangi proses dari awal

Config database (tabel config):
  wifi_ssid      → SSID utama
  wifi_password  → password WiFi utama

config.ini (section [WIFI]):
  FallbackSSID   → SSID cadangan jika utama gagal
  FallbackPass   → password SSID cadangan
  CheckInterval  → detik antar pengecekan (default 60)
  PingHost       → host untuk tes internet (default 8.8.8.8)
"""

import sqlite3
import subprocess
import time
import os
import sys
import configparser
import logging
from datetime import datetime

# ── Setup logging ─────────────────────────────────────────────────────────────
LOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'wifi-manager.log')
LOG_PATH = os.path.normpath(LOG_PATH)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_PATH, encoding='utf-8'),
    ]
)
log = logging.getLogger('wifi_manager')

# ── Config ────────────────────────────────────────────────────────────────────
BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
_cfg      = configparser.ConfigParser()
_cfg_path = os.path.join(BASE_DIR, 'config.ini')
_cfg.read(_cfg_path)

DB_PATH = os.path.abspath(os.path.join(BASE_DIR, '..', 'db', 'photostation.db'))

FALLBACK_SSID  = _cfg.get('WIFI', 'FallbackSSID',  fallback='')
FALLBACK_PASS  = _cfg.get('WIFI', 'FallbackPass',   fallback='')
CHECK_INTERVAL = int(_cfg.get('WIFI', 'CheckInterval', fallback='60'))
PING_HOST      = _cfg.get('WIFI', 'PingHost',       fallback='8.8.8.8')

# Delay antara retry (detik)
RETRY_DELAY    = 15
MAX_RETRIES    = 3


# ── DB helper ─────────────────────────────────────────────────────────────────
def get_wifi_config() -> tuple:
    """
    Baca wifi_ssid dan wifi_password dari database.
    Return (ssid, password) atau (None, None) jika tidak ada.
    """
    try:
        if not os.path.exists(DB_PATH):
            log.warning(f"Database tidak ditemukan: {DB_PATH}")
            return None, None

        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        ssid = cur.execute(
            "SELECT value FROM config WHERE key='wifi_ssid'"
        ).fetchone()
        pwd = cur.execute(
            "SELECT value FROM config WHERE key='wifi_password'"
        ).fetchone()
        conn.close()

        ssid = ssid['value'].strip() if ssid and ssid['value'] else None
        pwd  = pwd['value'].strip()  if pwd  and pwd['value']  else ''

        return ssid, pwd

    except Exception as e:
        log.error(f"Gagal baca config DB: {e}")
        return None, None


def update_wifi_status(status: str, ssid: str = ''):
    """Simpan status koneksi WiFi ke database."""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute(
            "INSERT OR REPLACE INTO config (key, value, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)",
            ('wifi_status', f"{status}:{ssid}")
        )
        conn.commit()
        conn.close()
    except Exception:
        pass


# ── Network helpers ───────────────────────────────────────────────────────────
def get_current_ssid() -> str:
    """Dapatkan SSID yang sedang terkoneksi."""
    try:
        result = subprocess.run(
            ['iwgetid', '-r'],
            capture_output=True, text=True, timeout=5
        )
        return result.stdout.strip()
    except Exception:
        return ''


def is_internet_available(host: str = PING_HOST, timeout: int = 5) -> bool:
    """Cek koneksi internet dengan ping."""
    try:
        result = subprocess.run(
            ['ping', '-c', '1', '-W', str(timeout), host],
            capture_output=True, timeout=timeout + 2
        )
        return result.returncode == 0
    except Exception:
        return False


def get_available_networks() -> list:
    """Scan WiFi yang tersedia. Return list SSID."""
    try:
        result = subprocess.run(
            ['nmcli', '-t', '-f', 'SSID', 'dev', 'wifi', 'list'],
            capture_output=True, text=True, timeout=15
        )
        ssids = [
            line.strip() for line in result.stdout.splitlines()
            if line.strip() and line.strip() != '--'
        ]
        return list(dict.fromkeys(ssids))  # deduplikasi, pertahankan urutan
    except Exception as e:
        log.warning(f"Scan WiFi gagal: {e}")
        return []


def disconnect_wifi():
    """Disconnect dari WiFi saat ini."""
    try:
        subprocess.run(
            ['nmcli', 'dev', 'disconnect', 'wlan0'],
            capture_output=True, timeout=10
        )
        time.sleep(2)
    except Exception:
        pass


def connect_to_wifi(ssid: str, password: str, retries: int = MAX_RETRIES) -> bool:
    """
    Coba connect ke SSID dengan password.
    Return True jika berhasil.
    """
    if not ssid:
        return False

    log.info(f"Mencoba connect ke: '{ssid}'")

    # Cek apakah SSID tersedia
    available = get_available_networks()
    if available and ssid not in available:
        log.warning(f"SSID '{ssid}' tidak ditemukan. Tersedia: {available[:5]}")

    for attempt in range(1, retries + 1):
        log.info(f"  Percobaan {attempt}/{retries}...")
        try:
            # Coba connect dengan nmcli
            # --ask diabaikan, password dari argumen
            result = subprocess.run(
                ['nmcli', 'dev', 'wifi', 'connect', ssid,
                 'password', password, 'ifname', 'wlan0'],
                capture_output=True, text=True, timeout=30
            )

            output = result.stdout + result.stderr
            log.debug(f"  nmcli output: {output[:200]}")

            if result.returncode == 0 or 'successfully activated' in output.lower():
                time.sleep(3)  # tunggu IP assigned
                current = get_current_ssid()
                if current == ssid:
                    log.info(f"  ✅ Connected ke '{ssid}'")
                    return True
                else:
                    log.warning(f"  nmcli OK tapi SSID saat ini: '{current}'")

            elif 'already active' in output.lower() or 'already exist' in output.lower():
                log.info(f"  ✅ Sudah terkoneksi ke '{ssid}'")
                return True

            else:
                log.warning(f"  Connect gagal: {output[:100]}")

        except subprocess.TimeoutExpired:
            log.warning(f"  Timeout percobaan {attempt}")
        except Exception as e:
            log.error(f"  Error: {e}")

        if attempt < retries:
            log.info(f"  Tunggu {RETRY_DELAY}s sebelum retry...")
            time.sleep(RETRY_DELAY)

    return False


def ensure_connection() -> bool:
    """
    Pastikan Raspi terkoneksi ke WiFi yang benar.
    Urutan:
      1. Cek apakah sudah online
      2. Coba wifi_ssid dari database
      3. Coba SSID fallback dari config.ini
    Return True jika berhasil connect ke salah satu.
    """
    # Cek koneksi saat ini
    current_ssid = get_current_ssid()
    if current_ssid and is_internet_available():
        log.info(f"✅ Online — SSID: '{current_ssid}'")
        update_wifi_status('connected', current_ssid)
        return True

    if current_ssid:
        log.warning(f"⚠ Terkoneksi ke '{current_ssid}' tapi tidak ada internet")
    else:
        log.warning("⚠ Tidak terkoneksi ke WiFi apapun")

    # Baca config dari database
    db_ssid, db_pass = get_wifi_config()
    log.info(f"Config DB → SSID: '{db_ssid}'")

    # Coba SSID dari database
    if db_ssid:
        if current_ssid != db_ssid:
            disconnect_wifi()

        if connect_to_wifi(db_ssid, db_pass):
            time.sleep(3)
            if is_internet_available():
                log.info(f"✅ Internet OK via '{db_ssid}'")
                update_wifi_status('connected', db_ssid)
                return True
            else:
                log.warning(f"Connected ke '{db_ssid}' tapi tidak ada internet")
        else:
            log.warning(f"Gagal connect ke '{db_ssid}'")
    else:
        log.info("Tidak ada wifi_ssid di database")

    # Coba fallback SSID dari config.ini
    if FALLBACK_SSID:
        log.info(f"Mencoba fallback SSID: '{FALLBACK_SSID}'")
        disconnect_wifi()

        if connect_to_wifi(FALLBACK_SSID, FALLBACK_PASS):
            time.sleep(3)
            if is_internet_available():
                log.info(f"✅ Internet OK via fallback '{FALLBACK_SSID}'")
                update_wifi_status('connected_fallback', FALLBACK_SSID)
                return True
            else:
                log.warning(f"Connected ke fallback '{FALLBACK_SSID}' tapi tidak ada internet")
        else:
            log.warning(f"Gagal connect ke fallback '{FALLBACK_SSID}'")
    else:
        log.info("Tidak ada FallbackSSID di config.ini")

    log.error("❌ Semua WiFi gagal")
    update_wifi_status('disconnected', '')
    return False


# ══════════════════════════════════════════════════════════════════════════════
# MAIN LOOP
# ══════════════════════════════════════════════════════════════════════════════

def main():
    log.info("=" * 60)
    log.info("  Digital Signage — WiFi Manager")
    log.info(f"  DB          : {DB_PATH}")
    log.info(f"  Fallback    : {FALLBACK_SSID or '(tidak ada)'}")
    log.info(f"  Check setiap: {CHECK_INTERVAL}s")
    log.info(f"  Ping host   : {PING_HOST}")
    log.info("=" * 60)

    # Tunggu sebentar saat boot agar NetworkManager siap
    log.info("Tunggu 10s untuk NetworkManager siap...")
    time.sleep(10)

    fail_count    = 0
    last_ssid     = ''

    while True:
        try:
            connected = ensure_connection()
            current   = get_current_ssid()

            if connected:
                fail_count = 0
                if current != last_ssid:
                    log.info(f"🌐 Aktif SSID berubah: '{last_ssid}' → '{current}'")
                    last_ssid = current
            else:
                fail_count += 1
                log.warning(f"Koneksi gagal (percobaan ke-{fail_count})")

                # Setelah 5x gagal berturut-turut, coba scan ulang
                if fail_count >= 5:
                    log.warning("5x gagal berturut — scan ulang jaringan...")
                    available = get_available_networks()
                    log.info(f"WiFi tersedia: {available[:10]}")
                    fail_count = 0

            log.info(f"Cek berikutnya dalam {CHECK_INTERVAL}s...")
            time.sleep(CHECK_INTERVAL)

        except KeyboardInterrupt:
            log.info("🛑 WiFi Manager dihentikan")
            sys.exit(0)
        except Exception as e:
            log.error(f"Error tak terduga: {e}")
            import traceback
            traceback.print_exc()
            time.sleep(30)


if __name__ == '__main__':
    # Cek apakah nmcli tersedia
    try:
        subprocess.run(['nmcli', '--version'], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        log.error("nmcli tidak ditemukan. Install dengan: sudo apt install network-manager")
        sys.exit(1)

    main()
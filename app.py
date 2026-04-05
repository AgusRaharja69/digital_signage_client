#!/usr/bin/env python3
"""
Digital Signage Client — app.py
Main Flask app + Photobooth sub-app (Blueprint)
"""

import os
import sys
from flask import Flask, render_template, request, jsonify, url_for, send_from_directory, redirect
from datetime import datetime
import sqlite3
import base64
import json

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR     = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = os.path.join(BASE_DIR, 'templates')
STATIC_DIR   = os.path.join(BASE_DIR, 'static')
DB_PATH      = os.path.join(BASE_DIR, 'db', 'photostation.db')

# Photobooth paths
PB_DIR          = os.path.join(BASE_DIR, 'apps', 'photobooth')
PB_TEMPLATE_DIR = os.path.join(PB_DIR, 'templates')
PB_FRAMES_DIR   = os.path.join(PB_DIR, 'imgs', 'frames')
PB_CAPTURES_DIR = os.path.join(PB_DIR, 'imgs', 'captures')

print("="*70)
print("  DIGITAL SIGNAGE CLIENT")
print(f"  BASE    : {BASE_DIR}")
print(f"  DB      : {DB_PATH}  exists={os.path.exists(DB_PATH)}")
print(f"  PB_DIR  : {PB_DIR}")
print("="*70)

# ── Ensure folders ─────────────────────────────────────────────────────────────
os.makedirs(PB_CAPTURES_DIR, exist_ok=True)

# ── Flask ──────────────────────────────────────────────────────────────────────
app = Flask(__name__,
            template_folder=TEMPLATE_DIR,
            static_folder=STATIC_DIR)

app.config['UPLOAD_FOLDER']      = os.path.join(STATIC_DIR, 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif', 'mp4', 'webm', 'avi', 'mov'}

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'ads'), exist_ok=True)

# ── Photo slot positions on 1000×2000 frame canvas ───────────────────────────
# Auto-detected from black regions in frame1/2/3.PNG (high-res version)
PB_SLOTS = [
    (111, 441,  775, 364),   # slot 1
    (111, 855,  775, 364),   # slot 2
    (112, 1269, 774, 364),   # slot 3
]

# ═════════════════════════════════════════════════════════════════════════════
# DB HELPERS
# ═════════════════════════════════════════════════════════════════════════════

def get_db():
    if not os.path.exists(DB_PATH):
        print(f"❌ Database not found: {DB_PATH}")
        print("Run: python3 init_db.py")
        sys.exit(1)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def get_config(key, default=None):
    try:
        conn = get_db()
        r = conn.execute('SELECT value FROM config WHERE key=?', (key,)).fetchone()
        conn.close()
        return r['value'] if r else default
    except:
        return default

def set_config(key, value):
    try:
        conn = get_db()
        conn.execute('INSERT OR REPLACE INTO config (key,value,updated_at) VALUES (?,?,CURRENT_TIMESTAMP)', (key, value))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"set_config error: {e}")
        return False

# ═════════════════════════════════════════════════════════════════════════════
# SCHEDULING HELPER
# ═════════════════════════════════════════════════════════════════════════════

def is_display_on():
    """Return True if the display should currently be ON based on config."""
    from datetime import date as _date
    now       = datetime.now()
    time_on   = get_config('time_on',  '00:00')
    time_off  = get_config('time_off', '23:59')
    date_off  = get_config('date_off', '')

    # Check date_off list
    today_str = now.strftime('%Y-%m-%d')
    off_dates = [d.strip() for d in date_off.split(',') if d.strip()]
    if today_str in off_dates:
        return False

    # Check time range
    try:
        h_on,  m_on  = [int(x) for x in time_on.split(':')]
        h_off, m_off = [int(x) for x in time_off.split(':')]
        minutes_now  = now.hour * 60 + now.minute
        minutes_on   = h_on  * 60 + m_on
        minutes_off  = h_off * 60 + m_off
        return minutes_on <= minutes_now < minutes_off
    except Exception:
        return True   # fallback: always on if config malformed


# ═════════════════════════════════════════════════════════════════════════════
# MAIN SIGNAGE ROUTES
# ═════════════════════════════════════════════════════════════════════════════

@app.route('/')
def index():
    try:
        # ── Scheduling check ──────────────────────────────────────────────
        if not is_display_on():
            time_on = get_config('time_on', '07:00')
            return render_template('standby.html', time_on=time_on), 200

        conn = get_db()

        templates = [dict(r) for r in conn.execute(
            'SELECT * FROM templates WHERE is_active=1 ORDER BY display_order').fetchall()]
        ads       = [dict(r) for r in conn.execute(
            'SELECT * FROM advertisements WHERE is_active=1 ORDER BY display_order').fetchall()]
        agendas   = [dict(r) for r in conn.execute(
            'SELECT * FROM agendas WHERE is_active=1 ORDER BY position').fetchall()]
        news      = [dict(r) for r in conn.execute(
            'SELECT * FROM news WHERE is_active=1 ORDER BY created_at DESC').fetchall()]

        device_name      = get_config('device_name',     'Digital Signage')
        main_color       = get_config('main_color',      '#4ecca3')
        secondary_color  = get_config('secondary_color', '#00b4d8')
        bg_color         = get_config('bg_color',        '#060a12')
        logo_univ        = get_config('logo_univ',       'static/imgs/logo1.png')
        logo_sekolah     = get_config('logo_sekolah',    'static/imgs/logo2.png')
        barcode_boot     = get_config('barcode_boot',    'static/imgs/barcode.jpeg')

        conn.close()

        return render_template('index.html',
                               templates=templates,
                               ads=ads,
                               agendas=agendas,
                               news=news,
                               device_name=device_name,
                               main_color=main_color,
                               secondary_color=secondary_color,
                               bg_color=bg_color,
                               logo_univ=logo_univ,
                               logo_sekolah=logo_sekolah,
                               barcode_boot=barcode_boot,
                               current_time=datetime.now())
    except Exception as e:
        import traceback; traceback.print_exc()
        return f"<h1>Error</h1><p>{e}</p>", 500

# ── Gallery ───────────────────────────────────────────────────────────────────
@app.route('/gallery')
def gallery():
    captures = sorted([
        f for f in os.listdir(PB_CAPTURES_DIR)
        if f.lower().endswith('.png')
    ], reverse=True)
    return render_template('gallery.html', captures=captures)

# ═════════════════════════════════════════════════════════════════════════════
# PHOTOBOOTH ROUTES  (served under /photobooth/...)
# ═════════════════════════════════════════════════════════════════════════════

# Photobooth page — renders from apps/photobooth/templates/
import jinja2

@app.route('/photobooth')
@app.route('/photobooth/')
def photobooth():
    frames = sorted([
        f for f in os.listdir(PB_FRAMES_DIR)
        if f.lower().endswith(('.png', '.jpg', '.jpeg'))
    ])

    # Baca config untuk ditampilkan di frame photobooth
    logo_univ    = get_config('logo_univ',    'static/imgs/logo1.png')
    logo_sekolah = get_config('logo_sekolah', 'static/imgs/logo2.png')
    barcode_boot = get_config('barcode_boot', 'static/imgs/barcode.jpeg')
    school_name  = get_config('school_name',  'SMKN 1 DENPASAR')

    pb_loader = jinja2.FileSystemLoader(PB_TEMPLATE_DIR)
    pb_env    = jinja2.Environment(loader=pb_loader)
    tmpl      = pb_env.get_template('photobooth.html')
    html      = tmpl.render(
        frames       = frames,
        logo_univ    = logo_univ,
        logo_sekolah = logo_sekolah,
        barcode_boot = barcode_boot,
        school_name  = school_name,
    )
    from flask import Response
    return Response(html, mimetype='text/html')


# Static files for photobooth (css, js, imgs)
@app.route('/photobooth/static/<path:filepath>')
def pb_static(filepath):
    return send_from_directory(PB_DIR, filepath)

@app.route('/photobooth/imgs/frames/<filename>')
def pb_frame_img(filename):
    return send_from_directory(PB_FRAMES_DIR, filename)

@app.route('/photobooth/imgs/captures/<filename>')
def pb_capture_img(filename):
    return send_from_directory(PB_CAPTURES_DIR, filename)


@app.route('/photobooth/save', methods=['POST'])
def pb_save():
    """
    Receive the already-composited image (JPEG blob) from browser canvas.
    Browser handles all compositing — server saves the file then
    triggers async upload to Google Drive (if photo_drive is configured).
    """
    try:
        if 'image' not in request.files:
            return jsonify({'success': False, 'error': 'No image file'}), 400

        img_file  = request.files['image']
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        out_name  = f'photo_{timestamp}.jpg'
        out_path  = os.path.join(PB_CAPTURES_DIR, out_name)
        img_file.save(out_path)

        print(f'[Photobooth] Saved: {out_path}')

        # ── Upload ke Google Drive via Apps Script webhook ──────────────
        # Tidak butuh google-auth — cukup HTTP POST biasa
        webhook = get_config('photo_drive_webhook', '')
        print(f'[Drive] Webhook config: "{webhook}"')  # ← tambah ini
        drive_uploading = False
        if webhook:
            import threading
            print(f'[Drive] Memulai thread upload ke: {webhook[:60]}...')
            t = threading.Thread(
                target=_upload_to_drive,
                args=(out_path, out_name, webhook),
                daemon=True
            )
            t.start()
            drive_uploading = True

        return jsonify({
            'success':        True,
            'filename':       out_name,
            'url':            f'/photobooth/imgs/captures/{out_name}',
            'drive_uploading': drive_uploading,
        })

    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


def _upload_to_drive(file_path, file_name, webhook_url):
    try:
        import base64 as _b64
        import urllib.request
        import urllib.error
        import json as _json

        print(f'[Drive] Memulai upload: {file_name}')

        with open(file_path, 'rb') as f:
            raw = f.read()
        b64data = _b64.b64encode(raw).decode('utf-8')

        payload = _json.dumps({
            'filename': file_name,
            'data':     b64data,
            'mimeType': 'image/jpeg',
        }).encode('utf-8')

        url = webhook_url
        MAX_REDIRECTS = 5

        for attempt in range(MAX_REDIRECTS):
            req = urllib.request.Request(
                url,
                data=payload,
                headers={
                    'Content-Type': 'application/json',
                },
                method='POST'
            )

            class NoRedirect(urllib.request.HTTPRedirectHandler):
                def redirect_request(self, req, fp, code, msg, headers, newurl):
                    return None

            opener = urllib.request.build_opener(NoRedirect)

            try:
                with opener.open(req, timeout=60) as resp:
                    body = resp.read().decode('utf-8')
                    print(f'[Drive] Response raw: {body[:200]}')
                    try:
                        result = _json.loads(body)
                        if result.get('success'):
                            print(f'[Drive] ✅ Upload berhasil: {result.get("filename")} → {result.get("viewLink")}')
                        else:
                            print(f'[Drive] ❌ Upload gagal: {result.get("error")}')
                    except Exception:
                        print(f'[Drive] Response bukan JSON: {body[:300]}')
                    return

            except urllib.error.HTTPError as e:
                if e.code in (301, 302, 303, 307, 308):
                    location = e.headers.get('Location', '')
                    print(f'[Drive] Redirect {e.code} → {location[:80]}')

                    # 303 = POST → GET (tidak bisa di-POST ulang)
                    # Untuk Apps Script, kita ABAIKAN redirect dan anggap sukses
                    # karena redirect 302 dari /exec ke echo berarti request diterima
                    if e.code == 302 and 'script.googleusercontent.com' in location:
                        print(f'[Drive] ✅ Apps Script menerima request (302 ke echo = sukses)')
                        return

                    url = location
                    continue
                else:
                    body = e.read().decode('utf-8', errors='replace')
                    print(f'[Drive] HTTP error {e.code}: {body[:300]}')
                    return

        print(f'[Drive] Terlalu banyak redirect ({MAX_REDIRECTS}x)')

    except Exception as e:
        print(f'[Drive] Upload error: {e}')
        import traceback; traceback.print_exc()


def _cover_crop(img, tw, th):
    """Resize + center-crop to fill tw×th (CSS object-fit: cover)."""
    from PIL import Image as _I
    iw, ih = img.size
    scale  = max(tw / iw, th / ih)
    nw, nh = int(iw * scale), int(ih * scale)
    img    = img.resize((nw, nh), _I.LANCZOS)
    l = (nw - tw) // 2
    t = (nh - th) // 2
    return img.crop((l, t, l + tw, t + th))




# ═════════════════════════════════════════════════════════════════════════════
# API ENDPOINTS
# ═════════════════════════════════════════════════════════════════════════════

@app.route('/api/templates')
def api_templates():
    try:
        conn = get_db()
        rows = conn.execute('SELECT * FROM templates WHERE is_active=1 ORDER BY display_order').fetchall()
        conn.close()
        return jsonify({'success': True, 'templates': [dict(r) for r in rows]})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/advertisements')
def api_advertisements():
    try:
        conn = get_db()
        rows = conn.execute('SELECT * FROM advertisements WHERE is_active=1 ORDER BY display_order').fetchall()
        conn.close()
        return jsonify({'success': True, 'advertisements': [dict(r) for r in rows]})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/agendas')
def api_agendas():
    try:
        conn = get_db()
        rows = conn.execute('SELECT * FROM agendas WHERE is_active=1 ORDER BY position').fetchall()
        conn.close()
        return jsonify({'success': True, 'agendas': [dict(r) for r in rows]})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/news')
def api_news():
    try:
        conn = get_db()
        rows = conn.execute('SELECT * FROM news WHERE is_active=1 ORDER BY created_at DESC').fetchall()
        conn.close()
        return jsonify({'success': True, 'news': [dict(r) for r in rows]})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/config')
def api_config():
    try:
        conn = get_db()
        rows = conn.execute('SELECT key, value FROM config').fetchall()
        conn.close()
        return jsonify({'success': True, 'config': {r['key']: r['value'] for r in rows}})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/config/update', methods=['POST'])
def api_config_update():
    try:
        data = request.get_json()
        conn = get_db()
        for k, v in data.items():
            conn.execute('INSERT OR REPLACE INTO config (key,value,updated_at) VALUES (?,?,CURRENT_TIMESTAMP)', (k, str(v)))
        conn.commit(); conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/photobooth/capture', methods=['POST'])
def api_photobooth_capture():
    try:
        data = request.get_json()
        if not data or 'image' not in data:
            return jsonify({'success': False, 'error': 'No image'}), 400
        image_bytes = base64.b64decode(data['image'].split(',')[1])
        timestamp   = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename    = f'photo_{timestamp}.png'
        filepath    = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        with open(filepath, 'wb') as f:
            f.write(image_bytes)
        conn = get_db()
        cur  = conn.cursor()
        cur.execute('INSERT INTO photos (filename, filepath, session_id) VALUES (?,?,?)',
                    (filename, filepath, data.get('session_id', '')))
        photo_id = cur.lastrowid
        conn.commit(); conn.close()
        return jsonify({'success': True, 'photo_id': photo_id, 'filename': filename,
                        'url': url_for('static', filename=f'uploads/{filename}')})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/stats')
def api_stats():
    try:
        conn  = get_db()
        stats = {
            'active_templates': conn.execute('SELECT COUNT(*) FROM templates WHERE is_active=1').fetchone()[0],
            'active_ads':       conn.execute('SELECT COUNT(*) FROM advertisements WHERE is_active=1').fetchone()[0],
            'active_agendas':   conn.execute('SELECT COUNT(*) FROM agendas WHERE is_active=1').fetchone()[0],
            'active_news':      conn.execute('SELECT COUNT(*) FROM news WHERE is_active=1').fetchone()[0],
            'total_photos':     conn.execute('SELECT COUNT(*) FROM photos').fetchone()[0],
        }
        conn.close()
        return jsonify({'success': True, 'stats': stats})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/health')
def health_check():
    return jsonify({
        'status':      'ok',
        'timestamp':   datetime.now().isoformat(),
        'database':    os.path.exists(DB_PATH),
        'mqtt_broker': get_config('mqtt_broker', 'not configured'),
        'device_id':   get_config('device_id', 'unknown')
    })

# ── Error handlers ────────────────────────────────────────────────────────────
@app.errorhandler(404)
def not_found(e):    return jsonify({'error': 'Not found'}), 404
@app.errorhandler(500)
def server_error(e): return jsonify({'error': 'Internal server error'}), 500

# ═════════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ═════════════════════════════════════════════════════════════════════════════
if __name__ == '__main__':
    if not os.path.exists(DB_PATH):
        print("\n❌ Database not found! Run: python3 init_db.py\n")
        sys.exit(1)

    print("\n  DEVICE CONFIGURATION")
    print("="*70)
    print(f"  Device ID   : {get_config('device_id')}")
    print(f"  Device Name : {get_config('device_name')}")
    print(f"  MQTT        : {get_config('mqtt_broker')}:{get_config('mqtt_port')}")
    print(f"  Frames      : {len(os.listdir(PB_FRAMES_DIR))} frame(s)")
    print("="*70)
    print("  http://localhost:5000          — Main display")
    print("  http://localhost:5000/photobooth — Photobooth")
    print("  http://localhost:5000/health   — Health check")
    print("  Ctrl+C to stop\n")

    app.run(host='0.0.0.0', port=5000, debug=False,
            threaded=True, use_reloader=False)
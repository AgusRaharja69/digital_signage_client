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
DB_PATH      = os.path.join(BASE_DIR, 'db', 'signage.db')

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
# MAIN SIGNAGE ROUTES
# ═════════════════════════════════════════════════════════════════════════════

@app.route('/')
def index():
    try:
        conn = get_db()
        templates = [dict(r) for r in conn.execute('SELECT * FROM templates WHERE is_active=1 ORDER BY display_order').fetchall()]
        ads       = [dict(r) for r in conn.execute('SELECT * FROM advertisements WHERE is_active=1 ORDER BY display_order').fetchall()]
        agendas   = [dict(r) for r in conn.execute('SELECT * FROM agendas WHERE is_active=1 ORDER BY position').fetchall()]
        news      = [dict(r) for r in conn.execute('SELECT * FROM news WHERE is_active=1 ORDER BY created_at DESC').fetchall()]
        device_name = get_config('device_name', 'Digital Signage')
        conn.close()
        return render_template('index.html',
                               templates=templates, ads=ads,
                               agendas=agendas, news=news,
                               device_name=device_name,
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
    pb_loader = jinja2.FileSystemLoader(PB_TEMPLATE_DIR)
    pb_env    = jinja2.Environment(loader=pb_loader)
    tmpl      = pb_env.get_template('photobooth.html')
    html      = tmpl.render(frames=frames)
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


@app.route('/photobooth/compose', methods=['POST'])
def pb_compose():
    """
    Composite 3 captured photos into the selected frame.
    Frame uses black slots (RGB, no transparency) — we use a black-pixel
    mask to cut holes and paste photos underneath the frame artwork.
    """
    try:
        import io as _io
        import numpy as np
        from PIL import Image

        data       = request.get_json()
        photos_b64 = data.get('photos', [])
        frame_name = data.get('frame', 'frame1.PNG')

        if len(photos_b64) != 3:
            return jsonify({'success': False, 'error': 'Need 3 photos'}), 400

        # Try both .PNG and .png extensions
        frame_path = os.path.join(PB_FRAMES_DIR, frame_name)
        if not os.path.exists(frame_path):
            # Try alternate case
            alt = frame_name.replace('.png', '.PNG').replace('.PNG', '.png')
            frame_path = os.path.join(PB_FRAMES_DIR, alt)
            if not os.path.exists(frame_path):
                return jsonify({'success': False, 'error': f'Frame not found: {frame_name}'}), 404

        frame_img = Image.open(frame_path).convert('RGB')
        fw, fh    = frame_img.size   # 1000 × 2000
        frame_arr = np.array(frame_img)

        # Build black hole mask: pixels where R<20, G<20, B<20
        hole_mask = (
            (frame_arr[:,:,0] < 20) &
            (frame_arr[:,:,1] < 20) &
            (frame_arr[:,:,2] < 20)
        )

        # Start with a copy of the frame
        result_arr = frame_arr.copy()

        # Build photo layer — paint each photo into its slot position
        photo_layer = np.zeros((fh, fw, 3), dtype=np.uint8)

        for i, b64_data in enumerate(photos_b64):
            x, y, sw, sh = PB_SLOTS[i]

            if ',' in b64_data:
                b64_data = b64_data.split(',', 1)[1]

            photo_bytes   = base64.b64decode(b64_data)
            photo_img     = Image.open(_io.BytesIO(photo_bytes)).convert('RGB')
            photo_resized = _cover_crop(photo_img, sw, sh)
            photo_arr     = np.array(photo_resized)

            photo_layer[y:y+sh, x:x+sw] = photo_arr

        # Replace black holes in frame with photo pixels
        result_arr[hole_mask] = photo_layer[hole_mask]

        # Save
        result_img = Image.fromarray(result_arr)
        timestamp  = datetime.now().strftime('%Y%m%d_%H%M%S')
        out_name   = f'photo_{timestamp}.jpg'
        out_path   = os.path.join(PB_CAPTURES_DIR, out_name)
        result_img.save(out_path, 'JPEG', quality=95, optimize=True)

        print(f'[Photobooth] Saved: {out_path}  ({fw}x{fh})')

        return jsonify({
            'success':  True,
            'filename': out_name,
            'url':      f'/photobooth/imgs/captures/{out_name}'
        })

    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


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
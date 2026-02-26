#!/usr/bin/env python3
"""
Photobooth App — apps/photobooth/photobooth.py
Standalone Flask sub-app for the Digital Signage system.

Routes:
  GET  /photobooth/           → photobooth UI
  GET  /photobooth/frames     → list available frames (JSON)
  POST /photobooth/capture    → receive base64 photo, return index
  POST /photobooth/compose    → composite 3 photos into selected frame, save PNG
  GET  /photobooth/captures/<file> → serve saved composite image
"""

import os
import json
import base64
import io
from datetime import datetime
from flask import Flask, render_template, jsonify, request, send_from_directory, redirect

# ── Paths ────────────────────────────────────────────────────────────────────
BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
FRAMES_DIR  = os.path.join(BASE_DIR, 'imgs', 'frames')
CAPTURES_DIR= os.path.join(BASE_DIR, 'imgs', 'captures')
LOGOS_DIR   = os.path.join(BASE_DIR, 'imgs', 'logos')
TEMPLATE_DIR= os.path.join(BASE_DIR, 'templates')
CSS_DIR     = os.path.join(BASE_DIR, 'css')
JS_DIR      = os.path.join(BASE_DIR, 'js')

os.makedirs(CAPTURES_DIR, exist_ok=True)

# ── Photo slot positions (detected from frame images 1000×2000) ──────────────
# Each slot: (x, y, width, height) in pixels on the 1000×2000 canvas
PHOTO_SLOTS = [
    (111, 441,  775, 364),   # slot 1
    (111, 855,  775, 364),   # slot 2
    (112, 1269, 774, 364),   # slot 3
]

# ── Flask app ─────────────────────────────────────────────────────────────────
app = Flask(
    __name__,
    template_folder=TEMPLATE_DIR,
    static_folder=BASE_DIR,        # serve everything under /photobooth/static/
    static_url_path='/photobooth/static'
)

# ── Routes ─────────────────────────────────────────────────────────────────────

@app.route('/photobooth/')
@app.route('/photobooth')
def index():
    frames = sorted([
        f for f in os.listdir(FRAMES_DIR)
        if f.lower().endswith(('.png', '.jpg', '.jpeg'))
    ])
    return render_template('photobooth.html', frames=frames)


@app.route('/photobooth/frames')
def list_frames():
    frames = sorted([
        f for f in os.listdir(FRAMES_DIR)
        if f.lower().endswith(('.png', '.jpg', '.jpeg'))
    ])
    return jsonify({'frames': frames})


@app.route('/photobooth/imgs/frames/<filename>')
def serve_frame(filename):
    return send_from_directory(FRAMES_DIR, filename)


@app.route('/photobooth/imgs/captures/<filename>')
def serve_capture(filename):
    return send_from_directory(CAPTURES_DIR, filename)


@app.route('/photobooth/compose', methods=['POST'])
def compose():
    """
    Composite 3 captured photos into the selected frame.
    Frame uses black slots (RGB, no transparency) — black-pixel mask approach.
    """
    try:
        import io as _io
        import numpy as np
        from PIL import Image

        data       = request.get_json()
        photos_b64 = data.get('photos', [])
        frame_name = data.get('frame', 'frame1.PNG')

        if len(photos_b64) != 3:
            return jsonify({'success': False, 'error': 'Need exactly 3 photos'}), 400

        frame_path = os.path.join(FRAMES_DIR, frame_name)
        if not os.path.exists(frame_path):
            alt = frame_name.replace('.png','.PNG').replace('.PNG','.png')
            frame_path = os.path.join(FRAMES_DIR, alt)
            if not os.path.exists(frame_path):
                return jsonify({'success': False, 'error': f'Frame not found: {frame_name}'}), 404

        frame_img = Image.open(frame_path).convert('RGB')
        fw, fh    = frame_img.size
        frame_arr = np.array(frame_img)

        # Black hole mask
        hole_mask = (frame_arr[:,:,0]<20) & (frame_arr[:,:,1]<20) & (frame_arr[:,:,2]<20)

        # Photo layer
        photo_layer = np.zeros((fh, fw, 3), dtype=np.uint8)

        for i, b64_data in enumerate(photos_b64):
            x, y, sw, sh = PHOTO_SLOTS[i]
            if ',' in b64_data:
                b64_data = b64_data.split(',', 1)[1]
            photo_bytes   = base64.b64decode(b64_data)
            photo_img     = Image.open(_io.BytesIO(photo_bytes)).convert('RGB')
            photo_resized = _cover_crop(photo_img, sw, sh)
            photo_layer[y:y+sh, x:x+sw] = np.array(photo_resized)

        result_arr = frame_arr.copy()
        result_arr[hole_mask] = photo_layer[hole_mask]

        result_img = Image.fromarray(result_arr)
        timestamp  = datetime.now().strftime('%Y%m%d_%H%M%S')
        out_name   = f'photo_{timestamp}.jpg'
        out_path   = os.path.join(CAPTURES_DIR, out_name)
        result_img.save(out_path, 'JPEG', quality=95, optimize=True)

        print(f'[Photobooth] Saved: {out_path}')

        return jsonify({
            'success':  True,
            'filename': out_name,
            'url':      f'/photobooth/imgs/captures/{out_name}'
        })

    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


# ── Helpers ────────────────────────────────────────────────────────────────────

def _cover_crop(img, target_w, target_h):
    """Resize image to fill target dimensions, center-cropped (like CSS object-fit:cover)."""
    from PIL import Image as PILImage

    iw, ih = img.size
    scale  = max(target_w / iw, target_h / ih)
    new_w  = int(iw * scale)
    new_h  = int(ih * scale)

    img    = img.resize((new_w, new_h), PILImage.LANCZOS)

    left   = (new_w - target_w) // 2
    top    = (new_h - target_h) // 2
    return img.crop((left, top, left + target_w, top + target_h))


# ── Entry point ────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    print('='*60)
    print('  Photobooth App')
    print(f'  Frames dir  : {FRAMES_DIR}')
    print(f'  Captures dir: {CAPTURES_DIR}')
    print('  URL: http://localhost:5001/photobooth/')
    print('='*60)

    app.run(host='0.0.0.0', port=5001, debug=False, threaded=True)
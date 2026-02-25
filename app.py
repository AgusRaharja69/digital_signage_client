#!/usr/bin/env python3
"""
Digital Signage Client - Dynamic Template System
Flask app dengan support untuk 3 tipe template (HTML, Image, Video)
dan advertisement popup system
"""

import os
import sys
from flask import Flask, render_template, request, redirect, url_for, jsonify, send_from_directory
from datetime import datetime
import sqlite3
import base64
from werkzeug.utils import secure_filename
import json

# FORCE ABSOLUTE PATHS
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = os.path.join(BASE_DIR, 'templates')
STATIC_DIR = os.path.join(BASE_DIR, 'static')
DB_PATH = os.path.join(BASE_DIR, 'db', 'signage.db')

# Debug info
print("="*70)
print("🚀 DIGITAL SIGNAGE CLIENT - DYNAMIC TEMPLATE SYSTEM")
print("="*70)
print(f"📁 BASE DIR     : {BASE_DIR}")
print(f"📁 TEMPLATE DIR : {TEMPLATE_DIR}")
print(f"📁 STATIC DIR   : {STATIC_DIR}")
print(f"💾 DATABASE     : {DB_PATH}")
print(f"✓ DB exists     : {os.path.exists(DB_PATH)}")
print("="*70)

# Initialize Flask
app = Flask(__name__,
            template_folder=TEMPLATE_DIR,
            static_folder=STATIC_DIR)

app.config['UPLOAD_FOLDER'] = os.path.join(STATIC_DIR, 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif', 'mp4', 'webm', 'avi', 'mov'}

# Ensure folders exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'ads'), exist_ok=True)
os.makedirs(os.path.join(STATIC_DIR, 'imgs'), exist_ok=True)

def get_db():
    """Get database connection"""
    if not os.path.exists(DB_PATH):
        print(f"❌ Database not found: {DB_PATH}")
        print("Please run: python3 init_db.py")
        sys.exit(1)
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def get_config(key, default=None):
    """Get configuration value"""
    try:
        conn = get_db()
        result = conn.execute('SELECT value FROM config WHERE key = ?', (key,)).fetchone()
        conn.close()
        return result['value'] if result else default
    except:
        return default

def set_config(key, value):
    """Set configuration value"""
    try:
        conn = get_db()
        conn.execute('''
            INSERT OR REPLACE INTO config (key, value, updated_at) 
            VALUES (?, ?, CURRENT_TIMESTAMP)
        ''', (key, value))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error setting config: {e}")
        return False

# ========================
# MAIN ROUTES
# ========================

@app.route('/')
def index():
    try:
        conn = get_db()
        
        # Convert Row to dict
        templates = [dict(row) for row in conn.execute('''
            SELECT * FROM templates 
            WHERE is_active = 1 
            ORDER BY display_order ASC
        ''').fetchall()]
        
        ads = [dict(row) for row in conn.execute('''
            SELECT * FROM advertisements 
            WHERE is_active = 1 
            ORDER BY display_order ASC
        ''').fetchall()]
        
        agendas = [dict(row) for row in conn.execute('''
            SELECT * FROM agendas 
            WHERE is_active = 1 
            ORDER BY position ASC
        ''').fetchall()]
        
        news = [dict(row) for row in conn.execute('''
            SELECT * FROM news 
            WHERE is_active = 1 
            ORDER BY created_at DESC
        ''').fetchall()]
        
        device_name = get_config('device_name', 'Digital Signage')
        
        conn.close()
        
        return render_template('index.html',
                             templates=templates,
                             ads=ads,
                             agendas=agendas,
                             news=news,
                             device_name=device_name,
                             current_time=datetime.now())
    
    except Exception as e:
        print(f"❌ Error in index route: {e}")
        import traceback
        traceback.print_exc()
        return f"<h1>Error</h1><p>{str(e)}</p>", 500

@app.route('/photobooth')
def photobooth():
    """Photo booth page (dari apps/photobooth)"""
    try:
        return render_template('photobooth.html')
    except Exception as e:
        print(f"❌ Error in photobooth route: {e}")
        return f"<h1>Error</h1><p>{str(e)}</p>", 500

# ========================
# API ENDPOINTS
# ========================

@app.route('/api/templates')
def api_templates():
    """Get active templates"""
    try:
        conn = get_db()
        templates = conn.execute('''
            SELECT * FROM templates 
            WHERE is_active = 1 
            ORDER BY display_order ASC
        ''').fetchall()
        conn.close()
        
        return jsonify({
            'success': True,
            'templates': [dict(row) for row in templates]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/advertisements')
def api_advertisements():
    """Get active advertisements"""
    try:
        conn = get_db()
        ads = conn.execute('''
            SELECT * FROM advertisements 
            WHERE is_active = 1 
            ORDER BY display_order ASC
        ''').fetchall()
        conn.close()
        
        return jsonify({
            'success': True,
            'advertisements': [dict(row) for row in ads]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/agendas')
def api_agendas():
    """Get active agendas"""
    try:
        conn = get_db()
        agendas = conn.execute('''
            SELECT * FROM agendas 
            WHERE is_active = 1 
            ORDER BY position ASC
        ''').fetchall()
        conn.close()
        
        return jsonify({
            'success': True,
            'agendas': [dict(row) for row in agendas]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/news')
def api_news():
    """Get active news"""
    try:
        conn = get_db()
        news = conn.execute('''
            SELECT * FROM news 
            WHERE is_active = 1 
            ORDER BY created_at DESC
        ''').fetchall()
        conn.close()
        
        return jsonify({
            'success': True,
            'news': [dict(row) for row in news]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/config')
def api_config():
    """Get configuration"""
    try:
        conn = get_db()
        configs = conn.execute('SELECT key, value FROM config').fetchall()
        conn.close()
        
        config_dict = {row['key']: row['value'] for row in configs}
        
        return jsonify({
            'success': True,
            'config': config_dict
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/config/update', methods=['POST'])
def api_config_update():
    """Update configuration"""
    try:
        data = request.get_json()
        
        conn = get_db()
        for key, value in data.items():
            conn.execute('''
                INSERT OR REPLACE INTO config (key, value, updated_at) 
                VALUES (?, ?, CURRENT_TIMESTAMP)
            ''', (key, str(value)))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Config updated'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/photobooth/capture', methods=['POST'])
def api_photobooth_capture():
    """Save photobooth capture"""
    try:
        data = request.get_json()
        
        if not data or 'image' not in data:
            return jsonify({'success': False, 'error': 'No image data'}), 400
        
        # Decode base64 image
        image_data = data['image'].split(',')[1]
        image_bytes = base64.b64decode(image_data)
        
        # Generate filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'photo_{timestamp}.png'
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        # Save file
        with open(filepath, 'wb') as f:
            f.write(image_bytes)
        
        # Save to database
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO photos (filename, filepath, session_id)
            VALUES (?, ?, ?)
        ''', (filename, filepath, data.get('session_id', '')))
        photo_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'photo_id': photo_id,
            'filename': filename,
            'url': url_for('static', filename=f'uploads/{filename}')
        })
    
    except Exception as e:
        print(f"❌ Error saving photo: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/stats')
def api_stats():
    """Get statistics"""
    try:
        conn = get_db()
        
        stats = {
            'active_templates': conn.execute('SELECT COUNT(*) FROM templates WHERE is_active = 1').fetchone()[0],
            'active_ads': conn.execute('SELECT COUNT(*) FROM advertisements WHERE is_active = 1').fetchone()[0],
            'active_agendas': conn.execute('SELECT COUNT(*) FROM agendas WHERE is_active = 1').fetchone()[0],
            'active_news': conn.execute('SELECT COUNT(*) FROM news WHERE is_active = 1').fetchone()[0],
            'total_photos': conn.execute('SELECT COUNT(*) FROM photos').fetchone()[0],
        }
        
        conn.close()
        
        return jsonify({'success': True, 'stats': stats})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.now().isoformat(),
        'database': os.path.exists(DB_PATH),
        'mqtt_broker': get_config('mqtt_broker', 'not configured'),
        'device_id': get_config('device_id', 'unknown')
    })

# Error handlers
@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def server_error(e):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    # Check database
    if not os.path.exists(DB_PATH):
        print("\n❌ Database not found!")
        print("Please run: python3 init_db.py\n")
        sys.exit(1)
    
    # Show configuration
    print("\n📋 DEVICE CONFIGURATION")
    print("="*70)
    print(f"Device ID    : {get_config('device_id')}")
    print(f"Device Name  : {get_config('device_name')}")
    print(f"MQTT Broker  : {get_config('mqtt_broker')}:{get_config('mqtt_port')}")
    print(f"MQTT Topic   : {get_config('mqtt_topic')}")
    print(f"Display      : {get_config('display_width')}x{get_config('display_height')}")
    print("="*70)
    
    # Run Flask app
    print("\n✅ Starting Digital Signage Client...")
    print("🌐 Main Display: http://localhost:5000")
    print("📸 Photo Booth : http://localhost:5000/photobooth")
    print("🔍 Health Check: http://localhost:5000/health")
    print("\nPress Ctrl+C to stop\n")
    
    app.run(host='0.0.0.0', port=5000, debug=True)

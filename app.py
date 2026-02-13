import os
import sys
from flask import Flask, render_template, request, redirect, url_for, jsonify
from datetime import datetime
import sqlite3
import base64

# ? PAKSA PATH ABSOLUT - INI KUNCINYA!
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = os.path.join(BASE_DIR, 'templates')
STATIC_DIR = os.path.join(BASE_DIR, 'static')

# Debug - cetak path
print("="*60)
print("? DEBUG INFO:")
print(f"? BASE DIR     : {BASE_DIR}")
print(f"? TEMPLATE DIR : {TEMPLATE_DIR}")
print(f"? STATIC DIR   : {STATIC_DIR}")
print(f"? index.html exists : {os.path.exists(os.path.join(TEMPLATE_DIR, 'index.html'))}")
print("="*60)

# Inisialisasi Flask dengan path ABSOLUT
app = Flask(__name__,
            template_folder=TEMPLATE_DIR,
            static_folder=STATIC_DIR)

app.config['UPLOAD_FOLDER'] = os.path.join(STATIC_DIR, 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

# Ensure folders exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(os.path.join(STATIC_DIR, 'logos'), exist_ok=True)

def get_db():
    db_path = os.path.join(BASE_DIR, 'photostation.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def index():
    try:
        conn = get_db()
        
        # Get active agendas
        agendas = conn.execute('''
            SELECT * FROM agendas 
            WHERE is_active = 1 
            ORDER BY position ASC 
            LIMIT 3
        ''').fetchall()
        
        # Get news items
        news = conn.execute('''
            SELECT * FROM news 
            WHERE is_active = 1 
            ORDER BY created_at DESC
        ''').fetchall()
        
        # Get logo and barcode
        settings = conn.execute('SELECT * FROM settings WHERE id = 1').fetchone()
        
        conn.close()
        
        return render_template('index.html', 
                             agendas=agendas, 
                             news=news, 
                             settings=settings)
    except Exception as e:
        return f"Error: {str(e)}<br>Template path: {TEMPLATOR_DIR}", 500

@app.route('/photobooth')
def photobooth():
    return render_template('photobooth.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

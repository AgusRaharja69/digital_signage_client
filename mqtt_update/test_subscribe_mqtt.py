import paho.mqtt.client as mqtt
import os
import time
import configparser

# Membaca konfigurasi dari config.ini
config = configparser.ConfigParser()
config.read('config.ini')

# Mengambil nilai konfigurasi
broker = config['DEFAULT']['Broker']
port = int(config['DEFAULT']['Port'])
username = config['DEFAULT']['UserID']
password = config['DEFAULT']['Pass']
keepalive = int(config['DEFAULT']['KAI'])
topic = "signage/sma-n-1-denpasar/promo/content"  # Topik diubah untuk data teks

# Direktori untuk menyimpan file teks
OUTPUT_DIR = "session_text"
os.makedirs(OUTPUT_DIR, exist_ok=True)

def on_message(client, userdata, msg):
    # Decode payload dari bytes ke string
    message = msg.payload.decode('utf-8')
    print(f"📩 Pesan masuk di topic {msg.topic}: {message}")
    
    # Menyimpan pesan ke file dengan timestamp
    filename = os.path.join(OUTPUT_DIR, f"text_{int(time.time())}.txt")
    with open(filename, "w", encoding='utf-8') as f:
        f.write(message)
    print(f"✅ Teks disimpan: {filename}")

# Inisialisasi client MQTT
client = mqtt.Client(protocol=mqtt.MQTTv311)
if username and password:
    client.username_pw_set(username, password)

# Set callback untuk pesan masuk
client.on_message = on_message

# Koneksi ke broker
try:
    client.connect(broker, port, keepalive)
except Exception as e:
    print(f"❌ Gagal terkoneksi ke broker: {e}")
    exit(1)

# Subscribe ke topik
client.subscribe(topic, qos=1)
print(f"📡 Listening on topic: {topic}")

# Mulai loop untuk menerima pesan
try:
    client.loop_forever()
except KeyboardInterrupt:
    print("\n🛑 Program dihentikan oleh pengguna")
    client.disconnect()
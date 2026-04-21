import paho.mqtt.client as mqtt
import configparser
import os
import time

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
cfg = configparser.ConfigParser()
cfg.read(os.path.join(BASE_DIR, 'config.ini'))

USERNAME  = 'mqtt_user'
PASSWORD  = 'W@2mad3w@_mqtt'

BROKER = "145.79.12.159"
PORT   = 1883
TOPIC  = "signage/sma-n-1-kuta-utara/"

done = False

def on_connect(client, userdata, flags, rc):
    global done
    if rc == 0:
        print(f"✅ Connected ke {BROKER}:{PORT}")
        print(f"🧹 Menghapus retained message di topic: {TOPIC}")
        client.publish(TOPIC, payload=None, qos=1, retain=True)
        time.sleep(1)
        client.disconnect()
        done = True
    else:
        print(f"❌ Gagal connect, rc={rc}")
        done = True

client = mqtt.Client(client_id="retained_cleaner")

if USERNAME:
    client.username_pw_set(USERNAME, PASSWORD)

client.on_connect = on_connect
client.connect(BROKER, PORT, 60)
client.loop_forever()

print("✅ Selesai.")
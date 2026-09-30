"""
MQTT Subscriber for SDN Telemetry and Energy Monitoring.
Subscribes to cloud monitoring and energy topics, writing live updates
to local data storage.
"""

import json
import ssl
import sys
from pathlib import Path
import certifi
import paho.mqtt.client as mqtt

from config import (
    MQTT_BROKER,
    MQTT_PORT,
    MQTT_USERNAME,
    MQTT_PASSWORD,
    MQTT_USE_TLS,
    ENERGY_TOPIC,
    TOPIC_SERVERS_METRICS,
    TOPIC_WORKLOADS,
    TOPIC_SDN_DECISIONS,
    TOPIC_LOADBALANCER_STATUS
)

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
LATEST_DATA_FILE = DATA_DIR / "latestdata.json"
LEGACY_DATA_FILE = Path(__file__).resolve().parent / "latest_data.json"


def on_connect(client, userdata, flags, reason_code, properties=None):
    if reason_code == 0:
        print("[MQTT Sub] SUCCESS: Connected to HiveMQ Cloud!")
        client.subscribe([
            (ENERGY_TOPIC, 0),
            (TOPIC_SERVERS_METRICS, 0),
            (TOPIC_WORKLOADS, 0),
            (TOPIC_SDN_DECISIONS, 0),
            (TOPIC_LOADBALANCER_STATUS, 0)
        ])
        print(f"[MQTT Sub] Subscribed to cloud and energy topics.")
    else:
        print(f"[MQTT Sub] Connection failed. Code: {reason_code}")


def on_message(client, userdata, message):
    try:
        topic = message.topic
        payload_str = message.payload.decode("utf-8")
        data = json.loads(payload_str)

        print(f"\n[MQTT Incoming] Topic: {topic}")

        if topic == ENERGY_TOPIC:
            # Update legacy latest_data.json
            with open(LEGACY_DATA_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
            print(f"Updated {LEGACY_DATA_FILE.name}: Power={data.get('power')}W")

    except Exception as error:
        print(f"[MQTT Sub] Processing error: {error}")


def start_subscriber():
    client = mqtt.Client(
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        client_id="sdn_cloud_subscriber"
    )

    if MQTT_USERNAME and MQTT_PASSWORD:
        client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)

    if MQTT_USE_TLS:
        ssl_context = ssl.create_default_context(cafile=certifi.where())
        client.tls_set_context(ssl_context)

    client.on_connect = on_connect
    client.on_message = on_message

    print(f"Connecting to {MQTT_BROKER}:{MQTT_PORT}...")
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        print("Waiting for cloud telemetry... Press Ctrl+C to exit.\n")
        client.loop_forever()
    except KeyboardInterrupt:
        print("\nStopping subscriber...")
    except Exception as e:
        print(f"MQTT Subscriber connection error: {e}")
    finally:
        client.disconnect()


if __name__ == "__main__":
    start_subscriber()
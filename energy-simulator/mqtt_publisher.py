"""
MQTT Publisher for SDN Telemetry and Energy Monitoring.
Publishes metrics to HiveMQ Cloud or local Mosquitto broker
with automatic fallback and non-blocking reconnects.
"""

import json
import time
import ssl
import sys
from pathlib import Path
from typing import Dict, Any, Optional

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
from energy_simulator import generate_energy_data


class MQTTEmitter:
    """Manages an MQTT connection and publishes multi-topic cloud telemetry."""

    def __init__(self, client_id: str = "sdn_cloud_publisher"):
        self.connected = False
        self.client_id = client_id
        self.client: Optional[mqtt.Client] = None
        self._setup_client()

    def _on_connect(self, client, userdata, flags, reason_code, properties=None):
        if reason_code == 0:
            self.connected = True
            print(f"[MQTT] SUCCESS: Connected to broker {MQTT_BROKER}:{MQTT_PORT}")
        else:
            self.connected = False
            print(f"[MQTT] Connection returned code {reason_code}")

    def _on_disconnect(self, client, userdata, flags, reason_code, properties=None):
        self.connected = False
        print("[MQTT] Disconnected from broker.")

    def _setup_client(self):
        try:
            self.client = mqtt.Client(
                callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
                client_id=self.client_id
            )
            if MQTT_USERNAME and MQTT_PASSWORD:
                self.client.username_pw_set(
                    username=MQTT_USERNAME,
                    password=MQTT_PASSWORD
                )

            if MQTT_USE_TLS:
                ssl_context = ssl.create_default_context(cafile=certifi.where())
                self.client.tls_set_context(ssl_context)

            self.client.on_connect = self._on_connect
            self.client.on_disconnect = self._on_disconnect
        except Exception as e:
            print(f"[MQTT] Client setup notice (offline mode available): {e}")

    def connect(self, timeout: int = 4) -> bool:
        """Attempts connection in background without hanging system."""
        if not self.client:
            return False
        try:
            print(f"[MQTT] Connecting to {MQTT_BROKER}:{MQTT_PORT}...")
            self.client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
            self.client.loop_start()
            # Wait briefly for handshake
            start = time.time()
            while time.time() - start < timeout:
                if self.connected:
                    return True
                time.sleep(0.2)
            print("[MQTT] Connection timed out; continuing with local fallback.")
            return False
        except Exception as e:
            print(f"[MQTT] Could not connect to broker ({e}); continuing with local fallback.")
            return False

    def publish_topic(self, topic: str, payload: Any) -> bool:
        """Safely publishes JSON message to a topic."""
        if not self.connected or not self.client:
            return False
        try:
            msg = json.dumps(payload) if not isinstance(payload, str) else payload
            res = self.client.publish(topic, msg, qos=1)
            return res.rc == mqtt.MQTT_ERR_SUCCESS
        except Exception:
            return False

    def publish_snapshot(self, snapshot: Dict[str, Any]) -> None:
        """Publishes all SDN telemetry channels."""
        if not self.connected:
            return
        # 1. Servers metrics
        self.publish_topic(TOPIC_SERVERS_METRICS, snapshot.get("servers", []))
        # 2. Workload summary
        self.publish_topic(TOPIC_WORKLOADS, {
            "summary": snapshot.get("summary", {}),
            "queued": snapshot.get("queued_items", [])
        })
        # 3. SDN Decisions & Flow table
        self.publish_topic(TOPIC_SDN_DECISIONS, {
            "flow_table": snapshot.get("flow_table", []),
            "weights": snapshot.get("weights", {})
        })
        # 4. Load balancer status
        self.publish_topic(TOPIC_LOADBALANCER_STATUS, {
            "status": "ACTIVE" if snapshot.get("is_running") else "PAUSED",
            "overloaded_count": snapshot.get("summary", {}).get("overloaded_servers", 0),
            "total_migrations": snapshot.get("summary", {}).get("total_migrations", 0)
        })
        # 5. Energy telemetry
        legacy_energy = {
            "timestamp": snapshot.get("timestamp"),
            "voltage": snapshot.get("voltage"),
            "current": snapshot.get("current"),
            "power": snapshot.get("power"),
            "power_factor": snapshot.get("power_factor"),
            "energy": snapshot.get("energy")
        }
        self.publish_topic(ENERGY_TOPIC, legacy_energy)

    def close(self):
        if self.client:
            try:
                self.client.loop_stop()
                self.client.disconnect()
            except Exception:
                pass


if __name__ == "__main__":
    emitter = MQTTEmitter()
    emitter.connect(timeout=3)

    print("\nStarting MQTT Telemetry Publisher...")
    print("Publishes server & energy telemetry every 2 seconds. Press Ctrl+C to stop.\n")

    try:
        while True:
            data = generate_energy_data()
            if emitter.connected:
                emitter.publish_topic(ENERGY_TOPIC, data)
                print(f"[MQTT Published] {ENERGY_TOPIC} -> Power: {data['power']}W | Energy: {data['energy']}kWh")
            else:
                print(f"[Local Mode] Generated: Power: {data['power']}W (MQTT broker offline)")
            time.sleep(2)
    except KeyboardInterrupt:
        print("\nStopping MQTT Publisher...")
    finally:
        emitter.close()
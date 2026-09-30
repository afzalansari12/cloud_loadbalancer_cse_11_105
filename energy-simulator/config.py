# ==========================================
# HIVEMQ CLOUD & MQTT CONFIGURATION
# ==========================================
import os
import sys
from pathlib import Path

# Ensure root directory is in sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

try:
    from sdn_config.config import (
        MQTT_BROKER as _BROKER,
        MQTT_PORT as _PORT,
        MQTT_USERNAME as _USER,
        MQTT_PASSWORD as _PASS,
        MQTT_USE_TLS as _TLS,
        TARIFF_PER_KWH as _TARIFF,
        TOPIC_SERVERS_METRICS,
        TOPIC_WORKLOADS,
        TOPIC_SDN_DECISIONS,
        TOPIC_LOADBALANCER_STATUS,
        TOPIC_ENERGY_DATA
    )
    MQTT_BROKER = _BROKER
    MQTT_PORT = _PORT
    MQTT_USERNAME = _USER
    MQTT_PASSWORD = _PASS
    MQTT_USE_TLS = _TLS
    TARIFF_PER_KWH = _TARIFF
    ENERGY_TOPIC = TOPIC_ENERGY_DATA
    ALERT_TOPIC = "smart_energy/alert"
except ImportError:
    MQTT_BROKER = os.getenv("MQTT_BROKER", "480b2e52602e45f7b1ea788c58a4bf0c.s1.eu.hivemq.cloud")
    MQTT_PORT = int(os.getenv("MQTT_PORT", "8883"))
    MQTT_USERNAME = os.getenv("MQTT_USERNAME", "afzalansari_12")
    MQTT_PASSWORD = os.getenv("MQTT_PASSWORD", "329NWfftvDPk9!d")
    MQTT_USE_TLS = os.getenv("MQTT_USE_TLS", "true").lower() in ("true", "1", "yes")
    TARIFF_PER_KWH = float(os.getenv("TARIFF_PER_KWH", "8.0"))
    ENERGY_TOPIC = "smart_energy/data"
    ALERT_TOPIC = "smart_energy/alert"
    TOPIC_SERVERS_METRICS = "cloud/servers/metrics"
    TOPIC_WORKLOADS = "cloud/workloads"
    TOPIC_SDN_DECISIONS = "sdn/controller/decisions"
    TOPIC_LOADBALANCER_STATUS = "cloud/loadbalancer/status"

POWER_LIMIT = 2000.0
CRITICAL_POWER_LIMIT = 2500.0
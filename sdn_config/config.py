"""
Configuration module for SDN Dynamic Cloud Load Balancer.
Provides centralized, project-relative settings and environment overrides.
"""

import os
from pathlib import Path

# Base Paths (always project-relative, no hardcoded user paths)
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

LATEST_DATA_FILE = DATA_DIR / "latestdata.json"
LEGACY_DATA_FILE = BASE_DIR / "energy-simulator" / "latest_data.json"

# ==========================================
# DEFAULT SERVERS SPECIFICATION
# ==========================================
DEFAULT_SERVERS = [
    {
        "id": "Server-1",
        "name": "US-East Compute 01",
        "cpu_capacity": 8,         # 8 cores
        "ram_capacity": 16.0,      # 16 GB
        "net_capacity": 1000.0,    # 1000 Mbps (1 Gbps)
        "idle_power": 50.0,        # 50 Watts base
        "max_dynamic_power": 120.0 # 120 Watts at 100% load
    },
    {
        "id": "Server-2",
        "name": "US-East Compute 02",
        "cpu_capacity": 8,         # 8 cores
        "ram_capacity": 16.0,      # 16 GB
        "net_capacity": 1000.0,    # 1000 Mbps (1 Gbps)
        "idle_power": 50.0,        # 50 Watts base
        "max_dynamic_power": 120.0 # 120 Watts at 100% load
    },
    {
        "id": "Server-3",
        "name": "US-West High-Perf 03",
        "cpu_capacity": 16,        # 16 cores
        "ram_capacity": 32.0,      # 32 GB
        "net_capacity": 2000.0,    # 2000 Mbps (2 Gbps)
        "idle_power": 85.0,        # 85 Watts base
        "max_dynamic_power": 220.0 # 220 Watts at 100% load
    },
    {
        "id": "Server-4",
        "name": "EU-Central General 04",
        "cpu_capacity": 12,        # 12 cores
        "ram_capacity": 24.0,      # 24 GB
        "net_capacity": 1500.0,    # 1500 Mbps (1.5 Gbps)
        "idle_power": 65.0,        # 65 Watts base
        "max_dynamic_power": 160.0 # 160 Watts at 100% load
    }
]

# ==========================================
# DYNAMIC LOAD-BALANCING WEIGHTS
# Formula:
# Load Score = w_cpu * CPU_util + w_ram * RAM_util + w_net * Net_util
#            + w_count * Count_norm + w_energy * Energy_norm
# ==========================================
DEFAULT_WEIGHTS = {
    "cpu": 0.40,
    "ram": 0.25,
    "net": 0.20,
    "count": 0.10,
    "energy": 0.05
}

# ==========================================
# RESOURCE THRESHOLDS
# ==========================================
THRESHOLDS = {
    "cpu_warning": 70.0,     # Warning when >= 70%
    "cpu_overload": 85.0,    # Overloaded when >= 85%
    "ram_warning": 70.0,     # Warning when >= 70%
    "ram_overload": 85.0,    # Overloaded when >= 85%
    "net_warning": 75.0,     # Warning when >= 75%
    "net_overload": 90.0     # Overloaded when >= 90%
}

# ==========================================
# SIMULATION PARAMETERS
# ==========================================
SIMULATION_CONFIG = {
    "tick_interval_seconds": 1.0,     # Simulation step interval
    "default_arrival_interval": 3.0,  # New workload every ~3 seconds
    "max_queue_size": 50,             # Max queued workloads
    "max_history_points": 60,         # Data points for time-series charts
    "max_activity_logs": 80,          # Live activity log entries to retain
    "auto_migration_enabled": True    # Auto-migrate workloads on overload
}

# ==========================================
# MQTT CONFIGURATION
# Configurable via environment variables with safe fallbacks
# ==========================================
MQTT_ENABLED = os.getenv("MQTT_ENABLED", "true").lower() in ("true", "1", "yes")
MQTT_BROKER = os.getenv("MQTT_BROKER", "480b2e52602e45f7b1ea788c58a4bf0c.s1.eu.hivemq.cloud")
MQTT_PORT = int(os.getenv("MQTT_PORT", "8883"))
MQTT_USERNAME = os.getenv("MQTT_USERNAME", "afzalansari_12")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD", "329NWfftvDPk9!d")
MQTT_USE_TLS = os.getenv("MQTT_USE_TLS", "true").lower() in ("true", "1", "yes")
MQTT_TIMEOUT = int(os.getenv("MQTT_TIMEOUT", "4"))

# MQTT Topics
TOPIC_SERVERS_METRICS = "cloud/servers/metrics"
TOPIC_WORKLOADS = "cloud/workloads"
TOPIC_SDN_DECISIONS = "sdn/controller/decisions"
TOPIC_LOADBALANCER_STATUS = "cloud/loadbalancer/status"
TOPIC_ENERGY_DATA = "smart_energy/data"

# ==========================================
# ELECTRICITY TARIFF (For Energy Cost Calc)
# ==========================================
TARIFF_PER_KWH = float(os.getenv("TARIFF_PER_KWH", "8.0"))

# ==========================================
# REST API CONFIGURATION
# ==========================================
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))

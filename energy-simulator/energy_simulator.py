"""
Energy simulator module.
Generates electrical telemetry and models energy consumption
tied to simulated server workloads.
"""

import os
import json
import random
import time
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_FILE = BASE_DIR / "data" / "latestdata.json"


def generate_energy_data():
    """
    Generates real-time energy telemetry.
    If the SDN cloud simulation is running, bridges data from actual server power;
    otherwise generates realistic baseline telemetry.
    """
    if DATA_FILE.exists():
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                cloud_data = json.load(f)
            summary = cloud_data.get("summary", {})
            power = summary.get("total_power_w", 0.0)
            if power > 0:
                voltage = cloud_data.get("voltage", 230.0)
                current = round(power / voltage, 2) if voltage > 0 else 1.0
                power_factor = cloud_data.get("power_factor", 0.95)
                energy = summary.get("total_energy_kwh", 0.0)
                return {
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "voltage": round(voltage, 2),
                    "current": current,
                    "power": round(power, 2),
                    "power_factor": power_factor,
                    "energy": round(energy, 3),
                    "source": "SDN_SIMULATION"
                }
        except Exception:
            pass

    # Fallback realistic random generator
    voltage = round(random.uniform(220, 240), 2)
    current = round(random.uniform(2, 10), 2)
    power = round(voltage * current, 2)
    power_factor = round(random.uniform(0.80, 0.99), 2)
    energy = round(power / 1000, 3)

    return {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "voltage": voltage,
        "current": current,
        "power": power,
        "power_factor": power_factor,
        "energy": energy,
        "source": "SYNTHETIC"
    }


if __name__ == "__main__":
    print("Starting Standalone Energy Simulator (Press Ctrl+C to stop)...")
    while True:
        data = generate_energy_data()
        print(f"[{data['timestamp']}] Power: {data['power']}W | Voltage: {data['voltage']}V | Source: {data.get('source')}")
        time.sleep(2)
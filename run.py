"""
Main entry point for SDN Dynamic Cloud Load Balancer.
Provides convenient modes to launch the Streamlit dashboard,
the REST API server, or an all-in-one execution stack.
"""

import sys
import os
import argparse
import subprocess
import time
from pathlib import Path

# Ensure root directory is in sys.path
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from sdn_config.config import API_HOST, API_PORT
from simulator.simulation import get_simulation_engine
from api.api_server import run_api_server


def start_dashboard():
    """Launches the modern bright Streamlit SaaS dashboard."""
    dashboard_path = ROOT_DIR / "energy-simulator" / "dashboard.py"
    cmd = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        str(dashboard_path),
        "--server.headless",
        "false",
        "--theme.base",
        "light",
        "--theme.backgroundColor",
        "#f8fafc",
        "--theme.secondaryBackgroundColor",
        "#ffffff",
        "--theme.textColor",
        "#0f172a"
    ]
    print("\n" + "=" * 60)
    print("🚀 Launching SDN Cloud Load Balancer Bright SaaS Dashboard...")
    print(f"Command: {' '.join(cmd)}")
    print("=" * 60 + "\n")
    subprocess.run(cmd)


def start_api():
    """Runs the REST API server."""
    print("\n" + "=" * 60)
    print(f"📡 Starting SDN Simulation REST API on http://{API_HOST}:{API_PORT}...")
    print("=" * 60 + "\n")
    engine = get_simulation_engine()
    engine.start()
    run_api_server(host=API_HOST, port=API_PORT, blocking=True)


def start_cli_monitor():
    """Runs a live console monitoring display."""
    print("\n" + "=" * 60)
    print("💻 Starting SDN Dynamic Cloud Load Balancer CLI Monitor...")
    print("=" * 60 + "\n")
    engine = get_simulation_engine()
    engine.start()

    try:
        while True:
            snap = engine.get_snapshot()
            s = snap["summary"]
            print(f"\r[{snap['time_short']}] Servers: {s['online_servers']}/{s['total_servers']} | "
                  f"Active Tasks: {s['active_workloads']} | Queue: {s['queued_workloads']} | "
                  f"Avg CPU: {s['avg_cpu_percent']}% | Avg RAM: {s['avg_ram_percent']}% | "
                  f"Power: {s['total_power_w']}W | Migrations: {s['total_migrations']}", end="", flush=True)
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping monitor...")
        engine.stop()


def main():
    parser = argparse.ArgumentParser(description="SDN Dynamic Cloud Load Balancer")
    parser.add_argument("--dashboard", action="store_true", help="Launch Streamlit SaaS Dashboard (Default)")
    parser.add_argument("--api", action="store_true", help="Launch REST API Server")
    parser.add_argument("--cli", action="store_true", help="Run terminal console monitor")
    parser.add_argument("--all", action="store_true", help="Run REST API and launch Streamlit dashboard")

    args = parser.parse_args()

    if args.api:
        start_api()
    elif args.cli:
        start_cli_monitor()
    elif args.all:
        print("Starting background REST API server...")
        run_api_server(host=API_HOST, port=API_PORT, blocking=False)
        start_dashboard()
    else:
        # Default is starting dashboard
        start_dashboard()


if __name__ == "__main__":
    main()

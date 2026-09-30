"""
Lightweight REST API Server for SDN Dynamic Cloud Load Balancer.
Uses Python standard http.server with ThreadingHTTPServer. Zero external dependencies required.
"""

import json
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import threading
from typing import Optional

from simulator.simulation import get_simulation_engine
from sdn_config.config import API_HOST, API_PORT


class SimulationAPIHandler(BaseHTTPRequestHandler):
    """Handles REST endpoints for monitoring and controlling the SDN simulation."""

    def _set_headers(self, status_code: int = 200, content_type: str = "application/json"):
        self.send_response(status_code)
        self.send_header("Content-Type", content_type)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_OPTIONS(self):
        self._set_headers(204)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path.rstrip("/")
        engine = get_simulation_engine()
        snapshot = engine.get_snapshot()

        if path == "" or path == "/api" or path == "/api/status":
            response = {
                "status": "RUNNING" if snapshot["is_running"] else "STOPPED",
                "is_paused": snapshot["is_paused"],
                "timestamp": snapshot["timestamp"],
                "summary": snapshot["summary"]
            }
            self._set_headers(200)
            self.wfile.write(json.dumps(response, indent=2).encode())

        elif path == "/api/servers":
            self._set_headers(200)
            self.wfile.write(json.dumps(snapshot["servers"], indent=2).encode())

        elif path == "/api/workloads":
            # Collect active workloads across servers plus queued workloads
            active = []
            for s in engine.sdn_controller.servers.values():
                for w in s.active_workloads.values():
                    active.append(w.to_dict())
            queued = [w.to_dict() for w in engine.sdn_controller.workload_queue]

            response = {
                "active_count": len(active),
                "queued_count": len(queued),
                "active_workloads": active,
                "queued_workloads": queued
            }
            self._set_headers(200)
            self.wfile.write(json.dumps(response, indent=2).encode())

        elif path == "/api/metrics":
            response = {
                "summary": snapshot["summary"],
                "history": snapshot.get("history", [])
            }
            self._set_headers(200)
            self.wfile.write(json.dumps(response, indent=2).encode())

        elif path == "/api/flowtable":
            self._set_headers(200)
            self.wfile.write(json.dumps(snapshot["flow_table"], indent=2).encode())

        elif path == "/metrics":
            # Prometheus exposition format (text/plain)
            lines = []
            s = snapshot["summary"]
            lines.append("# HELP sdn_summary_active_workloads Current number of active workloads running across fleet")
            lines.append("# TYPE sdn_summary_active_workloads gauge")
            lines.append(f"sdn_summary_active_workloads {s['active_workloads']}")

            lines.append("# HELP sdn_summary_queued_workloads Workloads waiting in admission queue")
            lines.append("# TYPE sdn_summary_queued_workloads gauge")
            lines.append(f"sdn_summary_queued_workloads {s['queued_workloads']}")

            lines.append("# HELP sdn_summary_completed_workloads Total completed workloads")
            lines.append("# TYPE sdn_summary_completed_workloads counter")
            lines.append(f"sdn_summary_completed_workloads {s['completed_workloads']}")

            lines.append("# HELP sdn_summary_overloaded_servers Number of servers currently overloaded")
            lines.append("# TYPE sdn_summary_overloaded_servers gauge")
            lines.append(f"sdn_summary_overloaded_servers {s['overloaded_servers']}")

            lines.append("# HELP sdn_summary_avg_cpu_percent Average CPU percentage across online servers")
            lines.append("# TYPE sdn_summary_avg_cpu_percent gauge")
            lines.append(f"sdn_summary_avg_cpu_percent {s['avg_cpu_percent']}")

            lines.append("# HELP sdn_summary_avg_ram_percent Average RAM percentage across online servers")
            lines.append("# TYPE sdn_summary_avg_ram_percent gauge")
            lines.append(f"sdn_summary_avg_ram_percent {s['avg_ram_percent']}")

            lines.append("# HELP sdn_summary_avg_net_percent Average network percentage across online servers")
            lines.append("# TYPE sdn_summary_avg_net_percent gauge")
            lines.append(f"sdn_summary_avg_net_percent {s['avg_net_percent']}")

            lines.append("# HELP sdn_summary_total_power_watts Instantaneous total power in Watts")
            lines.append("# TYPE sdn_summary_total_power_watts gauge")
            lines.append(f"sdn_summary_total_power_watts {s['total_power_w']}")

            lines.append("# HELP sdn_summary_total_energy_kwh Cumulative energy consumption in kWh")
            lines.append("# TYPE sdn_summary_total_energy_kwh counter")
            lines.append(f"sdn_summary_total_energy_kwh {s['total_energy_kwh']}")

            lines.append("# HELP sdn_summary_total_migrations Total autonomous workload live migrations")
            lines.append("# TYPE sdn_summary_total_migrations counter")
            lines.append(f"sdn_summary_total_migrations {s['total_migrations']}")

            lines.append("# HELP sdn_summary_total_failures Total simulated server failures")
            lines.append("# TYPE sdn_summary_total_failures counter")
            lines.append(f"sdn_summary_total_failures {s['total_failures']}")

            # Per-server metrics
            lines.append("# HELP sdn_server_cpu_utilization_percent Server CPU utilization percentage")
            lines.append("# TYPE sdn_server_cpu_utilization_percent gauge")
            for srv in snapshot["servers"]:
                lines.append(f'sdn_server_cpu_utilization_percent{{server_id="{srv["id"]}",name="{srv["name"]}"}} {srv["cpu_utilization"]}')

            lines.append("# HELP sdn_server_ram_utilization_percent Server RAM utilization percentage")
            lines.append("# TYPE sdn_server_ram_utilization_percent gauge")
            for srv in snapshot["servers"]:
                lines.append(f'sdn_server_ram_utilization_percent{{server_id="{srv["id"]}",name="{srv["name"]}"}} {srv["ram_utilization"]}')

            lines.append("# HELP sdn_server_net_utilization_percent Server Network utilization percentage")
            lines.append("# TYPE sdn_server_net_utilization_percent gauge")
            for srv in snapshot["servers"]:
                lines.append(f'sdn_server_net_utilization_percent{{server_id="{srv["id"]}",name="{srv["name"]}"}} {srv["net_utilization"]}')

            lines.append("# HELP sdn_server_power_watts Server power consumption in Watts")
            lines.append("# TYPE sdn_server_power_watts gauge")
            for srv in snapshot["servers"]:
                lines.append(f'sdn_server_power_watts{{server_id="{srv["id"]}",name="{srv["name"]}"}} {srv["current_power_w"]}')

            lines.append("# HELP sdn_server_active_workloads Active workloads on server")
            lines.append("# TYPE sdn_server_active_workloads gauge")
            for srv in snapshot["servers"]:
                lines.append(f'sdn_server_active_workloads{{server_id="{srv["id"]}",name="{srv["name"]}"}} {srv["active_workloads"]}')

            lines.append("# HELP sdn_server_is_online 1 if online, 0 if offline")
            lines.append("# TYPE sdn_server_is_online gauge")
            for srv in snapshot["servers"]:
                lines.append(f'sdn_server_is_online{{server_id="{srv["id"]}",name="{srv["name"]}"}} {1 if srv["is_online"] else 0}')

            output = "\n".join(lines) + "\n"
            self._set_headers(200, content_type="text/plain; version=0.0.4")
            self.wfile.write(output.encode("utf-8"))

        else:
            self._set_headers(404)
            self.wfile.write(json.dumps({"error": f"Endpoint '{path}' not found"}, indent=2).encode())

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path.rstrip("/")
        engine = get_simulation_engine()

        # Read JSON body if present
        content_length = int(self.headers.get("Content-Length", 0))
        body = {}
        if content_length > 0:
            try:
                body_raw = self.rfile.read(content_length)
                body = json.loads(body_raw.decode("utf-8"))
            except Exception:
                body = {}

        if path == "/api/simulation/start":
            engine.start()
            self._set_headers(200)
            self.wfile.write(json.dumps({"status": "SUCCESS", "message": "Simulation started"}).encode())

        elif path == "/api/simulation/stop":
            engine.stop()
            self._set_headers(200)
            self.wfile.write(json.dumps({"status": "SUCCESS", "message": "Simulation stopped"}).encode())

        elif path == "/api/simulation/pause":
            engine.pause()
            self._set_headers(200)
            self.wfile.write(json.dumps({"status": "SUCCESS", "message": "Simulation paused"}).encode())

        elif path == "/api/simulation/reset":
            engine.reset()
            self._set_headers(200)
            self.wfile.write(json.dumps({"status": "SUCCESS", "message": "Simulation reset"}).encode())

        elif path == "/api/workload":
            workload = engine.generate_workload_now(profile=body if body else None)
            self._set_headers(201)
            self.wfile.write(json.dumps({
                "status": "SUCCESS",
                "workload": workload.to_dict()
            }, indent=2).encode())

        elif path == "/api/burst":
            count = int(body.get("count", 5))
            workloads = engine.generate_burst_now(count=count)
            self._set_headers(201)
            self.wfile.write(json.dumps({
                "status": "SUCCESS",
                "injected_count": len(workloads),
                "workloads": [w.to_dict() for w in workloads]
            }, indent=2).encode())

        elif path.startswith("/api/server/") and path.endswith("/failure"):
            # Format: /api/server/{id}/failure
            parts = path.split("/")
            server_id = parts[3]
            success = engine.sdn_controller.simulate_server_failure(server_id)
            if success:
                self._set_headers(200)
                self.wfile.write(json.dumps({
                    "status": "SUCCESS",
                    "message": f"Server {server_id} marked offline and workloads evacuated"
                }).encode())
            else:
                self._set_headers(400)
                self.wfile.write(json.dumps({
                    "status": "FAILED",
                    "message": f"Server {server_id} not found or already offline"
                }).encode())

        elif path.startswith("/api/server/") and path.endswith("/recover"):
            # Format: /api/server/{id}/recover
            parts = path.split("/")
            server_id = parts[3]
            success = engine.sdn_controller.simulate_server_recovery(server_id)
            if success:
                self._set_headers(200)
                self.wfile.write(json.dumps({
                    "status": "SUCCESS",
                    "message": f"Server {server_id} recovered to Healthy"
                }).encode())
            else:
                self._set_headers(400)
                self.wfile.write(json.dumps({
                    "status": "FAILED",
                    "message": f"Server {server_id} not found or already online"
                }).encode())

        else:
            self._set_headers(404)
            self.wfile.write(json.dumps({"error": f"Endpoint '{path}' not found"}, indent=2).encode())

    def log_message(self, format, *args):
        # Suppress verbose standard logging to keep terminal clean
        pass


def run_api_server(host: str = API_HOST, port: int = API_PORT, blocking: bool = True) -> ThreadingHTTPServer:
    """Instantiates and starts the ThreadingHTTPServer."""
    server = ThreadingHTTPServer((host, port), SimulationAPIHandler)
    print(f"[REST API] Server listening on http://{host}:{port}")

    if blocking:
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\n[REST API] Shutting down...")
            server.shutdown()
    else:
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()

    return server


if __name__ == "__main__":
    run_api_server(blocking=True)

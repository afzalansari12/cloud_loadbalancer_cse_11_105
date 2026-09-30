"""
Cloud SDN Simulation Engine.
Coordinates workload generation, SDN control decisions, server ticks,
overload migrations, time-series telemetry aggregation, JSON persistence,
and MQTT broadcasting.
"""

import json
import time
import threading
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path

from sdn_config.config import (
    DEFAULT_SERVERS,
    DEFAULT_WEIGHTS,
    THRESHOLDS,
    SIMULATION_CONFIG,
    LATEST_DATA_FILE,
    LEGACY_DATA_FILE,
    TARIFF_PER_KWH
)
from simulator.workload_generator import WorkloadGenerator, Workload
from simulator.server_simulator import VirtualServer
from controller.load_balancer import DynamicLoadBalancer
from controller.sdn_controller import SDNController
from controller.server_manager import ServerManager


class CloudSimulationEngine:
    """Central simulation orchestrator running the discrete-event cloud SDN loop."""

    def __init__(self):
        self._lock = threading.Lock()
        self.is_running = False
        self.is_paused = False
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

        # Core components
        self.workload_generator = WorkloadGenerator()
        self.load_balancer = DynamicLoadBalancer(weights=DEFAULT_WEIGHTS.copy())

        # Initialize default virtual servers
        servers = [
            VirtualServer(
                server_id=s["id"],
                name=s["name"],
                cpu_capacity=s["cpu_capacity"],
                ram_capacity=s["ram_capacity"],
                net_capacity=s["net_capacity"],
                idle_power=s["idle_power"],
                max_dynamic_power=s["max_dynamic_power"]
            )
            for s in DEFAULT_SERVERS
        ]

        self.sdn_controller = SDNController(
            servers=servers,
            load_balancer=self.load_balancer,
            thresholds=THRESHOLDS.copy()
        )
        self.server_manager = ServerManager(self.sdn_controller)

        # Simulation parameters
        self.arrival_interval = SIMULATION_CONFIG.get("default_arrival_interval", 3.0)
        self.auto_migration_enabled = SIMULATION_CONFIG.get("auto_migration_enabled", True)
        self.last_workload_time = time.time()
        self.tick_count = 0

        # Time-series history buffers for real-time charts
        self.history: List[Dict[str, Any]] = []
        self.max_history_points = SIMULATION_CONFIG.get("max_history_points", 60)

        # Optional MQTT telemetry publisher hook
        self.mqtt_emitter = None

        # Initial export
        self._export_snapshot()

    def set_mqtt_emitter(self, emitter) -> None:
        self.mqtt_emitter = emitter

    def start(self) -> None:
        """Start background simulation thread."""
        with self._lock:
            if self.is_running and not self.is_paused:
                return
            if self.is_paused:
                self.is_paused = False
                self.sdn_controller.log_event("INFO", "Simulation resumed.")
                return

            self.is_running = True
            self.is_paused = False
            self._stop_event.clear()
            self._thread = threading.Thread(target=self._run_loop, daemon=True)
            self._thread.start()
            self.sdn_controller.log_event("SUCCESS", "Simulation engine started.")

    def pause(self) -> None:
        """Pause simulation execution."""
        with self._lock:
            if self.is_running and not self.is_paused:
                self.is_paused = True
                self.sdn_controller.log_event("WARNING", "Simulation paused.")

    def stop(self) -> None:
        """Stop background simulation thread."""
        with self._lock:
            if not self.is_running:
                return
            self.is_running = False
            self.is_paused = False
            self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        self.sdn_controller.log_event("INFO", "Simulation engine stopped.")

    def reset(self) -> None:
        """Resets all servers, workload queues, flow tables, and history."""
        self.stop()
        with self._lock:
            self.workload_generator = WorkloadGenerator()
            self.load_balancer = DynamicLoadBalancer(weights=DEFAULT_WEIGHTS.copy())
            servers = [
                VirtualServer(
                    server_id=s["id"],
                    name=s["name"],
                    cpu_capacity=s["cpu_capacity"],
                    ram_capacity=s["ram_capacity"],
                    net_capacity=s["net_capacity"],
                    idle_power=s["idle_power"],
                    max_dynamic_power=s["max_dynamic_power"]
                )
                for s in DEFAULT_SERVERS
            ]
            self.sdn_controller = SDNController(
                servers=servers,
                load_balancer=self.load_balancer,
                thresholds=THRESHOLDS.copy()
            )
            self.server_manager = ServerManager(self.sdn_controller)
            self.history.clear()
            self.tick_count = 0
            self.last_workload_time = time.time()
            self._export_snapshot()
            self.sdn_controller.log_event("INFO", "Simulation completely reset to factory defaults.")

    def generate_workload_now(self, profile: Optional[Dict[str, Any]] = None) -> Workload:
        """Trigger an immediate single workload generation."""
        with self._lock:
            workload = self.workload_generator.generate(custom_profile=profile)
            self.sdn_controller.route_workload(workload)
            self._export_snapshot()
            return workload

    def generate_burst_now(self, count: int = 5) -> List[Workload]:
        """Trigger a sudden burst of workloads."""
        with self._lock:
            workloads = self.workload_generator.generate_burst(count=count)
            for w in workloads:
                self.sdn_controller.route_workload(w)
            self.sdn_controller.log_event("WARNING", f"BURST TRAFFIC: Injected {count} simultaneous workloads.")
            self._export_snapshot()
            return workloads

    def tick_step(self, elapsed: float = 1.0) -> None:
        """Execute one simulation discrete step."""
        with self._lock:
            self.tick_count += 1
            now = time.time()

            # 1. Automatic Workload Generation based on arrival interval
            if (now - self.last_workload_time) >= self.arrival_interval:
                workload = self.workload_generator.generate()
                self.sdn_controller.route_workload(workload)
                self.last_workload_time = now

            # 2. Advance time on all servers and collect completed jobs
            thresholds = self.sdn_controller.thresholds
            for server in self.sdn_controller.servers.values():
                completed = server.tick(elapsed_seconds=elapsed, thresholds=thresholds)
                for c in completed:
                    # Remove from SDN flow table
                    self.sdn_controller.flow_table.pop(c.workload_id, None)
                    self.sdn_controller.log_event(
                        "INFO",
                        f"Workload {c.workload_id} finished execution on {server.server_id}."
                    )

            # 3. Drain and retry queued workloads
            self.sdn_controller.process_queue()

            # 4. Detect overloads & perform live migrations if enabled
            if self.auto_migration_enabled:
                self.sdn_controller.detect_and_handle_overloads()

            # 5. Record telemetry snapshot
            snapshot = self._compute_snapshot()
            self._record_history(snapshot)
            self._write_json(snapshot)

            # 6. Publish via MQTT if available
            if self.mqtt_emitter:
                try:
                    self.mqtt_emitter.publish_snapshot(snapshot)
                except Exception:
                    pass

    def _run_loop(self) -> None:
        """Background thread worker loop."""
        while not self._stop_event.is_set():
            start_time = time.time()
            if not self.is_paused:
                try:
                    self.tick_step(elapsed=1.0)
                except Exception as ex:
                    print(f"Simulation tick error: {ex}")
            # Maintain 1-second interval
            delay = max(0.1, 1.0 - (time.time() - start_time))
            time.sleep(delay)

    def _compute_snapshot(self) -> Dict[str, Any]:
        """Calculates global and per-server metrics for the current instant."""
        servers = self.sdn_controller.get_server_list()
        online_servers = [s for s in servers if s.is_online]
        overloaded = [s for s in online_servers if s.status == "Overloaded"]

        total_active_workloads = sum(s.active_workload_count for s in servers)
        total_completed_workloads = sum(s.completed_workloads_count for s in servers)
        queued_count = len(self.sdn_controller.workload_queue)

        avg_cpu = sum(s.cpu_utilization for s in online_servers) / len(online_servers) if online_servers else 0.0
        avg_ram = sum(s.ram_utilization for s in online_servers) / len(online_servers) if online_servers else 0.0
        avg_net = sum(s.net_utilization for s in online_servers) / len(online_servers) if online_servers else 0.0

        total_power_w = sum(s.current_power_w for s in online_servers)
        total_energy_kwh = sum(s.total_energy_kwh for s in servers)
        energy_cost = total_energy_kwh * TARIFF_PER_KWH

        energy_per_workload = (total_energy_kwh / total_active_workloads) if total_active_workloads > 0 else 0.0

        # Equivalent legacy electrical format for energy-simulator compatibility
        voltage = 230.0 + (avg_cpu * 0.05)
        current = round(total_power_w / voltage, 2) if voltage > 0 else 0.0
        power_factor = 0.95

        return {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "time_short": datetime.now().strftime("%H:%M:%S"),
            "is_running": self.is_running,
            "is_paused": self.is_paused,
            "summary": {
                "total_servers": len(servers),
                "online_servers": len(online_servers),
                "offline_servers": len(servers) - len(online_servers),
                "overloaded_servers": len(overloaded),
                "active_workloads": total_active_workloads,
                "queued_workloads": queued_count,
                "completed_workloads": total_completed_workloads,
                "avg_cpu_percent": round(avg_cpu, 1),
                "avg_ram_percent": round(avg_ram, 1),
                "avg_net_percent": round(avg_net, 1),
                "total_power_w": round(total_power_w, 1),
                "total_energy_kwh": round(total_energy_kwh, 4),
                "energy_cost_currency": round(energy_cost, 2),
                "energy_per_workload_kwh": round(energy_per_workload, 6),
                "total_migrations": self.sdn_controller.total_migrations,
                "total_failures": self.sdn_controller.total_failures
            },
            # Legacy electrical parameters for backwards compatibility
            "voltage": round(voltage, 2),
            "current": current,
            "power": round(total_power_w, 2),
            "power_factor": power_factor,
            "energy": round(total_energy_kwh, 3),
            # Detailed Server table
            "servers": [s.to_dict() for s in servers],
            # Queued workloads
            "queued_items": [w.to_dict() for w in self.sdn_controller.workload_queue],
            # Active SDN Flow Table
            "flow_table": list(self.sdn_controller.flow_table.values()),
            # Activity logs
            "activity_log": self.sdn_controller.activity_log[:30],
            # Current weights and thresholds
            "weights": self.load_balancer.weights,
            "thresholds": self.sdn_controller.thresholds
        }

    def _record_history(self, snapshot: Dict[str, Any]) -> None:
        """Stores historical metric points for continuous chart rendering."""
        summary = snapshot["summary"]
        point = {
            "time": snapshot["time_short"],
            "avg_cpu": summary["avg_cpu_percent"],
            "avg_ram": summary["avg_ram_percent"],
            "avg_net": summary["avg_net_percent"],
            "total_power": summary["total_power_w"],
            "total_energy": summary["total_energy_kwh"],
            "active_workloads": summary["active_workloads"],
            "queued_workloads": summary["queued_workloads"]
        }
        self.history.append(point)
        if len(self.history) > self.max_history_points:
            self.history.pop(0)

    def _write_json(self, snapshot: Dict[str, Any]) -> None:
        """Exports snapshot to data/latestdata.json and legacy path."""
        try:
            with open(LATEST_DATA_FILE, "w", encoding="utf-8") as f:
                json.dump(snapshot, f, indent=2)
        except Exception as e:
            print(f"Error saving to {LATEST_DATA_FILE}: {e}")

        try:
            # Also write legacy format to energy-simulator/latest_data.json
            legacy_dict = {
                "timestamp": snapshot["timestamp"],
                "voltage": snapshot["voltage"],
                "current": snapshot["current"],
                "power": snapshot["power"],
                "power_factor": snapshot["power_factor"],
                "energy": snapshot["energy"]
            }
            with open(LEGACY_DATA_FILE, "w", encoding="utf-8") as f:
                json.dump(legacy_dict, f, indent=4)
        except Exception:
            pass

    def _export_snapshot(self) -> None:
        snapshot = self._compute_snapshot()
        self._record_history(snapshot)
        self._write_json(snapshot)

    def get_snapshot(self) -> Dict[str, Any]:
        """Thread-safe acquisition of latest snapshot."""
        with self._lock:
            snap = self._compute_snapshot()
            snap["history"] = list(self.history)
            return snap


# Singleton global instance
_simulation_instance: Optional[CloudSimulationEngine] = None
_instance_lock = threading.Lock()


def get_simulation_engine() -> CloudSimulationEngine:
    """Retrieve or initialize the global shared simulation engine."""
    global _simulation_instance
    with _instance_lock:
        if _simulation_instance is None:
            _simulation_instance = CloudSimulationEngine()
        return _simulation_instance

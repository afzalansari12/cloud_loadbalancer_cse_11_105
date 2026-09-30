"""
SDN Controller simulation module.
Maintains logical SDN network topology, OpenFlow-inspired flow tables,
centralized telemetry aggregation, threshold-driven overload mitigation,
and dynamic workload migration across simulated cloud servers.
"""

from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from collections import deque

from simulator.server_simulator import VirtualServer
from simulator.workload_generator import Workload
from controller.load_balancer import DynamicLoadBalancer


class SDNController:
    """
    Simulated Software-Defined Networking (SDN) Control Plane.
    Separates the control logic from data-plane virtual compute servers.
    """

    def __init__(
        self,
        servers: List[VirtualServer],
        load_balancer: Optional[DynamicLoadBalancer] = None,
        thresholds: Optional[Dict[str, float]] = None
    ):
        self.servers: Dict[str, VirtualServer] = {s.server_id: s for s in servers}
        self.load_balancer = load_balancer or DynamicLoadBalancer()
        self.thresholds = thresholds or {
            "cpu_warning": 70.0,
            "cpu_overload": 85.0,
            "ram_warning": 70.0,
            "ram_overload": 85.0,
            "net_warning": 75.0,
            "net_overload": 90.0
        }

        # SDN OpenFlow Table: (match: workload_id -> action: forward to server port)
        self.flow_table: Dict[str, Dict[str, Any]] = {}

        # Waiting Queue for admission-controlled requests
        self.workload_queue: deque[Workload] = deque()

        # Activity / Telemetry Event Log
        self.activity_log: List[Dict[str, Any]] = []
        self.max_log_entries = 100

        # Migration tracking
        self.total_migrations = 0
        self.total_failures = 0

        self.log_event(
            level="SUCCESS",
            message="SDN Controller initialized with "
                    f"{len(self.servers)} cloud server nodes."
        )

    def log_event(self, level: str, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        """Records an event in the real-time activity log."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        entry = {
            "timestamp": timestamp,
            "level": level.upper(),  # INFO | SUCCESS | WARNING | DANGER
            "message": message,
            "details": details or {}
        }
        self.activity_log.insert(0, entry)
        if len(self.activity_log) > self.max_log_entries:
            self.activity_log.pop()

    def get_server_list(self) -> List[VirtualServer]:
        return list(self.servers.values())

    def add_server(self, server: VirtualServer) -> None:
        """Dynamically add a new server node to the SDN topology."""
        self.servers[server.server_id] = server
        self.log_event("INFO", f"New server node [{server.server_id}: {server.name}] attached to SDN plane.")
        # Process any waiting queue
        self.process_queue()

    def remove_server(self, server_id: str) -> Optional[VirtualServer]:
        """Gracefully drain and remove a server from SDN control."""
        server = self.servers.pop(server_id, None)
        if server:
            evicted = server.fail()
            for w in evicted:
                w.status = "queued"
                self.workload_queue.append(w)
            self.log_event("WARNING", f"Server [{server_id}] detached from SDN. Drained {len(evicted)} workloads to queue.")
            self.process_queue()
        return server

    def route_workload(self, workload: Workload) -> Tuple[bool, Optional[str]]:
        """
        Core SDN Load-Balancing Pipeline:
        Workload Request -> SDN Controller -> Dynamic Load Balancer -> Virtual Server
        """
        servers_list = self.get_server_list()
        best_server, decision = self.load_balancer.select_best_server(workload, servers_list)

        if best_server is not None:
            # Allocate workload on the selected virtual server
            allocated = best_server.allocate(workload)
            if allocated:
                # Install SDN Flow Entry (Match Workload -> Action: Forward to Server Virtual Switch Port)
                self.flow_table[workload.workload_id] = {
                    "workload_id": workload.workload_id,
                    "target_server": best_server.server_id,
                    "target_name": best_server.name,
                    "load_score": decision.get("target_load_score", 0.0),
                    "created_at": datetime.now().strftime("%H:%M:%S"),
                    "status": "ACTIVE"
                }
                self.log_event(
                    "SUCCESS",
                    f"Workload {workload.workload_id} ({workload.category}) assigned -> {best_server.server_id} "
                    f"[Score: {decision.get('target_load_score'):.3f}]"
                )
                return True, best_server.server_id

        # Admission check failed (all servers at full capacity or offline)
        workload.status = "queued"
        self.workload_queue.append(workload)
        self.log_event(
            "WARNING",
            f"Insufficient cloud capacity: Workload {workload.workload_id} placed into waiting queue "
            f"(Queue depth: {len(self.workload_queue)})"
        )
        return False, None

    def process_queue(self) -> int:
        """Attempts to dispatch queued workloads if server resources have freed up."""
        if not self.workload_queue:
            return 0

        dispatched_count = 0
        unallocated: List[Workload] = []

        while self.workload_queue:
            workload = self.workload_queue.popleft()
            servers_list = self.get_server_list()
            best_server, decision = self.load_balancer.select_best_server(workload, servers_list)

            if best_server and best_server.allocate(workload):
                self.flow_table[workload.workload_id] = {
                    "workload_id": workload.workload_id,
                    "target_server": best_server.server_id,
                    "target_name": best_server.name,
                    "load_score": decision.get("target_load_score", 0.0),
                    "created_at": datetime.now().strftime("%H:%M:%S"),
                    "status": "ACTIVE"
                }
                self.log_event(
                    "SUCCESS",
                    f"Queued Workload {workload.workload_id} allocated -> {best_server.server_id}"
                )
                dispatched_count += 1
            else:
                unallocated.append(workload)

        # Restore unallocated back to queue
        for w in unallocated:
            self.workload_queue.append(w)

        return dispatched_count

    def detect_and_handle_overloads(self) -> List[Dict[str, Any]]:
        """
        Autonomous SDN Overload Detection & Dynamic Workload Migration.
        Scans all servers: if any server exceeds overload thresholds (>85% CPU or RAM),
        identifies an optimal target server and live-migrates a workload to shed load.
        """
        migrations: List[Dict[str, Any]] = []
        cpu_over = self.thresholds.get("cpu_overload", 85.0)
        ram_over = self.thresholds.get("ram_overload", 85.0)

        for src_id, src_server in self.servers.items():
            if not src_server.is_online:
                continue

            if src_server.cpu_utilization >= cpu_over or src_server.ram_utilization >= ram_over:
                self.log_event(
                    "DANGER",
                    f"Overload detected on {src_id}! CPU: {src_server.cpu_utilization}% "
                    f"| RAM: {src_server.ram_utilization}%. Initiating migration..."
                )

                # Find candidate workload to migrate
                active_workloads = list(src_server.active_workloads.values())
                if not active_workloads:
                    continue

                # Sort by remaining time descending (migrate longest running jobs first)
                active_workloads.sort(key=lambda w: w.remaining_time, reverse=True)

                candidate_migrated = False
                for w in active_workloads:
                    # Search for another server with available capacity
                    healthy_servers = [
                        s for s in self.servers.values()
                        if s.server_id != src_id and s.is_online and s.status in ("Healthy", "Warning") and s.has_capacity(w)
                    ]

                    if not healthy_servers:
                        continue

                    # Select best target using dynamic load balancer
                    target_server, decision = self.load_balancer.select_best_server(w, healthy_servers)
                    if target_server:
                        # Perform live migration:
                        # 1. Deallocate from source
                        src_server.deallocate(w.workload_id)
                        # 2. Allocate on target
                        target_server.allocate(w)
                        # 3. Update flow rule in SDN table
                        w.migration_count += 1
                        w.status = "running"
                        self.flow_table[w.workload_id] = {
                            "workload_id": w.workload_id,
                            "target_server": target_server.server_id,
                            "target_name": target_server.name,
                            "load_score": decision.get("target_load_score", 0.0),
                            "created_at": datetime.now().strftime("%H:%M:%S"),
                            "status": "MIGRATED"
                        }
                        self.total_migrations += 1

                        migration_record = {
                            "workload_id": w.workload_id,
                            "source_server": src_id,
                            "target_server": target_server.server_id,
                            "cpu_shed": w.cpu_req,
                            "ram_shed": w.ram_req,
                            "timestamp": datetime.now().strftime("%H:%M:%S")
                        }
                        migrations.append(migration_record)

                        self.log_event(
                            "INFO",
                            f"SDN Migration: Workload {w.workload_id} rerouted "
                            f"{src_id} -> {target_server.server_id} [Mitigated overload]"
                        )
                        candidate_migrated = True
                        break

                if not candidate_migrated:
                    self.log_event(
                        "WARNING",
                        f"Migration deferred for {src_id}: No healthy target server has sufficient headroom."
                    )

        return migrations

    def simulate_server_failure(self, server_id: str) -> bool:
        """Simulate hardware failure: server drops offline, workloads rescheduled."""
        server = self.servers.get(server_id)
        if not server or not server.is_online:
            return False

        evicted_workloads = server.fail()
        self.total_failures += 1

        self.log_event(
            "DANGER",
            f"CRITICAL FAILURE: {server_id} went OFFLINE! Evicting {len(evicted_workloads)} workloads."
        )

        # Redistribute eligible workloads to healthy servers or enqueue
        for w in evicted_workloads:
            w.status = "queued"
            self.workload_queue.append(w)

        # Attempt immediate reroute
        self.process_queue()
        return True

    def simulate_server_recovery(self, server_id: str) -> bool:
        """Simulate server recovery: node returns online, accepts new traffic."""
        server = self.servers.get(server_id)
        if not server or server.is_online:
            return False

        server.recover()
        self.log_event("SUCCESS", f"RECOVERY: {server_id} restored to Healthy state.")
        # Re-dispatch queued items
        self.process_queue()
        return True

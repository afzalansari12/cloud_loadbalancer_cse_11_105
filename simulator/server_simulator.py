"""
Virtual Cloud Server Simulator.
Models realistic multi-core server nodes with dynamic resource allocation,
energy dissipation modeling, and lifecycle status management.
"""

from typing import Dict, Any, List, Optional
import time

class VirtualServer:
    """Represents a virtualized host / VM in a cloud datacenter."""

    def __init__(
        self,
        server_id: str,
        name: str,
        cpu_capacity: int,
        ram_capacity: float,
        net_capacity: float,
        idle_power: float = 50.0,
        max_dynamic_power: float = 120.0
    ):
        self.server_id = server_id
        self.name = name
        self.cpu_capacity = cpu_capacity        # Cores (e.g. 8, 16)
        self.ram_capacity = ram_capacity        # GB (e.g. 16.0, 32.0)
        self.net_capacity = net_capacity        # Mbps (e.g. 1000.0)
        self.idle_power = idle_power            # Watts at 0% load
        self.max_dynamic_power = max_dynamic_power # Watts at 100% CPU load

        # Dynamic runtime metrics
        self.allocated_cpu = 0.0                # Cores in use
        self.allocated_ram = 0.0                # GB in use
        self.allocated_net = 0.0                # Mbps in use
        self.active_workloads: Dict[str, Any] = {}
        self.completed_workloads_count = 0

        # Energy metrics
        self.current_power_w = idle_power       # Instantaneous Watts
        self.total_energy_kwh = 0.0             # Cumulative kWh consumed

        # Health & State
        self.is_online = True
        self.status = "Healthy"                 # Healthy | Warning | Overloaded | Offline

    @property
    def cpu_utilization(self) -> float:
        """CPU utilization percentage (0 - 100%)."""
        if not self.is_online or self.cpu_capacity <= 0:
            return 0.0
        return min(100.0, round((self.allocated_cpu / self.cpu_capacity) * 100.0, 1))

    @property
    def ram_utilization(self) -> float:
        """RAM utilization percentage (0 - 100%)."""
        if not self.is_online or self.ram_capacity <= 0:
            return 0.0
        return min(100.0, round((self.allocated_ram / self.ram_capacity) * 100.0, 1))

    @property
    def net_utilization(self) -> float:
        """Network utilization percentage (0 - 100%)."""
        if not self.is_online or self.net_capacity <= 0:
            return 0.0
        return min(100.0, round((self.allocated_net / self.net_capacity) * 100.0, 1))

    @property
    def active_workload_count(self) -> int:
        return len(self.active_workloads)

    def has_capacity(self, workload: Any) -> bool:
        """Checks if server has sufficient available headroom for incoming workload."""
        if not self.is_online:
            return False
        cpu_ok = (self.allocated_cpu + workload.cpu_req) <= self.cpu_capacity
        ram_ok = (self.allocated_ram + workload.ram_req) <= self.ram_capacity
        net_ok = (self.allocated_net + workload.net_req) <= self.net_capacity
        return cpu_ok and ram_ok and net_ok

    def allocate(self, workload: Any) -> bool:
        """Allocates a workload to this server."""
        if not self.is_online or not self.has_capacity(workload):
            return False

        workload.assigned_server = self.server_id
        workload.status = "running"
        self.active_workloads[workload.workload_id] = workload

        self.allocated_cpu = round(self.allocated_cpu + workload.cpu_req, 2)
        self.allocated_ram = round(self.allocated_ram + workload.ram_req, 2)
        self.allocated_net = round(self.allocated_net + workload.net_req, 2)
        self._recalculate_power()
        return True

    def deallocate(self, workload_id: str) -> Optional[Any]:
        """Removes a workload and frees its allocated resources."""
        workload = self.active_workloads.pop(workload_id, None)
        if workload:
            self.allocated_cpu = max(0.0, round(self.allocated_cpu - workload.cpu_req, 2))
            self.allocated_ram = max(0.0, round(self.allocated_ram - workload.ram_req, 2))
            self.allocated_net = max(0.0, round(self.allocated_net - workload.net_req, 2))
            self._recalculate_power()
        return workload

    def tick(self, elapsed_seconds: float = 1.0, thresholds: Optional[Dict[str, float]] = None) -> List[Any]:
        """
        Simulate progress of time:
        - Decrements remaining runtime on active workloads.
        - Deallocates and returns workloads that have completed.
        - Integrates energy consumption.
        - Updates health status based on thresholds.
        """
        if not self.is_online:
            self.status = "Offline"
            self.current_power_w = 0.0
            return []

        completed: List[Any] = []
        for wid, workload in list(self.active_workloads.items()):
            workload.remaining_time -= elapsed_seconds
            if workload.remaining_time <= 0:
                workload.status = "completed"
                self.deallocate(wid)
                self.completed_workloads_count += 1
                completed.append(workload)

        # Recalculate power and energy
        self._recalculate_power()
        # Watt-seconds to kWh: (Watts * seconds) / (3600 * 1000)
        self.total_energy_kwh += (self.current_power_w * elapsed_seconds) / 3600000.0

        # Update status
        self._update_status(thresholds)
        return completed

    def _recalculate_power(self) -> None:
        """Models server power draw based on CPU and network utilization."""
        if not self.is_online:
            self.current_power_w = 0.0
            return
        cpu_fraction = self.cpu_utilization / 100.0
        net_fraction = self.net_utilization / 100.0
        # Dynamic power proportional to CPU load + modest network interface power
        power = self.idle_power + (cpu_fraction * self.max_dynamic_power) + (net_fraction * 15.0)
        self.current_power_w = round(power, 2)

    def _update_status(self, thresholds: Optional[Dict[str, float]] = None) -> None:
        if not self.is_online:
            self.status = "Offline"
            return

        cpu_warn = thresholds.get("cpu_warning", 70.0) if thresholds else 70.0
        cpu_over = thresholds.get("cpu_overload", 85.0) if thresholds else 85.0
        ram_warn = thresholds.get("ram_warning", 70.0) if thresholds else 70.0
        ram_over = thresholds.get("ram_overload", 85.0) if thresholds else 85.0

        if self.cpu_utilization >= cpu_over or self.ram_utilization >= ram_over:
            self.status = "Overloaded"
        elif self.cpu_utilization >= cpu_warn or self.ram_utilization >= ram_warn:
            self.status = "Warning"
        else:
            self.status = "Healthy"

    def fail(self) -> List[Any]:
        """Simulate hardware/network crash: takes server offline and evicts workloads."""
        self.is_online = False
        self.status = "Offline"
        evicted = list(self.active_workloads.values())
        self.active_workloads.clear()
        self.allocated_cpu = 0.0
        self.allocated_ram = 0.0
        self.allocated_net = 0.0
        self.current_power_w = 0.0
        return evicted

    def recover(self) -> None:
        """Restores server to active online state."""
        self.is_online = True
        self.status = "Healthy"
        self._recalculate_power()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.server_id,
            "name": self.name,
            "is_online": self.is_online,
            "status": self.status,
            "cpu_capacity": self.cpu_capacity,
            "allocated_cpu": round(self.allocated_cpu, 2),
            "cpu_utilization": self.cpu_utilization,
            "ram_capacity": self.ram_capacity,
            "allocated_ram": round(self.allocated_ram, 2),
            "ram_utilization": self.ram_utilization,
            "net_capacity": self.net_capacity,
            "allocated_net": round(self.allocated_net, 2),
            "net_utilization": self.net_utilization,
            "active_workloads": len(self.active_workloads),
            "completed_workloads": self.completed_workloads_count,
            "current_power_w": self.current_power_w,
            "total_energy_kwh": round(self.total_energy_kwh, 4)
        }

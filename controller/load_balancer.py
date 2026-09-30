"""
Dynamic Weighted Load Balancer for SDN Cloud Architecture.
Computes multi-dimensional normalized load scores across CPU, RAM, Network,
Active Workloads, and Power draw to route incoming workloads optimally.
"""

from typing import Dict, List, Optional, Tuple, Any
from simulator.server_simulator import VirtualServer
from simulator.workload_generator import Workload


class DynamicLoadBalancer:
    """Computes server load scores and determines optimal target placement."""

    def __init__(self, weights: Optional[Dict[str, float]] = None):
        self.weights = weights or {
            "cpu": 0.40,
            "ram": 0.25,
            "net": 0.20,
            "count": 0.10,
            "energy": 0.05
        }

    def update_weights(self, new_weights: Dict[str, float]) -> None:
        """Dynamically update load balancing weights."""
        total = sum(new_weights.values())
        if total > 0:
            self.weights = {k: round(v / total, 3) for k, v in new_weights.items()}

    def calculate_server_score(
        self,
        server: VirtualServer,
        max_workloads: int = 1,
        max_power: float = 1.0
    ) -> float:
        """
        Calculates a normalized scalar load score (0.0 to 1.0).
        Lower is better (less loaded).
        """
        if not server.is_online:
            return 999.0  # Offline servers should never be chosen

        # 1. Normalized CPU utilization [0.0 - 1.0]
        u_cpu = server.cpu_utilization / 100.0

        # 2. Normalized RAM utilization [0.0 - 1.0]
        u_ram = server.ram_utilization / 100.0

        # 3. Normalized Network utilization [0.0 - 1.0]
        u_net = server.net_utilization / 100.0

        # 4. Normalized Active Workload count [0.0 - 1.0]
        u_count = server.active_workload_count / max(1.0, float(max_workloads))

        # 5. Normalized Energy consumption [0.0 - 1.0]
        u_energy = server.current_power_w / max(1.0, max_power)

        w = self.weights
        score = (
            w.get("cpu", 0.40) * u_cpu +
            w.get("ram", 0.25) * u_ram +
            w.get("net", 0.20) * u_net +
            w.get("count", 0.10) * u_count +
            w.get("energy", 0.05) * u_energy
        )
        return round(score, 4)

    def evaluate_servers(
        self,
        servers: List[VirtualServer]
    ) -> Dict[str, Dict[str, Any]]:
        """Calculates normalized load scores and sub-metrics for all servers."""
        active_counts = [s.active_workload_count for s in servers if s.is_online]
        max_workloads = max(active_counts) if active_counts else 1
        powers = [s.current_power_w for s in servers if s.is_online]
        max_power = max(powers) if powers else 1.0

        evaluations = {}
        for s in servers:
            score = self.calculate_server_score(s, max_workloads, max_power)
            evaluations[s.server_id] = {
                "score": score,
                "is_online": s.is_online,
                "status": s.status,
                "cpu_util": s.cpu_utilization,
                "ram_util": s.ram_utilization,
                "net_util": s.net_utilization,
                "workload_count": s.active_workload_count,
                "power_w": s.current_power_w
            }
        return evaluations

    def select_best_server(
        self,
        workload: Workload,
        servers: List[VirtualServer]
    ) -> Tuple[Optional[VirtualServer], Dict[str, Any]]:
        """
        Selects the server with the lowest suitable load score that also possesses
        sufficient capacity headroom for this specific workload.
        Returns:
            (selected_server, decision_details)
        """
        evaluations = self.evaluate_servers(servers)

        candidate_servers = []
        for s in servers:
            if s.is_online and s.has_capacity(workload):
                candidate_servers.append((s, evaluations[s.server_id]["score"]))

        if not candidate_servers:
            return None, {
                "workload_id": workload.workload_id,
                "decision": "QUEUED_NO_CAPACITY",
                "reason": "All servers are full, overloaded, or offline",
                "evaluations": evaluations
            }

        # Sort candidates ascending by load score (lowest load first)
        candidate_servers.sort(key=lambda item: item[1])
        best_server, best_score = candidate_servers[0]

        decision_info = {
            "workload_id": workload.workload_id,
            "decision": "ASSIGNED",
            "target_server": best_server.server_id,
            "target_server_name": best_server.name,
            "target_load_score": best_score,
            "evaluations": evaluations
        }

        return best_server, decision_info

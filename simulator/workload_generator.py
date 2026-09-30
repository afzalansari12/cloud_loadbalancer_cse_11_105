"""
Workload generator for cloud tasks.
Simulates realistic diverse cloud workloads with variable resource profiles.
"""

import time
import random
from datetime import datetime
from typing import Dict, Any, Optional

WORKLOAD_PROFILES = [
    {
        "category": "Web Request",
        "cpu_range": (0.4, 1.2),
        "ram_range": (0.5, 2.0),
        "net_range": (30.0, 120.0),
        "duration_range": (6, 14),
        "weight": 0.40
    },
    {
        "category": "Batch Processing",
        "cpu_range": (1.5, 3.5),
        "ram_range": (3.0, 6.0),
        "net_range": (10.0, 50.0),
        "duration_range": (12, 28),
        "weight": 0.25
    },
    {
        "category": "Media Streaming",
        "cpu_range": (0.8, 2.0),
        "ram_range": (1.5, 4.0),
        "net_range": (150.0, 350.0),
        "duration_range": (10, 22),
        "weight": 0.20
    },
    {
        "category": "Database Query",
        "cpu_range": (1.0, 2.5),
        "ram_range": (2.0, 5.0),
        "net_range": (40.0, 100.0),
        "duration_range": (5, 12),
        "weight": 0.15
    }
]


class Workload:
    """Represents an individual cloud computing workload request."""

    def __init__(
        self,
        workload_id: str,
        category: str,
        cpu_req: float,
        ram_req: float,
        net_req: float,
        duration: int,
        timestamp: Optional[str] = None
    ):
        self.workload_id = workload_id
        self.category = category
        self.cpu_req = round(cpu_req, 2)       # in cores
        self.ram_req = round(ram_req, 2)       # in GB
        self.net_req = round(net_req, 2)       # in Mbps
        self.duration = duration               # in seconds
        self.remaining_time = duration         # countdown
        self.timestamp = timestamp or datetime.now().strftime("%H:%M:%S")
        self.assigned_server: Optional[str] = None
        self.status = "queued"                 # queued | running | completed | migrated
        self.migration_count = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "workload_id": self.workload_id,
            "category": self.category,
            "cpu_req": self.cpu_req,
            "ram_req": self.ram_req,
            "net_req": self.net_req,
            "duration": self.duration,
            "remaining_time": self.remaining_time,
            "timestamp": self.timestamp,
            "assigned_server": self.assigned_server,
            "status": self.status,
            "migration_count": self.migration_count
        }


class WorkloadGenerator:
    """Generates continuous or burst synthetic cloud workloads."""

    def __init__(self, start_id: int = 1001):
        self._counter = start_id

    def generate(self, custom_profile: Optional[Dict[str, Any]] = None) -> Workload:
        """Create a single new workload based on weighted profiles or custom specs."""
        self._counter += 1
        workload_id = f"W{self._counter}"

        if custom_profile:
            return Workload(
                workload_id=workload_id,
                category=custom_profile.get("category", "Custom Job"),
                cpu_req=custom_profile.get("cpu_req", 1.0),
                ram_req=custom_profile.get("ram_req", 2.0),
                net_req=custom_profile.get("net_req", 50.0),
                duration=int(custom_profile.get("duration", 10))
            )

        # Select a random profile based on relative weights
        weights = [p["weight"] for p in WORKLOAD_PROFILES]
        profile = random.choices(WORKLOAD_PROFILES, weights=weights, k=1)[0]

        cpu = random.uniform(*profile["cpu_range"])
        ram = random.uniform(*profile["ram_range"])
        net = random.uniform(*profile["net_range"])
        duration = random.randint(*profile["duration_range"])

        return Workload(
            workload_id=workload_id,
            category=profile["category"],
            cpu_req=cpu,
            ram_req=ram,
            net_req=net,
            duration=duration
        )

    def generate_burst(self, count: int = 5) -> list[Workload]:
        """Generate a batch of workloads simulating a sudden traffic surge."""
        return [self.generate() for _ in range(count)]

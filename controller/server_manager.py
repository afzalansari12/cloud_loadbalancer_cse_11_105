"""
Server manager module for dynamic capacity expansion and lifecycle management.
"""

from typing import List, Dict, Any, Optional
from simulator.server_simulator import VirtualServer
from controller.sdn_controller import SDNController


class ServerManager:
    """Manages cloud virtual machine fleet lifecycle and dynamic scaling."""

    def __init__(self, sdn_controller: SDNController):
        self.controller = sdn_controller
        self._server_counter = len(sdn_controller.servers)

    def add_custom_server(
        self,
        name: Optional[str] = None,
        cpu_cores: int = 8,
        ram_gb: float = 16.0,
        net_mbps: float = 1000.0,
        idle_power: float = 50.0,
        dynamic_power: float = 120.0
    ) -> VirtualServer:
        """Scales out the infrastructure by spinning up a new virtual server."""
        self._server_counter += 1
        server_id = f"Server-{self._server_counter}"
        server_name = name or f"Dynamic-Worker-{self._server_counter:02d}"

        new_server = VirtualServer(
            server_id=server_id,
            name=server_name,
            cpu_capacity=cpu_cores,
            ram_capacity=ram_gb,
            net_capacity=net_mbps,
            idle_power=idle_power,
            max_dynamic_power=dynamic_power
        )

        self.controller.add_server(new_server)
        return new_server

    def remove_server(self, server_id: str) -> bool:
        """Scales in the infrastructure by decommissioning a server."""
        # Prevent removing all servers
        if len(self.controller.servers) <= 1:
            self.controller.log_event("WARNING", "Cannot remove last remaining server in the cloud pool.")
            return False

        server = self.controller.remove_server(server_id)
        return server is not None

    def toggle_server_failure(self, server_id: str) -> bool:
        """Toggles a server between failed (offline) and recovered (healthy)."""
        server = self.controller.servers.get(server_id)
        if not server:
            return False

        if server.is_online:
            return self.controller.simulate_server_failure(server_id)
        else:
            return self.controller.simulate_server_recovery(server_id)

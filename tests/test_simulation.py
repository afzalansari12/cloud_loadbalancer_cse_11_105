"""
Automated unit and integration test suite for SDN Dynamic Cloud Load Balancer.
Tests server simulation, workload admission, dynamic load balancing scores,
SDN flow table installation, overload detection, live migration, and failure recovery.
"""

import sys
import unittest
import time
import json
from pathlib import Path

# Add root directory to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from simulator.workload_generator import WorkloadGenerator, Workload
from simulator.server_simulator import VirtualServer
from controller.load_balancer import DynamicLoadBalancer
from controller.sdn_controller import SDNController
from controller.server_manager import ServerManager
from simulator.simulation import CloudSimulationEngine


class TestSDNCloudLoadBalancer(unittest.TestCase):

    def setUp(self):
        # Create 3 isolated test servers
        self.server1 = VirtualServer(
            server_id="S1",
            name="Node-1",
            cpu_capacity=8,
            ram_capacity=16.0,
            net_capacity=1000.0,
            idle_power=50.0,
            max_dynamic_power=100.0
        )
        self.server2 = VirtualServer(
            server_id="S2",
            name="Node-2",
            cpu_capacity=8,
            ram_capacity=16.0,
            net_capacity=1000.0,
            idle_power=50.0,
            max_dynamic_power=100.0
        )
        self.server3 = VirtualServer(
            server_id="S3",
            name="Node-3",
            cpu_capacity=16,
            ram_capacity=32.0,
            net_capacity=2000.0,
            idle_power=80.0,
            max_dynamic_power=200.0
        )
        self.servers = [self.server1, self.server2, self.server3]
        self.load_balancer = DynamicLoadBalancer()
        self.controller = SDNController(
            servers=self.servers,
            load_balancer=self.load_balancer
        )

    def test_virtual_server_allocation_and_power(self):
        w = Workload("W1", "Web", cpu_req=4.0, ram_req=8.0, net_req=200.0, duration=10)
        self.assertTrue(self.server1.has_capacity(w))
        self.assertTrue(self.server1.allocate(w))

        # Check utilization
        self.assertEqual(self.server1.cpu_utilization, 50.0)  # 4/8 cores = 50%
        self.assertEqual(self.server1.ram_utilization, 50.0)  # 8/16 GB = 50%
        self.assertEqual(self.server1.active_workload_count, 1)

        # Check dynamic power calculation
        # power = idle (50) + cpu_frac (0.5 * 100 = 50) + net_frac (0.2 * 15 = 3) = 103.0
        self.assertGreater(self.server1.current_power_w, 50.0)

    def test_dynamic_load_balancer_selection(self):
        # Preload server 1 with a heavy workload
        w_heavy = Workload("W_pre", "Batch", cpu_req=6.0, ram_req=12.0, net_req=500.0, duration=20)
        self.server1.allocate(w_heavy)

        # Now test routing for a new workload
        w_new = Workload("W_new", "Web", cpu_req=2.0, ram_req=4.0, net_req=100.0, duration=10)
        best_server, decision = self.load_balancer.select_best_server(w_new, self.servers)

        # S2 and S3 are completely empty; S1 is 75% loaded.
        # Dynamic LB must choose either S2 or S3, never heavily loaded S1!
        self.assertIn(best_server.server_id, ["S2", "S3"])
        self.assertNotEqual(best_server.server_id, "S1")

    def test_sdn_controller_flow_table_installation(self):
        w = Workload("W101", "Web", cpu_req=1.0, ram_req=2.0, net_req=50.0, duration=10)
        routed, target_id = self.controller.route_workload(w)

        self.assertTrue(routed)
        self.assertIsNotNone(target_id)
        # Verify OpenFlow rule was installed
        self.assertIn("W101", self.controller.flow_table)
        flow_rule = self.controller.flow_table["W101"]
        self.assertEqual(flow_rule["target_server"], target_id)
        self.assertEqual(flow_rule["status"], "ACTIVE")

    def test_admission_control_and_queueing(self):
        # Create a tiny server
        tiny_server = VirtualServer("T1", "Tiny", cpu_capacity=2, ram_capacity=2.0, net_capacity=100.0)
        ctl = SDNController(servers=[tiny_server])

        # Fill it up
        w1 = Workload("W_fit", "Test", cpu_req=2.0, ram_req=2.0, net_req=100.0, duration=5)
        routed1, _ = ctl.route_workload(w1)
        self.assertTrue(routed1)

        # Incoming request that exceeds available capacity
        w2 = Workload("W_excess", "Test", cpu_req=1.0, ram_req=1.0, net_req=50.0, duration=5)
        routed2, _ = ctl.route_workload(w2)
        self.assertFalse(routed2)
        self.assertEqual(len(ctl.workload_queue), 1)
        self.assertEqual(w2.status, "queued")

    def test_server_failure_and_reschedule(self):
        w = Workload("W_fail", "Web", cpu_req=2.0, ram_req=4.0, net_req=50.0, duration=15)
        self.server1.allocate(w)
        self.controller.flow_table[w.workload_id] = {
            "workload_id": w.workload_id,
            "target_server": "S1",
            "status": "ACTIVE"
        }

        # Simulate failure of S1
        success = self.controller.simulate_server_failure("S1")
        self.assertTrue(success)
        self.assertFalse(self.server1.is_online)
        self.assertEqual(self.server1.status, "Offline")

        # Workload should have been rescheduled to a healthy server (S2 or S3)
        self.assertEqual(w.status, "running")
        self.assertIn(w.assigned_server, ["S2", "S3"])

    def test_overload_detection_and_live_migration(self):
        # Drive Server 1 into Overloaded status (>85% CPU)
        w_base = Workload("W_long1", "Compute", cpu_req=7.2, ram_req=14.0, net_req=300.0, duration=30)
        self.server1.allocate(w_base)
        self.server1.tick(0.1, thresholds=self.controller.thresholds)
        self.assertEqual(self.server1.status, "Overloaded")

        # Trigger autonomous overload mitigation
        migrations = self.controller.detect_and_handle_overloads()
        self.assertGreaterEqual(len(migrations), 1)

        # Workload should have migrated to S2 or S3
        self.assertEqual(migrations[0]["source_server"], "S1")
        self.assertIn(migrations[0]["target_server"], ["S2", "S3"])
        self.assertGreaterEqual(self.controller.total_migrations, 1)

    def test_simulation_engine_tick_and_persistence(self):
        engine = CloudSimulationEngine()
        # Generate some synthetic traffic
        engine.generate_burst_now(count=3)
        # Advance simulation
        engine.tick_step(elapsed=1.0)

        snap = engine.get_snapshot()
        self.assertGreater(snap["summary"]["total_servers"], 0)
        self.assertGreater(snap["summary"]["total_power_w"], 0.0)

        # Verify JSON file output
        data_file = ROOT_DIR / "data" / "latestdata.json"
        self.assertTrue(data_file.exists())
        with open(data_file, "r") as f:
            saved = json.load(f)
        self.assertIn("summary", saved)
        self.assertIn("servers", saved)


if __name__ == "__main__":
    unittest.main()

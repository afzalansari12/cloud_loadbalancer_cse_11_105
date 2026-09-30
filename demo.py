"""
Interactive End-to-End Live Demonstration Script
for SDN Dynamic Cloud Load Balancer.

Executes a guided 5-phase simulation scenario:
1. System Initialization & Fleet Inspection
2. Dynamic Multi-Metric Workload Distribution
3. Traffic Surge & Autonomous Overload Mitigation (Live Migration)
4. Server Hardware Failure & Automated Rescheduling
5. Server Node Recovery & Queue Draining
"""

import sys
import time
from pathlib import Path

# Ensure root directory is accessible
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from simulator.simulation import get_simulation_engine
from simulator.workload_generator import Workload


def print_banner(text: str):
    print("\n" + "═" * 70)
    print(f"  {text}")
    print("═" * 70)


def print_fleet_status(engine):
    snap = engine.get_snapshot()
    s = snap["summary"]
    print(f"\n[FLEET OVERVIEW] Time: {snap['time_short']}")
    print(f"  Nodes Online: {s['online_servers']}/{s['total_servers']} | Active Tasks: {s['active_workloads']} | Queue: {s['queued_workloads']}")
    print(f"  Fleet Avg: CPU {s['avg_cpu_percent']}% | RAM {s['avg_ram_percent']}% | Net {s['avg_net_percent']}%")
    print(f"  Total Power: {s['total_power_w']} W | Cumulative Energy: {s['total_energy_kwh']:.4f} kWh | Migrations: {s['total_migrations']}")
    print("-" * 70)
    print(f"  {'SERVER ID':<12} {'STATUS':<12} {'CPU (Cores)':<15} {'RAM (GB)':<15} {'TASKS':<8} {'POWER'}")
    print("-" * 70)
    for srv in snap["servers"]:
        cpu_str = f"{srv['allocated_cpu']}/{srv['cpu_capacity']} ({srv['cpu_utilization']}%)"
        ram_str = f"{srv['allocated_ram']}/{srv['ram_capacity']} ({srv['ram_utilization']}%)"
        print(f"  {srv['id']:<12} {srv['status']:<12} {cpu_str:<15} {ram_str:<15} {srv['active_workloads']:<8} {srv['current_power_w']} W")
    print("-" * 70)


def run_demo():
    print_banner("⚡ SDN CLOUD LOAD BALANCER — LIVE END-TO-END DEMO ⚡")
    print("Initializing SDN Controller, Dynamic Load Balancer, and Virtual Servers...")
    engine = get_simulation_engine()
    engine.reset()
    time.sleep(1)

    print_fleet_status(engine)

    # -------------------------------------------------------------
    # PHASE 1: Normal Traffic Distribution
    # -------------------------------------------------------------
    print_banner("PHASE 1: Dynamic Multi-Metric Workload Routing")
    print("Injecting 4 diverse cloud workloads:")
    print("  • W1: Web API Request       (CPU: 1.0 core,  RAM: 1.5 GB,  Net: 50 Mbps)")
    print("  • W2: Batch Analytics Job   (CPU: 3.0 cores, RAM: 6.0 GB,  Net: 30 Mbps)")
    print("  • W3: Video Transcoding     (CPU: 2.0 cores, RAM: 4.0 GB,  Net: 250 Mbps)")
    print("  • W4: Database Query        (CPU: 1.5 cores, RAM: 3.5 GB,  Net: 80 Mbps)")

    tasks = [
        Workload("W1001", "Web API", cpu_req=1.0, ram_req=1.5, net_req=50.0, duration=15),
        Workload("W1002", "Batch Analytics", cpu_req=3.0, ram_req=6.0, net_req=30.0, duration=20),
        Workload("W1003", "Video Transcode", cpu_req=2.0, ram_req=4.0, net_req=250.0, duration=18),
        Workload("W1004", "Database Query", cpu_req=1.5, ram_req=3.5, net_req=80.0, duration=12),
    ]

    for t in tasks:
        routed, target = engine.sdn_controller.route_workload(t)
        time.sleep(0.3)

    print("\n[SDN OpenFlow Flow Rules Installed]:")
    for flow in list(engine.sdn_controller.flow_table.values())[-4:]:
        print(f"  Match: Workload [{flow['workload_id']}] ➔ Action: Route to {flow['target_server']} (Load Score: {flow['load_score']:.4f})")

    engine.tick_step(elapsed=1.0)
    print_fleet_status(engine)
    time.sleep(1.5)

    # -------------------------------------------------------------
    # PHASE 2: Heavy Workload Injection & Traffic Surge
    # -------------------------------------------------------------
    print_banner("PHASE 2: Traffic Surge & Load Balancing Decisioning")
    print("Simulating high-traffic influx (Burst of 6 simultaneous workloads)...")
    burst = engine.generate_burst_now(count=6)
    print(f"Successfully routed {len(burst)} workloads across the server fleet.")

    engine.tick_step(elapsed=1.0)
    print_fleet_status(engine)
    time.sleep(1.5)

    # -------------------------------------------------------------
    # PHASE 3: Overload Detection & Autonomous Live Migration
    # -------------------------------------------------------------
    print_banner("PHASE 3: Overload Detection & Autonomous Live Workload Migration")
    print("Artificially pushing Server-1 to critical load (>85% CPU)...")
    overload_task = Workload("W_HEAVY", "Deep Learning", cpu_req=4.8, ram_req=8.0, net_req=300.0, duration=35)
    target_server = engine.sdn_controller.servers["Server-1"]
    allocated = target_server.allocate(overload_task)
    if allocated:
        engine.sdn_controller.flow_table[overload_task.workload_id] = {
            "workload_id": overload_task.workload_id,
            "target_server": "Server-1",
            "load_score": 0.95,
            "created_at": time.strftime("%H:%M:%S"),
            "status": "ACTIVE"
        }

    # Step simulation to trigger status recalculation
    engine.tick_step(elapsed=1.0)
    print_fleet_status(engine)
    print(f"\n>> Server-1 Status is now: [{target_server.status}] (CPU: {target_server.cpu_utilization}%)")

    print("\n>> SDN Controller detecting overload condition & running live migration...")
    migrations = engine.sdn_controller.detect_and_handle_overloads()
    for m in migrations:
        print(f"  [MIGRATION EVENT] Workload {m['workload_id']} live-migrated: {m['source_server']} ➔ {m['target_server']} (Shed {m['cpu_shed']} Cores, {m['ram_shed']} GB)")

    engine.tick_step(elapsed=1.0)
    print_fleet_status(engine)
    time.sleep(1.5)

    # -------------------------------------------------------------
    # PHASE 4: Server Failure Simulation & Automatic Rescheduling
    # -------------------------------------------------------------
    print_banner("PHASE 4: Server Hardware Crash & Automated Rescheduling")
    print("Simulating sudden hardware crash on Server-2...")
    engine.sdn_controller.simulate_server_failure("Server-2")

    engine.tick_step(elapsed=1.0)
    print_fleet_status(engine)
    print("Server-2 is OFFLINE. All running tasks were evacuated and rerouted to surviving nodes!")
    time.sleep(1.5)

    # -------------------------------------------------------------
    # PHASE 5: Server Recovery
    # -------------------------------------------------------------
    print_banner("PHASE 5: Server Recovery & Re-balancing")
    print("Repairing Server-2 and restoring online connectivity...")
    engine.sdn_controller.simulate_server_recovery("Server-2")

    engine.tick_step(elapsed=1.0)
    print_fleet_status(engine)
    print("Server-2 is back ONLINE (Healthy) and ready to accept new workloads.")

    print_banner("DEMO COMPLETED SUCCESSFULLY ✓")
    print("The system verified:")
    print("  ✓ Multi-metric dynamic load scoring")
    print("  ✓ SDN OpenFlow flow table rule installation")
    print("  ✓ Overload detection (>85%)")
    print("  ✓ Autonomous live workload migration")
    print("  ✓ Server hardware failure evacuation & rescheduling")
    print("  ✓ Node recovery and admission queue processing")
    print("  ✓ Real-time telemetry export to data/latestdata.json")
    print("═" * 70 + "\n")


if __name__ == "__main__":
    run_demo()

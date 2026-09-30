# Software-Defined Networking (SDN) Dynamic Cloud Load Balancer

An end-to-end, runnable Software-Defined Networking (SDN) Dynamic Cloud Load Balancer for cloud workloads. Built with Python, Streamlit, and MQTT telemetry, this project simulates virtual server nodes, continuously monitors CPU, RAM, Network, and Energy metrics, and dynamically computes routing decisions using an admission-controlled multi-metric scoring algorithm.

---

## 1. Problem Statement & Objective

Traditional hardware cloud load balancers often rely on static heuristics (e.g., Round Robin, Random, or simple least connections) that fail to account for the heterogeneous resource footprints of modern microservices (compute-heavy ML batch jobs, memory-intensive caching queries, or network-bound streaming media). 

**Objective:**
1. Decouple cloud traffic routing logic from physical servers using an **SDN Control Plane** architecture.
2. Implement a **Dynamic Weighted Load-Balancing Algorithm** that continuously scores servers using normalized CPU, RAM, Network, Workload Count, and Power Draw metrics.
3. Provide **Autonomous Overload Detection and Live Workload Migration** to preempt server crashes.
4. Integrate **Real-Time Telemetry and Predictive Energy Modeling** broadcast over MQTT (HiveMQ Cloud / local Mosquitto).
5. Deliver a **Bright, High-Contrast Modern SaaS Monitoring Dashboard** for cloud operators.

---

## 2. System Architecture

```
                       +---------------------------------------+
                       |            Cloud Workloads            |
                       | (Web, Batch, Media, Database, Custom) |
                       +-------------------+-------------------+
                                           |
                                           v
                       +---------------------------------------+
                       |            SDN Controller             |
                       |  - Global Topology & Flow Tables      |
                       |  - Overload & Threshold Detection     |
                       |  - Autonomous Workload Migration      |
                       +-------------------+-------------------+
                                           |
                                           v
                       +---------------------------------------+
                       |         Dynamic Load Balancer         |
                       |  - Multi-Metric Normalized Scoring    |
                       |  - Headroom Admission Check           |
                       |  - Prioritized Admission Queue        |
                       +-------------------+-------------------+
                                           |
                    +----------------------+----------------------+
                    |                      |                      |
                    v                      v                      v
             +--------------+       +--------------+       +--------------+
             |   Server 1   |       |   Server 2   |       |   Server 3   |
             | 8 Core/16GB  |       | 8 Core/16GB  |       | 16 Core/32GB |
             |    1 Gbps    |       |    1 Gbps    |       |    2 Gbps    |
             +-------+------+       +-------+------+       +-------+------+
                     |                      |                      |
                     +----------------------+----------------------+
                                           |
                        Telemetry (CPU, RAM, Net, Energy)
                                           |
                     +---------------------+---------------------+
                     |                                           |
                     v                                           v
             +---------------+                           +---------------+
             | MQTT Telemetry|                           |  latestdata   |
             | HiveMQ/Local  |                           |    .json      |
             +-------+-------+                           +-------+-------+
                     |                                           |
                     +---------------------+---------------------+
                                           |
                                           v
                         +-----------------------------------+
                         |   Streamlit SaaS Cloud Dashboard  |
                         |     & Embedded REST API Engine    |
                         +-----------------------------------+
```

> **Note on SDN Emulation:** This project implements an SDN controller simulation with clean OpenFlow flow-rule abstractions (`match: workload_id -> action: forward_to_port(server)`). It does not require physical OpenFlow switches or a running Mininet VM to execute, but provides clean interfaces for future Mininet/Ryu integration.

---

## 3. Dynamic Load-Balancing Algorithm

The Load Balancer does not distribute traffic randomly. For each incoming workload, the controller assesses candidate servers:

### A. Normalized Load Score Formula
$$\text{Score} = w_{\text{cpu}} \cdot U_{\text{cpu}} + w_{\text{ram}} \cdot U_{\text{ram}} + w_{\text{net}} \cdot U_{\text{net}} + w_{\text{count}} \cdot U_{\text{count}} + w_{\text{energy}} \cdot U_{\text{energy}}$$

* **Default Weights:**
  * CPU Utilization: $w_{\text{cpu}} = 0.40$
  * RAM Utilization: $w_{\text{ram}} = 0.25$
  * Network Utilization: $w_{\text{net}} = 0.20$
  * Active Workload Count: $w_{\text{count}} = 0.10$
  * Energy Utilization: $w_{\text{energy}} = 0.05$

### B. Normalization Mechanics
* Utilization fractions $U_{\text{cpu}}$, $U_{\text{ram}}$, and $U_{\text{net}}$ are mapped to $[0.0, 1.0]$.
* Workload count $U_{\text{count}} = \frac{\text{count}}{\max(1, \max_{\text{pool}}(\text{count}))}$.
* Energy draw $U_{\text{energy}} = \frac{P_{\text{current}}}{P_{\text{max\_pool}}}$.

### C. Admission Control & Waiting Queue
Before assignment, the controller performs a strict headroom check:
$$\text{Allocated} + \text{Required} \le \text{Capacity}$$
If all healthy servers lack sufficient headroom, the workload is safely enqueued in `workload_queue` and retried automatically as soon as any server completes an active task.

---

## 4. Energy Model

Energy consumption is modeled realistically using static and dynamic power draw:
$$P(t) = P_{\text{idle}} + \left(\frac{U_{\text{cpu}}}{100} \cdot P_{\text{dynamic\_max}}\right) + \left(\frac{U_{\text{net}}}{100} \cdot 15.0\text{ W}\right)$$

* **Cumulative Energy:**
  $$E_{\text{total}} = \sum \frac{P(t) \cdot \Delta t}{3600 \times 1000} \text{ kWh}$$
* **Energy Cost:**
  $$\text{Cost} = E_{\text{total}} \times \text{Tariff per kWh (default: ₹8.00)}$$

---

## 5. Key Features

- **Bright SaaS UI:** Light background, high-contrast metric cards, clean status badges, and Plotly charts.
- **Autonomous Overload Migration:** Detects servers crossing threshold ($\ge 85\%$ CPU/RAM) and live-migrates tasks to healthy nodes.
- **Hardware Failure & Recovery Simulation:** Test server crashes with a single click; workloads are automatically evicted, enqueued, and rescheduled.
- **Interactive Fleet Scaling:** Add new nodes (custom cores/RAM/bandwidth) or decommission servers on the fly.
- **MQTT Telemetry (HiveMQ Cloud & Local):** Multi-topic publishing with non-blocking fallback if the network or broker is offline.
- **Embedded REST API:** Full programmatic control over servers, simulation state, and traffic injection.
- **Preserved ML Anomaly Detection:** Retains the Isolation Forest machine learning model for electrical parameter validation.

---

## 6. Project Structure

```
cloud_loadbalancer_cse_11_105/
│
├── config/
│   ├── __init__.py
│   └── config.py               # Central settings, weights, thresholds, MQTT
│
├── controller/
│   ├── __init__.py
│   ├── load_balancer.py        # Multi-metric weighted load scoring & admission
│   ├── sdn_controller.py       # SDN control plane, flow table & migration
│   └── server_manager.py       # Fleet expansion, scale-out & failure toggles
│
├── simulator/
│   ├── __init__.py
│   ├── workload_generator.py   # Realistic synthetic workload models
│   ├── server_simulator.py     # Virtual server nodes with energy dissipation
│   └── simulation.py           # Master discrete-event simulation engine
│
├── energy-simulator/
│   ├── dashboard.py            # Streamlit Bright SaaS Dashboard
│   ├── energy_simulator.py     # Energy telemetry generator
│   ├── mqtt_publisher.py       # MQTT publisher with HiveMQ/Local fallback
│   ├── mqtt_subscriber.py      # MQTT subscriber daemon
│   ├── config.py               # Energy simulator config adapter
│   ├── latest_data.json        # Legacy JSON telemetry mirror
│   └── ml_model.joblib         # IsolationForest electrical anomaly model
│
├── api/
│   ├── __init__.py
│   └── api_server.py           # Zero-dependency Python ThreadingHTTPServer REST API
│
├── data/
│   └── latestdata.json         # Real-time state, metrics, flow rules & logs
│
├── tests/
│   └── test_simulation.py      # Automated unit test suite
│
├── requirements.txt            # Project dependencies
├── README.md                   # Documentation
└── run.py                      # Unified CLI launcher
```

---

## 7. Installation & Quick Start

### Option A: Complete Docker + Grafana + Prometheus Stack (Recommended)
You can spin up the complete cloud monitoring suite (SDN Load Balancer + Prometheus + Grafana) with a single command:

```bash
docker compose up -d --build
```

**Services Launched:**
- **Grafana Cloud Telemetry:** [`http://localhost:3001`](http://localhost:3001) *(Pre-provisioned with full SDN dashboard, anonymous viewer access enabled)*
- **Streamlit SaaS Dashboard:** [`http://localhost:8505`](http://localhost:8505) *(or 8501)*
- **SDN REST API & Prometheus Exporter:** [`http://localhost:8000/metrics`](http://localhost:8000/metrics)
- **Prometheus TSDB Engine:** [`http://localhost:9090`](http://localhost:9090)

To stop the Docker stack:
```bash
docker compose down
```

---

### Option B: Local Python Execution

#### Step 1: Install Dependencies
```bash
cd cloud_loadbalancer_cse_11_105
pip install -r requirements.txt
```

#### Step 2: Launch the Project
```bash
# Option 1: Direct Streamlit command (Cleanest & Fastest)
streamlit run app.py

# Option 2: Using the unified Python launcher
python run.py

# Option 3: Launch All-In-One (Dashboard + REST API + Prometheus Exporter):
python run.py --all
```
Open your browser at: `http://localhost:8501`

#### Other CLI Modes:
```bash
# Launch standalone REST API on port 8000
python run.py --api

# Launch terminal console live monitor
python run.py --cli

# Run automated test suite
python tests/test_simulation.py
```

---

## 8. REST API Reference

The built-in HTTP server requires zero third-party web frameworks and responds with JSON:

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/status` | Current simulation status, runtime flags, summary |
| `GET` | `/api/servers` | Fleet table (CPU, RAM, Net, Workloads, Status) |
| `GET` | `/api/workloads` | Active and queued workloads across all nodes |
| `GET` | `/api/metrics` | Global telemetry metrics and historical buffer |
| `GET` | `/api/flowtable` | Active SDN OpenFlow routing rules |
| `POST` | `/api/simulation/start` | Start the background simulation loop |
| `POST` | `/api/simulation/pause` | Pause workload arrival and ticking |
| `POST` | `/api/simulation/reset` | Reset fleet and workloads to factory state |
| `POST` | `/api/workload` | Inject a single workload (custom body supported) |
| `POST` | `/api/burst` | Inject a burst of workloads (`{"count": 5}`) |
| `POST` | `/api/server/{id}/failure` | Trigger hardware failure on node |
| `POST` | `/api/server/{id}/recover` | Restore failed node to Healthy state |

---

## 9. MQTT Telemetry Setup

The project supports both **HiveMQ Cloud** (configured out of the box) and local **Mosquitto**:

### HiveMQ Cloud (Default)
Credentials and broker endpoints can be set via environment variables:
```bash
export MQTT_BROKER="your-hivemq-cluster.hivemq.cloud"
export MQTT_PORT=8883
export MQTT_USERNAME="your-username"
export MQTT_PASSWORD="your-password"
export MQTT_USE_TLS=true
```

### Topics Broadcasted:
- `cloud/servers/metrics` - Real-time utilization per server node
- `cloud/workloads` - Active workloads and queued backlogs
- `sdn/controller/decisions` - SDN OpenFlow flow table updates
- `cloud/loadbalancer/status` - Health flags, migrations count, and status
- `smart_energy/data` - Voltage, current, power factor, power (W), and energy (kWh)

### Standalone Publisher & Subscriber
```bash
# In Terminal 1 (Subscriber):
python energy-simulator/mqtt_subscriber.py

# In Terminal 2 (Publisher):
python energy-simulator/mqtt_publisher.py
```
*If HiveMQ is temporarily unreachable, the system automatically falls back to local simulation without crashing.*

---

## 10. Running Automated Tests

A dedicated test suite validates the entire algorithm, SDN routing, queueing, overload detection, and JSON persistence:
```bash
python -m unittest tests/test_simulation.py
```
All tests should pass with `OK`.

---

## 11. Dashboard Controls Guide

1. **Simulation Controls:** Use `▶️ Start`, `⏸️ Pause`, and `🔄 Reset` in the sidebar.
2. **Traffic Injection:** Click `➕ 1 Request` for a single task, or `🚀 Burst (+5)` for sudden traffic spikes.
3. **Weight Sliders:** Adjust relative weights for CPU, RAM, Network, Workloads, and Energy to observe route adaptations.
4. **Server Failure Testing:** Click `Simulate Failure` on any server card. Observe the node turn `Offline`, active workloads get evacuated, and tasks rerouted to remaining nodes. Click `Recover Server` to restore it.
5. **Auto-Migration:** When CPU or RAM utilization crosses $85\%$, the SDN controller automatically live-migrates tasks to prevent crashes.

---

## 12. Future Enhancements

- Integration with Mininet and Ryu SDN OpenFlow Controller via real OpenFlow 1.3 protocol.
- Reinforcement learning (DQN / PPO) agent for dynamic load balancing weight tuning.
- Multi-region latency awareness with simulated geo-distributed edge nodes.

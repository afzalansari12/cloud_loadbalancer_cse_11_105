"""
SDN Dynamic Cloud Load Balancer - Real-Time SaaS Dashboard.
Engineered with a modern bright theme, interactive fleet controls,
live OpenFlow routing visualization, telemetry charts, and ML diagnostics.
"""

import sys
import os
import time
import json
from pathlib import Path
from datetime import datetime

import textwrap
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import joblib

# Ensure root directory is accessible
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from simulator.simulation import get_simulation_engine
from simulator.server_simulator import VirtualServer
from sdn_config.config import TARIFF_PER_KWH

# ==========================================
# PAGE CONFIGURATION
# ==========================================
st.set_page_config(
    page_title="SDN Cloud Load Balancer",
    page_icon="🌐",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==========================================
# BRIGHT MODERN SAAS CSS
# ==========================================
st.markdown("""
<style>
    /* Main Background & Light Theme */
    .stApp {
        background-color: #f8fafc;
        color: #0f172a;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }
    
    /* Headers & Typography */
    h1, h2, h3, h4, h5, h6 {
        color: #0f172a !important;
        font-weight: 700 !important;
    }

    /* Ultra-Bright White Sidebar */
    section[data-testid="stSidebar"] {
        background-color: #ffffff !important;
        border-right: 2px solid #e2e8f0 !important;
        box-shadow: 4px 0 16px rgba(0, 0, 0, 0.03) !important;
    }
    section[data-testid="stSidebar"] > div {
        background-color: #ffffff !important;
    }
    section[data-testid="stSidebar"] [data-testid="stSidebarNav"] {
        background-color: #ffffff !important;
    }
    section[data-testid="stSidebar"] h1, 
    section[data-testid="stSidebar"] h2, 
    section[data-testid="stSidebar"] h3 {
        color: #1e3a8a !important;
        font-size: 1.15rem !important;
        font-weight: 800 !important;
        margin-top: 10px !important;
    }
    section[data-testid="stSidebar"] p, 
    section[data-testid="stSidebar"] label, 
    section[data-testid="stSidebar"] span {
        color: #0f172a !important;
        font-weight: 600 !important;
    }
    section[data-testid="stSidebar"] .stCaption, 
    section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] small {
        color: #475569 !important;
        font-weight: 500 !important;
    }
    section[data-testid="stSidebar"] hr {
        border-color: #e2e8f0 !important;
        border-width: 1.5px !important;
        margin: 16px 0 !important;
    }
    section[data-testid="stSidebar"] [data-testid="stExpander"] {
        background-color: #f8fafc !important;
        border: 1px solid #cbd5e1 !important;
        border-radius: 10px !important;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04) !important;
    }
    section[data-testid="stSidebar"] .stButton>button {
        background-color: #f1f5f9 !important;
        color: #0f172a !important;
        border: 1px solid #cbd5e1 !important;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04) !important;
        font-weight: 700 !important;
    }
    section[data-testid="stSidebar"] .stButton>button:hover {
        background-color: #e2e8f0 !important;
        border-color: #94a3b8 !important;
        color: #1e3a8a !important;
    }
    section[data-testid="stSidebar"] .stButton>button[kind="primary"] {
        background-color: #2563eb !important;
        color: #ffffff !important;
        border: 1px solid #1d4ed8 !important;
    }
    section[data-testid="stSidebar"] .stButton>button[kind="primary"]:hover {
        background-color: #1d4ed8 !important;
    }
    
    /* Top Header Banner */
    .header-banner {
        background: linear-gradient(135deg, #ffffff 0%, #f1f5f9 100%);
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 18px 24px;
        margin-bottom: 20px;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.03);
    }
    
    /* Bright Metric Card */
    .metric-card {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 16px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
        transition: transform 0.15s ease, box-shadow 0.15s ease;
    }
    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 6px rgba(0,0,0,0.06);
    }
    .metric-label {
        font-size: 0.82rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: #64748b;
        margin-bottom: 4px;
    }
    .metric-value {
        font-size: 1.6rem;
        font-weight: 800;
        color: #0f172a;
    }
    .metric-sub {
        font-size: 0.78rem;
        color: #94a3b8;
        margin-top: 4px;
    }
    
    /* Server Health Card */
    .server-card {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 18px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.03);
        margin-bottom: 12px;
    }
    
    /* Status Badges */
    .status-badge {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.03em;
    }
    .badge-healthy {
        background-color: #dcfce7;
        color: #15803d;
        border: 1px solid #bbf7d0;
    }
    .badge-warning {
        background-color: #fef3c7;
        color: #b45309;
        border: 1px solid #fde68a;
    }
    .badge-overloaded {
        background-color: #fee2e2;
        color: #b91c1c;
        border: 1px solid #fecaca;
    }
    .badge-offline {
        background-color: #f1f5f9;
        color: #64748b;
        border: 1px solid #e2e8f0;
    }

    /* Activity Stream Item */
    .activity-item {
        padding: 10px 14px;
        border-left: 3px solid #cbd5e1;
        background-color: #ffffff;
        margin-bottom: 8px;
        border-radius: 0 8px 8px 0;
        box-shadow: 0 1px 2px rgba(0,0,0,0.02);
        font-size: 0.88rem;
    }
    .activity-SUCCESS { border-left-color: #16a34a; }
    .activity-WARNING { border-left-color: #d97706; }
    .activity-DANGER  { border-left-color: #dc2626; }
    .activity-INFO    { border-left-color: #2563eb; }

    /* Button Enhancements */
    .stButton>button {
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.2s ease;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# RETRIEVE SIMULATION ENGINE
# ==========================================
engine = get_simulation_engine()

# Automatically start background tick loop if not running
if not engine.is_running and not engine.is_paused:
    engine.start()

# Load ML Model for Electrical Anomaly Detection (Preserving Existing Project Capability)
@st.cache_resource
def load_ml_model():
    model_path = Path(__file__).resolve().parent / "ml_model.joblib"
    if model_path.exists():
        try:
            return joblib.load(str(model_path))
        except Exception:
            return None
    return None

ml_data = load_ml_model()

# ==========================================
# SIDEBAR CONTROLS
# ==========================================
with st.sidebar:
    st.markdown(textwrap.dedent("""
    <div style="text-align: center; margin-bottom: 8px;">
        <svg width="60" height="60" viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
            <rect x="6" y="8" width="52" height="14" rx="4" fill="#2563eb"/>
            <circle cx="14" cy="15" r="2.5" fill="#ffffff"/>
            <circle cx="21" cy="15" r="2.5" fill="#93c5fd"/>
            <rect x="30" y="14" width="22" height="2" rx="1" fill="#bfdbfe"/>
            <rect x="6" y="25" width="52" height="14" rx="4" fill="#0284c7"/>
            <circle cx="14" cy="32" r="2.5" fill="#ffffff"/>
            <circle cx="21" cy="32" r="2.5" fill="#7dd3fc"/>
            <rect x="30" y="31" width="22" height="2" rx="1" fill="#bae6fd"/>
            <rect x="6" y="42" width="52" height="14" rx="4" fill="#0f172a"/>
            <circle cx="14" cy="49" r="2.5" fill="#22c55e"/>
            <circle cx="21" cy="49" r="2.5" fill="#4ade80"/>
            <rect x="30" y="48" width="22" height="2" rx="1" fill="#94a3b8"/>
        </svg>
    </div>
    """), unsafe_allow_html=True)
    st.title("SDN Control Plane")
    st.caption("Dynamic Cloud Load Balancer Manager")

    st.markdown("---")
    st.subheader("🕹️ Simulation Engine")
    col_s1, col_s2 = st.columns(2)
    with col_s1:
        if engine.is_running and not engine.is_paused:
            if st.button("⏸️ Pause", use_container_width=True):
                engine.pause()
                st.rerun()
        else:
            if st.button("▶️ Start", use_container_width=True, type="primary"):
                engine.start()
                st.rerun()
    with col_s2:
        if st.button("🔄 Reset", use_container_width=True):
            engine.reset()
            st.rerun()

    st.markdown("---")
    st.subheader("⚡ Workload Injection")
    col_w1, col_w2 = st.columns(2)
    with col_w1:
        if st.button("➕ 1 Request", use_container_width=True):
            engine.generate_workload_now()
            st.rerun()
    with col_w2:
        if st.button("🚀 Burst (+5)", use_container_width=True):
            engine.generate_burst_now(count=5)
            st.rerun()

    arrival_rate = st.slider(
        "Workload Arrival Interval (sec)",
        min_value=1.0,
        max_value=10.0,
        value=float(engine.arrival_interval),
        step=0.5
    )
    if arrival_rate != engine.arrival_interval:
        engine.arrival_interval = arrival_rate

    auto_mig = st.checkbox("Autonomous Workload Migration", value=engine.auto_migration_enabled)
    engine.auto_migration_enabled = auto_mig

    st.markdown("---")
    st.subheader("⚖️ Load Balancing Weights")
    st.caption("Normalized Score = Σ(Weight × Metric)")

    w_cpu = st.slider("CPU Weight", 0.0, 1.0, float(engine.load_balancer.weights.get("cpu", 0.40)), 0.05)
    w_ram = st.slider("RAM Weight", 0.0, 1.0, float(engine.load_balancer.weights.get("ram", 0.25)), 0.05)
    w_net = st.slider("Network Weight", 0.0, 1.0, float(engine.load_balancer.weights.get("net", 0.20)), 0.05)
    w_count = st.slider("Workload Count Weight", 0.0, 1.0, float(engine.load_balancer.weights.get("count", 0.10)), 0.05)
    w_energy = st.slider("Energy Weight", 0.0, 1.0, float(engine.load_balancer.weights.get("energy", 0.05)), 0.05)

    if st.button("Apply New Weights", use_container_width=True):
        engine.load_balancer.update_weights({
            "cpu": w_cpu,
            "ram": w_ram,
            "net": w_net,
            "count": w_count,
            "energy": w_energy
        })
        st.success("Weights updated!")
        st.rerun()

    st.markdown("---")
    st.subheader("🛠️ Fleet Scaling")
    with st.expander("Add New Server Node"):
        new_name = st.text_input("Server Name", value=f"Node-East-{len(engine.sdn_controller.servers)+1:02d}")
        new_cpu = st.selectbox("CPU Cores", [4, 8, 12, 16, 32], index=1)
        new_ram = st.selectbox("RAM (GB)", [8.0, 16.0, 24.0, 32.0, 64.0], index=1)
        new_net = st.selectbox("Bandwidth (Mbps)", [500.0, 1000.0, 2000.0], index=1)
        if st.button("Deploy Server", type="primary", use_container_width=True):
            engine.server_manager.add_custom_server(
                name=new_name,
                cpu_cores=new_cpu,
                ram_gb=new_ram,
                net_mbps=new_net
            )
            st.rerun()

    with st.expander("Decommission Server"):
        server_ids = list(engine.sdn_controller.servers.keys())
        del_id = st.selectbox("Select Node", server_ids)
        if st.button("Remove Server", use_container_width=True):
            if engine.server_manager.remove_server(del_id):
                st.success(f"{del_id} removed.")
                st.rerun()
            else:
                st.error("Cannot remove last node.")

    st.markdown("---")
    st.caption(f"Backend Engine: {'Active' if engine.is_running else 'Stopped'} • Auto-Refresh: 2s")


# ==========================================
# FETCH REAL-TIME SNAPSHOT
# ==========================================
snapshot = engine.get_snapshot()
summary = snapshot["summary"]
servers = snapshot["servers"]
history = snapshot.get("history", [])
activity_logs = snapshot.get("activity_log", [])
flow_table = snapshot.get("flow_table", [])
queued_items = snapshot.get("queued_items", [])

# ==========================================
# TOP HEADER BANNER
# ==========================================
header_html = textwrap.dedent(f"""
<div class="header-banner">
    <div style="display: flex; justify-content: space-between; align-items: center;">
        <div>
            <h1 style="margin: 0; font-size: 1.75rem; color: #1e3a8a;">🌐 SDN Cloud Workload Dynamic Load Balancer</h1>
            <p style="margin: 4px 0 0 0; color: #475569; font-size: 0.95rem;">
                Software-Defined Control Plane • Multi-Metric Dynamic Routing • Autonomous Overload Migration • HiveMQ Telemetry
            </p>
        </div>
        <div style="text-align: right;">
            <span class="status-badge {'badge-healthy' if snapshot['is_running'] and not snapshot['is_paused'] else 'badge-warning'}">
                ● {'ENGINE RUNNING' if snapshot['is_running'] and not snapshot['is_paused'] else ('PAUSED' if snapshot['is_paused'] else 'OFFLINE')}
            </span>
            <div style="font-size: 0.8rem; color: #64748b; margin-top: 4px;">Tick Snapshot: {snapshot['timestamp']}</div>
        </div>
    </div>
</div>
""").strip()
st.markdown(header_html, unsafe_allow_html=True)

# ==========================================
# 1. OVERVIEW METRICS RIBBON (8 Cards)
# ==========================================
col1, col2, col3, col4, col5, col6, col7, col8 = st.columns(8)

with col1:
    st.markdown(textwrap.dedent(f"""
    <div class="metric-card">
        <div class="metric-label">Servers</div>
        <div class="metric-value">{summary['total_servers']}</div>
        <div class="metric-sub">{summary['online_servers']} Online • {summary['offline_servers']} Down</div>
    </div>
    """).strip(), unsafe_allow_html=True)

with col2:
    st.markdown(textwrap.dedent(f"""
    <div class="metric-card">
        <div class="metric-label">Active Tasks</div>
        <div class="metric-value" style="color: #2563eb;">{summary['active_workloads']}</div>
        <div class="metric-sub">{summary['completed_workloads']} Completed</div>
    </div>
    """).strip(), unsafe_allow_html=True)

with col3:
    st.markdown(textwrap.dedent(f"""
    <div class="metric-card">
        <div class="metric-label">Avg CPU</div>
        <div class="metric-value" style="color: {'#dc2626' if summary['avg_cpu_percent'] >= 85 else ('#d97706' if summary['avg_cpu_percent'] >= 70 else '#16a34a')};">{summary['avg_cpu_percent']}%</div>
        <div class="metric-sub">Threshold: 85% Over</div>
    </div>
    """).strip(), unsafe_allow_html=True)

with col4:
    st.markdown(textwrap.dedent(f"""
    <div class="metric-card">
        <div class="metric-label">Avg RAM</div>
        <div class="metric-value" style="color: {'#dc2626' if summary['avg_ram_percent'] >= 85 else ('#d97706' if summary['avg_ram_percent'] >= 70 else '#0284c7')};">{summary['avg_ram_percent']}%</div>
        <div class="metric-sub">Fleet Memory Used</div>
    </div>
    """).strip(), unsafe_allow_html=True)

with col5:
    st.markdown(textwrap.dedent(f"""
    <div class="metric-card">
        <div class="metric-label">Avg Network</div>
        <div class="metric-value">{summary['avg_net_percent']}%</div>
        <div class="metric-sub">SDN Port Utilization</div>
    </div>
    """).strip(), unsafe_allow_html=True)

with col6:
    st.markdown(textwrap.dedent(f"""
    <div class="metric-card">
        <div class="metric-label">Total Power</div>
        <div class="metric-value" style="color: #4f46e5;">{summary['total_power_w']} W</div>
        <div class="metric-sub">{summary['total_energy_kwh']:.3f} kWh (₹{summary['energy_cost_currency']:.2f})</div>
    </div>
    """).strip(), unsafe_allow_html=True)

with col7:
    st.markdown(textwrap.dedent(f"""
    <div class="metric-card">
        <div class="metric-label">Task Queue</div>
        <div class="metric-value" style="color: {'#dc2626' if summary['queued_workloads'] > 0 else '#64748b'};">{summary['queued_workloads']}</div>
        <div class="metric-sub">Admission Controlled</div>
    </div>
    """).strip(), unsafe_allow_html=True)

with col8:
    st.markdown(textwrap.dedent(f"""
    <div class="metric-card">
        <div class="metric-label">Overloaded</div>
        <div class="metric-value" style="color: {'#dc2626' if summary['overloaded_servers'] > 0 else '#16a34a'};">{summary['overloaded_servers']}</div>
        <div class="metric-sub">{summary['total_migrations']} Auto Migrated</div>
    </div>
    """).strip(), unsafe_allow_html=True)

st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)

# ==========================================
# 2. SERVER FLEET MONITORING & HEALTH CARDS
# ==========================================
st.subheader("🖥️ Virtual Cloud Server Fleet")
server_cols = st.columns(len(servers))

for idx, s in enumerate(servers):
    with server_cols[idx]:
        status_class = f"badge-{s['status'].lower()}"
        card_html = textwrap.dedent(f"""
        <div class="server-card">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                <strong style="font-size: 1.05rem; color: #0f172a;">{s['id']}</strong>
                <span class="status-badge {status_class}">{s['status']}</span>
            </div>
            <div style="font-size: 0.8rem; color: #64748b; margin-bottom: 12px;">{s['name']}</div>
            
            <div style="margin-bottom: 8px;">
                <div style="display: flex; justify-content: space-between; font-size: 0.78rem; font-weight: 600;">
                    <span>CPU ({s['allocated_cpu']}/{s['cpu_capacity']} Cores)</span>
                    <span>{s['cpu_utilization']}%</span>
                </div>
                <div style="background-color: #e2e8f0; border-radius: 4px; height: 6px; overflow: hidden;">
                    <div style="width: {s['cpu_utilization']}%; height: 100%; background-color: {'#dc2626' if s['cpu_utilization']>=85 else ('#d97706' if s['cpu_utilization']>=70 else '#2563eb')};"></div>
                </div>
            </div>

            <div style="margin-bottom: 8px;">
                <div style="display: flex; justify-content: space-between; font-size: 0.78rem; font-weight: 600;">
                    <span>RAM ({s['allocated_ram']}/{s['ram_capacity']} GB)</span>
                    <span>{s['ram_utilization']}%</span>
                </div>
                <div style="background-color: #e2e8f0; border-radius: 4px; height: 6px; overflow: hidden;">
                    <div style="width: {s['ram_utilization']}%; height: 100%; background-color: {'#dc2626' if s['ram_utilization']>=85 else ('#d97706' if s['ram_utilization']>=70 else '#06b6d4')};"></div>
                </div>
            </div>

            <div style="margin-bottom: 12px;">
                <div style="display: flex; justify-content: space-between; font-size: 0.78rem; font-weight: 600;">
                    <span>Network ({s['allocated_net']:.0f}/{s['net_capacity']:.0f} Mbps)</span>
                    <span>{s['net_utilization']}%</span>
                </div>
                <div style="background-color: #e2e8f0; border-radius: 4px; height: 6px; overflow: hidden;">
                    <div style="width: {s['net_utilization']}%; height: 100%; background-color: #10b981;"></div>
                </div>
            </div>

            <div style="display: flex; justify-content: space-between; font-size: 0.8rem; color: #475569; padding-top: 8px; border-top: 1px dashed #e2e8f0;">
                <div>Active Tasks: <strong>{s['active_workloads']}</strong></div>
                <div>Power: <strong>{s['current_power_w']} W</strong></div>
            </div>
        </div>
        """).strip()
        st.markdown(card_html, unsafe_allow_html=True)

        # Failure / Recovery Interactive Control
        if s['is_online']:
            if st.button(f"Simulate Failure", key=f"fail_{s['id']}", use_container_width=True):
                engine.sdn_controller.simulate_server_failure(s['id'])
                st.rerun()
        else:
            if st.button(f"Recover Server", key=f"rec_{s['id']}", type="primary", use_container_width=True):
                engine.sdn_controller.simulate_server_recovery(s['id'])
                st.rerun()

st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

# ==========================================
# 3. LIVE LOAD BALANCING DISTRIBUTION & SDN FLOW TABLE
# ==========================================
col_lb1, col_lb2 = st.columns([1, 1])

with col_lb1:
    st.subheader("📊 Dynamic Workload Distribution")
    dist_df = pd.DataFrame([
        {
            "Server": s["id"],
            "Workloads": s["active_workloads"],
            "CPU %": s["cpu_utilization"],
            "Status": s["status"]
        }
        for s in servers
    ])

    fig_dist = px.bar(
        dist_df,
        x="Server",
        y="Workloads",
        color="Status",
        color_discrete_map={
            "Healthy": "#2563eb",
            "Warning": "#d97706",
            "Overloaded": "#dc2626",
            "Offline": "#94a3b8"
        },
        text="Workloads"
    )
    fig_dist.update_layout(
        plot_bgcolor="#ffffff",
        paper_bgcolor="#ffffff",
        margin=dict(l=20, r=20, t=30, b=20),
        height=280,
        yaxis=dict(gridcolor="#f1f5f9", title="Active Workload Count"),
        xaxis=dict(title="")
    )
    st.plotly_chart(fig_dist, use_container_width=True)

with col_lb2:
    st.subheader("🛣️ SDN Flow Table & Routing Rules")
    if flow_table:
        flow_df = pd.DataFrame(flow_table)[["workload_id", "target_server", "load_score", "created_at", "status"]]
        flow_df.columns = ["Workload ID", "Assigned Server", "Load Score", "Assigned At", "Flow Status"]
        st.dataframe(flow_df.tail(8), use_container_width=True, height=280)
    else:
        st.info("No active OpenFlow routing rules in table. Inject workloads to populate.")

# ==========================================
# 4. REAL-TIME CHARTS
# ==========================================
st.subheader("📈 Real-Time Cloud Infrastructure Telemetry")

if len(history) > 1:
    hist_df = pd.DataFrame(history)

    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:
        st.markdown("**Resource Utilization Over Time (CPU, RAM, Network %)**")
        fig_res = go.Figure()
        fig_res.add_trace(go.Scatter(x=hist_df["time"], y=hist_df["avg_cpu"], mode="lines+markers", name="CPU %", line=dict(color="#2563eb", width=2.5)))
        fig_res.add_trace(go.Scatter(x=hist_df["time"], y=hist_df["avg_ram"], mode="lines+markers", name="RAM %", line=dict(color="#06b6d4", width=2.5)))
        fig_res.add_trace(go.Scatter(x=hist_df["time"], y=hist_df["avg_net"], mode="lines+markers", name="Network %", line=dict(color="#10b981", width=2.0)))
        fig_res.update_layout(
            plot_bgcolor="#ffffff",
            paper_bgcolor="#ffffff",
            margin=dict(l=20, r=20, t=20, b=20),
            height=300,
            yaxis=dict(range=[0, 105], gridcolor="#f1f5f9", title="Utilization (%)"),
            xaxis=dict(gridcolor="#f1f5f9", showticklabels=False),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig_res, use_container_width=True)

    with chart_col2:
        st.markdown("**Dynamic Power Draw (Watts) & Energy Accumulation**")
        fig_pow = go.Figure()
        fig_pow.add_trace(go.Scatter(x=hist_df["time"], y=hist_df["total_power"], mode="lines+markers", name="Power (W)", line=dict(color="#8b5cf6", width=2.5)))
        fig_pow.update_layout(
            plot_bgcolor="#ffffff",
            paper_bgcolor="#ffffff",
            margin=dict(l=20, r=20, t=20, b=20),
            height=300,
            yaxis=dict(gridcolor="#f1f5f9", title="Instantaneous Power (Watts)"),
            xaxis=dict(gridcolor="#f1f5f9", showticklabels=False),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig_pow, use_container_width=True)

else:
    st.info("Accumulating telemetry data points... Please wait a few seconds.")

# ==========================================
# 5. LIVE ACTIVITY PANEL & QUEUE MONITOR
# ==========================================
col_act1, col_act2 = st.columns([2, 1])

with col_act1:
    st.subheader("⚡ Live SDN Activity & Event Stream")
    if activity_logs:
        log_html = "<div style='max-height: 280px; overflow-y: auto; padding-right: 8px;'>"
        for entry in activity_logs[:12]:
            lvl = entry.get("level", "INFO")
            ts = entry.get("timestamp", "")
            msg = entry.get("message", "")
            log_html += f"""
            <div class="activity-item activity-{lvl}">
                <span style="font-size: 0.76rem; font-weight: 700; color: #64748b; margin-right: 8px;">[{ts}]</span>
                <span style="font-weight: 500;">{msg}</span>
            </div>
            """
        log_html += "</div>"
        st.markdown(log_html, unsafe_allow_html=True)
    else:
        st.write("No events recorded yet.")

with col_act2:
    st.subheader("⏳ Admission Control Queue")
    if queued_items:
        st.warning(f"⚠️ {len(queued_items)} Workload(s) waiting for server capacity!")
        q_df = pd.DataFrame(queued_items)[["workload_id", "category", "cpu_req", "ram_req", "duration"]]
        st.dataframe(q_df, use_container_width=True, height=220)
    else:
        st.success("✅ Zero backlog. All workloads admitted and assigned.")

    # Machine Learning Anomaly Detection Card (Preserved from existing project)
    if ml_data is not None:
        try:
            model = ml_data["model"]
            features = ml_data["features"]
            current_df = pd.DataFrame([{
                "voltage": snapshot.get("voltage", 230.0),
                "current": snapshot.get("current", 2.0),
                "power": snapshot.get("power", 400.0),
                "power_factor": snapshot.get("power_factor", 0.95)
            }])
            pred = model.predict(current_df[features])[0]
            ml_badge = "ANOMALY DETECTED" if pred == -1 else "NORMAL OPERATION"
            badge_type = "badge-overloaded" if pred == -1 else "badge-healthy"
            st.markdown(f"""
            <div style="background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px; margin-top: 10px;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <span style="font-size: 0.82rem; font-weight: 600; color: #475569;">🤖 ML Energy Anomaly Model:</span>
                    <span class="status-badge {badge_type}">{ml_badge}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
        except Exception:
            pass

# ==========================================
# AUTO REFRESH LOOP
# ==========================================
time.sleep(2)
st.rerun()
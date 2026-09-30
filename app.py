"""
Main Streamlit application entry point for SDN Dynamic Cloud Load Balancer.
Usage:
    streamlit run app.py
"""

import sys
from pathlib import Path

# Ensure root directory is at index 0 of sys.path
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Execute the dashboard
dashboard_path = ROOT_DIR / "energy-simulator" / "dashboard.py"
with open(dashboard_path, "r", encoding="utf-8") as f:
    code = compile(f.read(), str(dashboard_path), "exec")
    exec(code, globals())

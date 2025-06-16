#!/usr/bin/env python3
"""Streamlit dashboard for monitoring and controlling the Web4AI orchestrator."""

import streamlit as st
import requests
import pandas as pd
import time
from datetime import datetime

st.set_page_config(
    page_title="Web4AI Orchestrator Dashboard",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("🚀 Web4AI Orchestrator Dashboard")

# Sidebar configuration
st.sidebar.header("Configuration")
orc_url = st.sidebar.text_input("Orchestrator URL", value="http://localhost:9000")
auto_refresh = st.sidebar.checkbox("Auto Refresh", value=True)
refresh_interval = st.sidebar.slider("Refresh Interval (seconds)", 2, 30, 5)

api_base = f"{orc_url}/api/v1"

# Control buttons
st.sidebar.header("Control")
col_start, col_stop, col_restart = st.sidebar.columns(3)
if col_start.button("Start"):
    try:
        r = requests.post(f"{api_base}/control/start", timeout=5)
        st.sidebar.success(r.json().get("message", "Started"))
    except Exception as e:
        st.sidebar.error(f"Start failed: {e}")
if col_stop.button("Stop"):
    try:
        r = requests.post(f"{api_base}/control/stop", timeout=5)
        st.sidebar.success(r.json().get("message", "Stopped"))
    except Exception as e:
        st.sidebar.error(f"Stop failed: {e}")
if col_restart.button("Restart"):
    try:
        r = requests.post(f"{api_base}/control/restart", timeout=5)
        st.sidebar.success(r.json().get("message", "Restarted"))
    except Exception as e:
        st.sidebar.error(f"Restart failed: {e}")

# Helper functions
@st.cache_data(ttl=5)
def fetch_status() -> dict:
    """Retrieve orchestrator status information."""
    try:
        return requests.get(f"{api_base}/status", timeout=5).json()
    except Exception as e:
        st.error(f"Status error: {e}")
        return {}

@st.cache_data(ttl=5)
def fetch_metrics() -> dict:
    """Retrieve orchestrator performance metrics."""
    try:
        return requests.get(f"{api_base}/metrics/performance", timeout=5).json()
    except Exception as e:
        st.error(f"Metrics error: {e}")
        return {}

status_data = fetch_status()
metrics_data = fetch_metrics()

# Display key metrics
if status_data.get("success"):
    nm = status_data["data"]["network_metrics"]
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Active Nodes", nm.get("active_nodes", 0))
    col2.metric("Tasks Completed", nm.get("tasks_completed", 0))
    utilization = nm.get("network_utilization", 0)
    col3.metric("Utilization", f"{utilization * 100:.1f}%")
    col4.metric("Success Rate", f"{nm.get('success_rate',0):.1f}%")

# Maintain history for charts
if 'history' not in st.session_state:
    st.session_state['history'] = []

if status_data.get("success"):
    st.session_state['history'].append({
        'time': datetime.now(),
        'utilization': nm.get('network_utilization', 0),
        'active_nodes': nm.get('active_nodes', 0)
    })
    if len(st.session_state['history']) > 50:
        st.session_state['history'] = st.session_state['history'][-50:]

if st.session_state['history']:
    df_hist = pd.DataFrame(st.session_state['history'])
    st.line_chart(df_hist.set_index('time')[['utilization','active_nodes']])

# Node table
if status_data.get("success"):
    nodes = status_data["data"].get("nodes", {})
    if nodes:
        node_list = []
        for node_id, info in nodes.items():
            node_list.append({
                'Node ID': node_id,
                'Status': info.get('status'),
                'CPU %': info.get('cpu_usage'),
                'Memory %': info.get('memory_usage'),
                'Load': info.get('load_score'),
                'Agents': info.get('agents_count')
            })
        st.subheader("Nodes")
        st.dataframe(pd.DataFrame(node_list))

# Task summary
if status_data.get("success"):
    st.subheader("Tasks")
    tasks = {
        'Pending': status_data['data'].get('pending_tasks', 0),
        'Active': status_data['data'].get('active_tasks', 0),
        'Completed': status_data['data'].get('completed_tasks', 0),
        'Failed': status_data['data'].get('failed_tasks', 0)
    }
    st.bar_chart(pd.DataFrame.from_dict(tasks, orient='index', columns=['count']))

# Auto-refresh
if auto_refresh:
    time.sleep(refresh_interval)
    st.experimental_rerun()


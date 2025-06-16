#!/usr/bin/env python3
"""
Fixed Advanced Dashboard for Web4AI Orchestrator
This fixes the AttributeError and improves error handling
"""

import streamlit as st
import requests
import json
import time
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
ORCHESTRATOR_URL = "https://orc.peoplesainetwork.com"
REFRESH_INTERVAL = 30  # seconds

# Page configuration
st.set_page_config(
    page_title="Web4AI Orchestrator Dashboard",
    page_icon="🎛️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        text-align: center;
        color: #1f77b4;
        font-size: 2.5rem;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin: 0.5rem 0;
    }
    .status-online {
        color: #28a745;
        font-weight: bold;
    }
    .status-offline {
        color: #dc3545;
        font-weight: bold;
    }
    .status-warning {
        color: #ffc107;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

def safe_get(data, key, default=None):
    """Safely get a value from data, handling both dict and non-dict cases"""
    if isinstance(data, dict):
        return data.get(key, default)
    else:
        return default

def fetch_orchestrator_status():
    """Fetch status from orchestrator with error handling"""
    try:
        response = requests.get(f"{ORCHESTRATOR_URL}/api/v1/status", timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"API returned status code: {response.status_code}")
            return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching orchestrator status: {e}")
        return None

def fetch_orchestrator_health():
    """Fetch health from orchestrator with error handling"""
    try:
        response = requests.get(f"{ORCHESTRATOR_URL}/api/v1/health", timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"Health API returned status code: {response.status_code}")
            return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching orchestrator health: {e}")
        return None

def fetch_nodes():
    """Fetch nodes from orchestrator with error handling"""
    try:
        response = requests.get(f"{ORCHESTRATOR_URL}/api/v1/nodes", timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"Nodes API returned status code: {response.status_code}")
            return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching nodes: {e}")
        return None

def display_header():
    """Display the main header"""
    st.markdown('<h1 class="main-header">🎛️ Web4AI Orchestrator Dashboard</h1>', unsafe_allow_html=True)
    st.markdown(f"**🌐 Connected to:** {ORCHESTRATOR_URL}")
    st.markdown("---")

def display_health_status():
    """Display health status section"""
    st.subheader("🏥 System Health")
    
    health_data = fetch_orchestrator_health()
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if health_data and safe_get(health_data, 'status') == 'healthy':
            st.markdown('<div class="status-online">✅ HEALTHY</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="status-offline">❌ UNHEALTHY</div>', unsafe_allow_html=True)
    
    with col2:
        timestamp = safe_get(health_data, 'timestamp', 'Unknown') if health_data else 'Unknown'
        st.metric("Last Check", timestamp)
    
    with col3:
        orchestrator_id = safe_get(health_data, 'orchestrator_id', 'Unknown') if health_data else 'Unknown'
        st.metric("Orchestrator ID", orchestrator_id)
    
    with col4:
        version = safe_get(health_data, 'version', '1.0.0') if health_data else '1.0.0'
        st.metric("Version", version)

def display_network_overview():
    """Display network overview section"""
    st.subheader("🌐 Network Overview")
    
    status_data = fetch_orchestrator_status()
    
    if not status_data or not safe_get(status_data, 'success', False):
        st.error("❌ Unable to fetch network status")
        return
    
    data = safe_get(status_data, 'data', {})
    network_metrics = safe_get(data, 'network_metrics', {})
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        active_tasks = safe_get(data, 'active_tasks', 0)
        st.metric("Active Tasks", active_tasks)
    
    with col2:
        pending_tasks = safe_get(data, 'pending_tasks', 0)
        st.metric("Pending Tasks", pending_tasks)
    
    with col3:
        completed_tasks = safe_get(data, 'completed_tasks', 0)
        st.metric("Completed Tasks", completed_tasks)
    
    with col4:
        failed_tasks = safe_get(data, 'failed_tasks', 0)
        st.metric("Failed Tasks", failed_tasks)
    
    # Network metrics
    col1, col2, col3 = st.columns(3)
    
    with col1:
        uptime = safe_get(network_metrics, 'uptime', 0)
        uptime_hours = round(uptime / 3600, 2) if uptime else 0
        st.metric("Uptime (hours)", uptime_hours)
    
    with col2:
        utilization = safe_get(network_metrics, 'network_utilization', 0)
        st.metric("Network Utilization (%)", f"{utilization:.1f}")
    
    with col3:
        efficiency = safe_get(network_metrics, 'overall_efficiency', 0)
        st.metric("Overall Efficiency (%)", f"{efficiency:.1f}")

def display_nodes_section():
    """Display nodes section"""
    st.subheader("📡 Network Nodes")
    
    nodes_data = fetch_nodes()
    
    if not nodes_data or not safe_get(nodes_data, 'success', False):
        st.warning("⚠️ No nodes data available")
        return
    
    nodes = safe_get(nodes_data, 'nodes', {})
    total_nodes = safe_get(nodes_data, 'total_nodes', 0)
    
    st.metric("Total Nodes", total_nodes)
    
    if not nodes:
        st.info("🔍 No nodes currently registered")
        return
    
    # Create nodes DataFrame
    nodes_list = []
    for node_id, node_info in nodes.items():
        # Handle both dict and non-dict node_info
        if isinstance(node_info, dict):
            nodes_list.append({
                'Node ID': node_id,
                'Status': safe_get(node_info, 'status', 'unknown'),
                'Host': safe_get(node_info, 'host', 'unknown'),
                'Port': safe_get(node_info, 'port', 'unknown'),
                'CPU Usage (%)': safe_get(node_info, 'cpu_usage', 0),
                'Memory Usage (%)': safe_get(node_info, 'memory_usage', 0),
                'Load Score': safe_get(node_info, 'load_score', 0),
                'Last Heartbeat': safe_get(node_info, 'last_heartbeat', 'unknown')
            })
        else:
            # If node_info is not a dict, create a minimal entry
            nodes_list.append({
                'Node ID': node_id,
                'Status': 'unknown',
                'Host': 'unknown',
                'Port': 'unknown',
                'CPU Usage (%)': 0,
                'Memory Usage (%)': 0,
                'Load Score': 0,
                'Last Heartbeat': 'unknown'
            })
    
    if nodes_list:
        df = pd.DataFrame(nodes_list)
        st.dataframe(df, use_container_width=True)
        
        # Node Status Chart
        if len(nodes_list) > 0:
            status_counts = df['Status'].value_counts()
            fig = px.pie(
                values=status_counts.values,
                names=status_counts.index,
                title="Node Status Distribution",
                color_discrete_map={
                    'active': '#28a745',
                    'inactive': '#dc3545',
                    'maintenance': '#ffc107',
                    'unknown': '#6c757d'
                }
            )
            st.plotly_chart(fig, use_container_width=True)

def display_performance_metrics():
    """Display performance metrics section"""
    st.subheader("📊 Performance Metrics")
    
    # Try to get performance metrics
    try:
        response = requests.get(f"{ORCHESTRATOR_URL}/api/v1/metrics/performance", timeout=10)
        if response.status_code == 200:
            metrics_data = response.json()
            if safe_get(metrics_data, 'success', False):
                performance = safe_get(metrics_data, 'performance', {})
                
                col1, col2 = st.columns(2)
                
                with col1:
                    avg_cpu = safe_get(performance, 'average_cpu_usage', 0)
                    avg_memory = safe_get(performance, 'average_memory_usage', 0)
                    
                    # CPU Usage Gauge
                    fig_cpu = go.Figure(go.Indicator(
                        mode = "gauge+number",
                        value = avg_cpu,
                        domain = {'x': [0, 1], 'y': [0, 1]},
                        title = {'text': "Average CPU Usage (%)"},
                        gauge = {
                            'axis': {'range': [None, 100]},
                            'bar': {'color': "darkblue"},
                            'steps': [
                                {'range': [0, 50], 'color': "lightgray"},
                                {'range': [50, 80], 'color': "yellow"},
                                {'range': [80, 100], 'color': "red"}
                            ],
                            'threshold': {
                                'line': {'color': "red", 'width': 4},
                                'thickness': 0.75,
                                'value': 90
                            }
                        }
                    ))
                    fig_cpu.update_layout(height=300)
                    st.plotly_chart(fig_cpu, use_container_width=True)
                
                with col2:
                    # Memory Usage Gauge
                    fig_memory = go.Figure(go.Indicator(
                        mode = "gauge+number",
                        value = avg_memory,
                        domain = {'x': [0, 1], 'y': [0, 1]},
                        title = {'text': "Average Memory Usage (%)"},
                        gauge = {
                            'axis': {'range': [None, 100]},
                            'bar': {'color': "darkgreen"},
                            'steps': [
                                {'range': [0, 50], 'color': "lightgray"},
                                {'range': [50, 80], 'color': "yellow"},
                                {'range': [80, 100], 'color': "red"}
                            ],
                            'threshold': {
                                'line': {'color': "red", 'width': 4},
                                'thickness': 0.75,
                                'value': 90
                            }
                        }
                    ))
                    fig_memory.update_layout(height=300)
                    st.plotly_chart(fig_memory, use_container_width=True)
                
                # Additional metrics
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    active_nodes = safe_get(performance, 'active_nodes', 0)
                    st.metric("Active Nodes", active_nodes)
                
                with col2:
                    throughput = safe_get(performance, 'task_throughput', 0)
                    st.metric("Task Throughput", f"{throughput:.2f}")
                
                with col3:
                    success_rate = safe_get(performance, 'success_rate', 0)
                    st.metric("Success Rate (%)", f"{success_rate:.1f}")
            else:
                st.warning("⚠️ Performance metrics not available")
        else:
            st.warning("⚠️ Performance metrics endpoint not responding")
    except Exception as e:
        st.warning(f"⚠️ Error fetching performance metrics: {str(e)}")

def display_system_logs():
    """Display system logs section"""
    st.subheader("📋 System Information")
    
    # Show raw API responses for debugging
    with st.expander("🔍 API Response Debug Info"):
        col1, col2 = st.columns(2)
        
        with col1:
            st.text("Health API Response:")
            health_data = fetch_orchestrator_health()
            st.json(health_data if health_data else {"error": "No response"})
        
        with col2:
            st.text("Status API Response:")
            status_data = fetch_orchestrator_status()
            st.json(status_data if status_data else {"error": "No response"})

def main():
    """Main dashboard function"""
    display_header()
    
    # Auto-refresh checkbox
    auto_refresh = st.sidebar.checkbox("🔄 Auto-refresh", value=True)
    refresh_interval = st.sidebar.slider("Refresh interval (seconds)", 10, 300, REFRESH_INTERVAL)
    
    # Manual refresh button
    if st.sidebar.button("🔄 Refresh Now"):
        st.rerun()
    
    # Connection test
    st.sidebar.subheader("🔗 Connection Test")
    try:
        test_response = requests.get(f"{ORCHESTRATOR_URL}/api/v1/health", timeout=5)
        if test_response.status_code == 200:
            st.sidebar.success("✅ Connected")
        else:
            st.sidebar.error(f"❌ Error: {test_response.status_code}")
    except Exception as e:
        st.sidebar.error(f"❌ Connection failed: {str(e)}")
    
    # Display all sections
    display_health_status()
    st.markdown("---")
    
    display_network_overview()
    st.markdown("---")
    
    display_nodes_section()
    st.markdown("---")
    
    display_performance_metrics()
    st.markdown("---")
    
    display_system_logs()
    
    # Auto-refresh logic
    if auto_refresh:
        time.sleep(refresh_interval)
        st.rerun()

if __name__ == "__main__":
    main()
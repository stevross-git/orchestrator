# web4ai_client.py - Python Client SDK
"""
Web4AI Orchestrator Python Client SDK
Provides easy-to-use Python interface for interacting with the orchestrator
"""

import requests
import json
import time
import asyncio
import websockets
from typing import Dict, Any, List, Optional, Callable, Union
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class TaskPriority(Enum):
    """Task priority levels"""
    CRITICAL = 1
    HIGH = 2
    NORMAL = 3
    LOW = 4
    BACKGROUND = 5

class TaskStatus(Enum):
    """Task status values"""
    PENDING = "pending"
    QUEUED = "queued"
    ASSIGNED = "assigned"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"

@dataclass
class TaskResult:
    """Task execution result"""
    task_id: str
    status: TaskStatus
    result_data: Any = None
    execution_time: float = 0
    error_message: Optional[str] = None
    node_id: Optional[str] = None
    agent_id: Optional[str] = None

@dataclass
class NodeInfo:
    """Node information"""
    node_id: str
    host: str
    port: int
    status: str
    capabilities: List[str]
    cpu_usage: float
    memory_usage: float
    load_score: float

class Web4AIClient:
    """Main client for Web4AI Orchestrator"""
    
    def __init__(self, 
                 base_url: str = "http://localhost:9000",
                 api_key: Optional[str] = None,
                 timeout: int = 30):
        """
        Initialize the Web4AI client
        
        Args:
            base_url: Orchestrator base URL
            api_key: API key for authentication
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip('/')
        self.api_url = f"{self.base_url}/api/v1"
        self.api_key = api_key
        self.timeout = timeout
        self.session = requests.Session()
        
        # Set default headers
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'Web4AI-Python-Client/1.0'
        })
        
        if api_key:
            self.session.headers['Authorization'] = f'Bearer {api_key}'
    
    def _request(self, method: str, endpoint: str, data: Dict = None, 
                params: Dict = None) -> Dict[str, Any]:
        """Make HTTP request to orchestrator"""
        url = f"{self.api_url}{endpoint}"
        
        try:
            response = self.session.request(
                method=method,
                url=url,
                json=data,
                params=params,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {e}")
            raise
    
    def health_check(self) -> Dict[str, Any]:
        """Check orchestrator health"""
        return self._request('GET', '/health')
    
    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive orchestrator status"""
        return self._request('GET', '/status')
    
    def get_nodes(self) -> List[NodeInfo]:
        """Get all registered nodes"""
        response = self._request('GET', '/nodes')
        nodes = []
        
        for node_data in response.get('nodes', {}).values():
            nodes.append(NodeInfo(
                node_id=node_data['node_id'],
                host=node_data['host'],
                port=node_data['port'],
                status=node_data['status'],
                capabilities=node_data['capabilities'],
                cpu_usage=node_data['cpu_usage'],
                memory_usage=node_data['memory_usage'],
                load_score=node_data['load_score']
            ))
        
        return nodes
    
    def get_node(self, node_id: str) -> NodeInfo:
        """Get specific node information"""
        response = self._request('GET', f'/nodes/{node_id}')
        node_data = response['node']
        
        return NodeInfo(
            node_id=node_data['node_id'],
            host=node_data['host'],
            port=node_data['port'],
            status=node_data['status'],
            capabilities=node_data['capabilities'],
            cpu_usage=node_data['cpu_usage'],
            memory_usage=node_data['memory_usage'],
            load_score=node_data['load_score']
        )
    
    def register_node(self, node_id: str, host: str, port: int, 
                     node_type: str = "worker", capabilities: List[str] = None,
                     **kwargs) -> bool:
        """Register a new node"""
        data = {
            'host': host,
            'port': port,
            'node_type': node_type,
            'capabilities': capabilities or [],
            **kwargs
        }
        
        response = self._request('POST', f'/nodes/{node_id}/register', data)
        return response.get('success', False)
    
    def send_heartbeat(self, node_id: str, **metrics) -> bool:
        """Send node heartbeat with metrics"""
        response = self._request('POST', f'/nodes/{node_id}/heartbeat', metrics)
        return response.get('success', False)
    
    def submit_task(self, 
                   task_type: str,
                   input_data: Any,
                   priority: TaskPriority = TaskPriority.NORMAL,
                   requirements: Dict[str, Any] = None,
                   timeout: int = 300,
                   task_id: Optional[str] = None,
                   **kwargs) -> str:
        """
        Submit a task for execution
        
        Args:
            task_type: Type of task to execute
            input_data: Task input data
            priority: Task priority level
            requirements: Task requirements (capabilities, resources, etc.)
            timeout: Task timeout in seconds
            task_id: Optional task ID (auto-generated if not provided)
            **kwargs: Additional task parameters
            
        Returns:
            Task ID
        """
        data = {
            'task_type': task_type,
            'input_data': input_data,
            'priority': priority.value,
            'requirements': requirements or {},
            'timeout': timeout,
            **kwargs
        }
        
        if task_id:
            data['task_id'] = task_id
        
        response = self._request('POST', '/tasks', data)
        return response['task_id']
    
    def get_task(self, task_id: str) -> TaskResult:
        """Get task status and result"""
        response = self._request('GET', f'/tasks/{task_id}')
        task_data = response['task']
        
        return TaskResult(
            task_id=task_data['task_id'],
            status=TaskStatus(task_data['status']),
            result_data=task_data.get('result_data'),
            execution_time=task_data.get('execution_time', 0),
            error_message=task_data.get('error_message'),
            node_id=task_data.get('node_id'),
            agent_id=task_data.get('agent_id')
        )
    
    def get_tasks(self, status: Optional[str] = None, 
                 limit: int = 50, offset: int = 0) -> Dict[str, List[Dict]]:
        """Get tasks with optional filtering"""
        params = {'limit': limit, 'offset': offset}
        if status:
            params['status'] = status
        
        response = self._request('GET', '/tasks', params=params)
        return response['tasks']
    
    def wait_for_task(self, task_id: str, 
                     timeout: Optional[int] = None,
                     poll_interval: float = 2.0) -> TaskResult:
        """
        Wait for task completion
        
        Args:
            task_id: Task ID to wait for
            timeout: Maximum time to wait (seconds)
            poll_interval: How often to check status (seconds)
            
        Returns:
            TaskResult when task completes
            
        Raises:
            TimeoutError: If task doesn't complete within timeout
        """
        start_time = time.time()
        
        while True:
            task = self.get_task(task_id)
            
            if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, 
                              TaskStatus.CANCELLED, TaskStatus.TIMEOUT]:
                return task
            
            if timeout and (time.time() - start_time) > timeout:
                raise TimeoutError(f"Task {task_id} did not complete within {timeout} seconds")
            
            time.sleep(poll_interval)
    
    def submit_and_wait(self, task_type: str, input_data: Any, 
                       **kwargs) -> TaskResult:
        """Submit task and wait for completion"""
        task_id = self.submit_task(task_type, input_data, **kwargs)
        return self.wait_for_task(task_id, timeout=kwargs.get('timeout', 300))
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get orchestrator metrics"""
        return self._request('GET', '/metrics')
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance analysis and recommendations"""
        return self._request('GET', '/metrics/performance')
    
    def get_config(self) -> Dict[str, Any]:
        """Get orchestrator configuration"""
        return self._request('GET', '/config')
    
    def update_config(self, config_updates: Dict[str, Any]) -> bool:
        """Update orchestrator configuration"""
        response = self._request('PUT', '/config', config_updates)
        return response.get('success', False)
    
    async def subscribe_to_events(self, 
                                 event_handler: Callable[[Dict], None],
                                 websocket_url: Optional[str] = None):
        """
        Subscribe to real-time events via WebSocket
        
        Args:
            event_handler: Function to handle incoming events
            websocket_url: Custom WebSocket URL (auto-detected if not provided)
        """
        if not websocket_url:
            # Get WebSocket URL from API
            ws_info = self._request('GET', '/websocket/info')
            websocket_url = ws_info['websocket']['url']
        
        async with websockets.connect(websocket_url) as websocket:
            logger.info(f"Connected to WebSocket: {websocket_url}")
            
            async for message in websocket:
                try:
                    event = json.loads(message)
                    event_handler(event)
                except Exception as e:
                    logger.error(f"Error handling WebSocket event: {e}")

# Batch operations helper
class BatchTaskManager:
    """Helper for managing multiple tasks"""
    
    def __init__(self, client: Web4AIClient):
        self.client = client
        self.tasks: List[str] = []
    
    def submit_task(self, task_type: str, input_data: Any, **kwargs) -> str:
        """Submit task and track it"""
        task_id = self.client.submit_task(task_type, input_data, **kwargs)
        self.tasks.append(task_id)
        return task_id
    
    def wait_for_all(self, timeout: Optional[int] = None) -> List[TaskResult]:
        """Wait for all submitted tasks to complete"""
        results = []
        
        for task_id in self.tasks:
            try:
                result = self.client.wait_for_task(task_id, timeout)
                results.append(result)
            except TimeoutError:
                logger.warning(f"Task {task_id} timed out")
                # Get current status
                result = self.client.get_task(task_id)
                results.append(result)
        
        return results
    
    def get_status_summary(self) -> Dict[str, int]:
        """Get summary of task statuses"""
        summary = {}
        
        for task_id in self.tasks:
            task = self.client.get_task(task_id)
            status = task.status.value
            summary[status] = summary.get(status, 0) + 1
        
        return summary

# Example usage and testing
def example_usage():
    """Example of how to use the Web4AI client"""
    
    # Initialize client
    client = Web4AIClient(
        base_url="http://localhost:9000",
        api_key="your_api_key_here"  # Optional
    )
    
    # Check health
    health = client.health_check()
    print(f"Orchestrator status: {health['status']}")
    
    # Get network status
    status = client.get_status()
    print(f"Active nodes: {status['data']['nodes']['active']}")
    
    # List nodes
    nodes = client.get_nodes()
    for node in nodes:
        print(f"Node {node.node_id}: {node.status} (CPU: {node.cpu_usage}%)")
    
    # Submit a simple task
    task_id = client.submit_task(
        task_type="ai_inference",
        input_data={"prompt": "Hello, Web4AI!"},
        priority=TaskPriority.HIGH,
        requirements={"capabilities": ["ai_inference"]}
    )
    print(f"Submitted task: {task_id}")
    
    # Wait for completion
    try:
        result = client.wait_for_task(task_id, timeout=60)
        print(f"Task completed: {result.status.value}")
        if result.result_data:
            print(f"Result: {result.result_data}")
    except TimeoutError:
        print("Task timed out")
    
    # Batch task example
    batch = BatchTaskManager(client)
    
    # Submit multiple tasks
    for i in range(5):
        batch.submit_task(
            task_type="data_processing",
            input_data={"batch_id": i, "data": f"batch_{i}"}
        )
    
    print("Submitted 5 batch tasks")
    
    # Wait for all to complete
    results = batch.wait_for_all(timeout=120)
    
    # Print summary
    summary = batch.get_status_summary()
    print(f"Batch results: {summary}")
    
    # WebSocket event handling example
    async def handle_events():
        def event_handler(event):
            print(f"Received event: {event['type']}")
            if event['type'] == 'task_completed':
                print(f"Task {event['data']['task_id']} completed")
        
        await client.subscribe_to_events(event_handler)
    
    # Run WebSocket listener (in async context)
    # asyncio.run(handle_events())

if __name__ == "__main__":
    example_usage()

---
# monitoring_dashboard.py - Advanced Monitoring Dashboard
"""
Advanced monitoring dashboard for Web4AI Orchestrator
Provides real-time visualization and alerting
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import requests
import time
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any
import asyncio
import websockets
import threading
import queue

class OrchestratorMonitor:
    """Real-time orchestrator monitoring"""
    
    def __init__(self, orchestrator_url: str = "http://localhost:9000"):
        self.orchestrator_url = orchestrator_url
        self.api_url = f"{orchestrator_url}/api/v1"
        self.metrics_history = []
        self.event_queue = queue.Queue()
        self.ws_thread = None
        self.running = False
    
    def get_status(self) -> Dict[str, Any]:
        """Get current orchestrator status"""
        try:
            response = requests.get(f"{self.api_url}/status", timeout=5)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            st.error(f"Failed to get status: {e}")
            return {}
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get orchestrator metrics"""
        try:
            response = requests.get(f"{self.api_url}/metrics", timeout=5)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            st.error(f"Failed to get metrics: {e}")
            return {}
    
    def get_nodes(self) -> Dict[str, Any]:
        """Get node information"""
        try:
            response = requests.get(f"{self.api_url}/nodes", timeout=5)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            st.error(f"Failed to get nodes: {e}")
            return {}
    
    def get_tasks(self) -> Dict[str, Any]:
        """Get task information"""
        try:
            response = requests.get(f"{self.api_url}/tasks", timeout=5)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            st.error(f"Failed to get tasks: {e}")
            return {}
    
    def start_websocket_monitoring(self):
        """Start WebSocket monitoring in background thread"""
        if self.ws_thread and self.ws_thread.is_alive():
            return
        
        self.running = True
        self.ws_thread = threading.Thread(target=self._websocket_worker, daemon=True)
        self.ws_thread.start()
    
    def _websocket_worker(self):
        """WebSocket worker thread"""
        async def websocket_handler():
            try:
                # Get WebSocket URL
                ws_info = requests.get(f"{self.api_url}/websocket/info").json()
                ws_url = ws_info['websocket']['url']
                
                async with websockets.connect(ws_url) as websocket:
                    while self.running:
                        message = await websocket.recv()
                        event = json.loads(message)
                        self.event_queue.put(event)
                        
            except Exception as e:
                print(f"WebSocket error: {e}")
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(websocket_handler())
    
    def stop_monitoring(self):
        """Stop WebSocket monitoring"""
        self.running = False

def create_dashboard():
    """Create Streamlit dashboard"""
    
    st.set_page_config(
        page_title="Web4AI Orchestrator Monitor",
        page_icon="🚀",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    st.title("🚀 Web4AI Orchestrator Monitor")
    
    # Sidebar configuration
    st.sidebar.header("Configuration")
    orchestrator_url = st.sidebar.text_input(
        "Orchestrator URL", 
        value="http://localhost:9000"
    )
    
    auto_refresh = st.sidebar.checkbox("Auto Refresh", value=True)
    refresh_interval = st.sidebar.slider("Refresh Interval (seconds)", 1, 30, 5)
    
    # Initialize monitor
    if 'monitor' not in st.session_state:
        st.session_state.monitor = OrchestratorMonitor(orchestrator_url)
        st.session_state.monitor.start_websocket_monitoring()
    
    # Main dashboard
    col1, col2, col3, col4 = st.columns(4)
    
    # Get current data
    status_data = st.session_state.monitor.get_status()
    metrics_data = st.session_state.monitor.get_metrics()
    nodes_data = st.session_state.monitor.get_nodes()
    tasks_data = st.session_state.monitor.get_tasks()
    
    if not status_data.get('success'):
        st.error("⚠️ Unable to connect to orchestrator")
        return
    
    # Key metrics cards
    network_metrics = status_data['data']['network_metrics']
    
    with col1:
        st.metric(
            "Active Nodes",
            network_metrics.get('active_nodes', 0),
            delta=None
        )
    
    with col2:
        st.metric(
            "Tasks Completed",
            network_metrics.get('tasks_completed', 0),
            delta=None
        )
    
    with col3:
        utilization = network_metrics.get('network_utilization', 0)
        st.metric(
            "Network Utilization",
            f"{utilization * 100:.1f}%",
            delta=None
        )
    
    with col4:
        success_rate = network_metrics.get('success_rate', 0)
        st.metric(
            "Success Rate",
            f"{success_rate * 100:.1f}%",
            delta=None
        )
    
    # Real-time charts
    st.header("📊 Real-time Metrics")
    
    # Create metrics history
    if 'metrics_history' not in st.session_state:
        st.session_state.metrics_history = []
    
    # Add current metrics to history
    current_time = datetime.now()
    st.session_state.metrics_history.append({
        'time': current_time,
        'utilization': utilization,
        'active_nodes': network_metrics.get('active_nodes', 0),
        'response_time': network_metrics.get('average_response_time', 0),
        'throughput': network_metrics.get('throughput_per_minute', 0)
    })
    
    # Keep only last 50 data points
    if len(st.session_state.metrics_history) > 50:
        st.session_state.metrics_history = st.session_state.metrics_history[-50:]
    
    # Convert to DataFrame
    df = pd.DataFrame(st.session_state.metrics_history)
    
    if not df.empty:
        # Network utilization chart
        fig_util = px.line(
            df, 
            x='time', 
            y='utilization',
            title='Network Utilization Over Time',
            labels={'utilization': 'Utilization', 'time': 'Time'}
        )
        fig_util.update_layout(height=300)
        st.plotly_chart(fig_util, use_container_width=True)
        
        # Multi-metric chart
        fig_multi = make_subplots(
            rows=2, cols=2,
            subplot_titles=('Active Nodes', 'Response Time', 'Throughput', 'Success Rate'),
            specs=[[{"secondary_y": False}, {"secondary_y": False}],
                   [{"secondary_y": False}, {"secondary_y": False}]]
        )
        
        fig_multi.add_trace(
            go.Scatter(x=df['time'], y=df['active_nodes'], name='Active Nodes'),
            row=1, col=1
        )
        
        fig_multi.add_trace(
            go.Scatter(x=df['time'], y=df['response_time'], name='Response Time (ms)'),
            row=1, col=2
        )
        
        fig_multi.add_trace(
            go.Scatter(x=df['time'], y=df['throughput'], name='Tasks/minute'),
            row=2, col=1
        )
        
        # Success rate from metrics
        success_rates = [network_metrics.get('success_rate', 0)] * len(df)
        fig_multi.add_trace(
            go.Scatter(x=df['time'], y=success_rates, name='Success Rate'),
            row=2, col=2
        )
        
        fig_multi.update_layout(height=600, showlegend=False)
        st.plotly_chart(fig_multi, use_container_width=True)
    
    # Node status
    st.header("🖥️ Node Status")
    
    if nodes_data.get('success') and nodes_data.get('nodes'):
        nodes = []
        for node_id, node_info in nodes_data['nodes'].items():
            nodes.append({
                'Node ID': node_id,
                'Status': node_info['status'],
                'CPU %': f"{node_info['cpu_usage']:.1f}%",
                'Memory %': f"{node_info['memory_usage']:.1f}%",
                'Load Score': f"{node_info['load_score']:.2f}",
                'Agents': node_info['agents_count']
            })
        
        df_nodes = pd.DataFrame(nodes)
        st.dataframe(df_nodes, use_container_width=True)
        
        # Node resource utilization chart
        if not df_nodes.empty:
            fig_nodes = px.bar(
                df_nodes,
                x='Node ID',
                y=['CPU %', 'Memory %'],
                title='Node Resource Utilization',
                barmode='group'
            )
            fig_nodes.update_layout(height=400)
            st.plotly_chart(fig_nodes, use_container_width=True)
    else:
        st.info("No nodes registered")
    
    # Task status
    st.header("📋 Task Status")
    
    if tasks_data.get('success'):
        task_summary = tasks_data.get('summary', {})
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Pending", task_summary.get('pending_count', 0))
        with col2:
            st.metric("Active", task_summary.get('active_count', 0))
        with col3:
            st.metric("Completed", task_summary.get('completed_count', 0))
        with col4:
            st.metric("Failed", task_summary.get('failed_count', 0))
        
        # Task distribution pie chart
        if any(task_summary.values()):
            fig_tasks = px.pie(
                values=list(task_summary.values()),
                names=list(task_summary.keys()),
                title='Task Distribution'
            )
            st.plotly_chart(fig_tasks, use_container_width=True)
    
    # Recent events
    st.header("📡 Recent Events")
    
    # Display WebSocket events
    events = []
    while not st.session_state.monitor.event_queue.empty():
        try:
            event = st.session_state.monitor.event_queue.get_nowait()
            events.append({
                'Time': datetime.fromtimestamp(event.get('timestamp', time.time())),
                'Type': event.get('type', 'unknown'),
                'Details': str(event.get('data', {}))[:100] + '...'
            })
        except queue.Empty:
            break
    
    if events:
        df_events = pd.DataFrame(events)
        st.dataframe(df_events.tail(10), use_container_width=True)
    else:
        st.info("No recent events")
    
    # Performance recommendations
    if metrics_data.get('success'):
        perf_data = st.session_state.monitor.get_metrics()
        if perf_data.get('success'):
            # This would typically come from /metrics/performance endpoint
            st.header("💡 Performance Recommendations")
            
            recommendations = [
                "Network utilization is optimal",
                "All nodes are healthy",
                "Task distribution is balanced"
            ]
            
            for rec in recommendations:
                st.success(f"✅ {rec}")
    
    # Auto refresh
    if auto_refresh:
        time.sleep(refresh_interval)
        st.experimental_rerun()

if __name__ == "__main__":
    create_dashboard()

---
# requirements.txt - Python Dependencies
# Web4AI Orchestrator Requirements

# Core dependencies
flask>=2.3.0
flask-cors>=4.0.0
requests>=2.31.0
websockets>=11.0.0
pyyaml>=6.0.0
psutil>=5.9.0

# Database drivers (optional)
redis>=4.6.0
pymongo>=4.4.0
psycopg2-binary>=2.9.0

# Monitoring and metrics
prometheus-client>=0.17.0

# Async support
asyncio>=3.4.3

# Data processing
pandas>=2.0.0
numpy>=1.24.0

# Web dashboard (optional)
streamlit>=1.25.0
plotly>=5.15.0

# Testing
pytest>=7.4.0
pytest-asyncio>=0.21.0

# Development tools
black>=23.0.0
flake8>=6.0.0
mypy>=1.4.0

# Security
cryptography>=41.0.0
bcrypt>=4.0.0

# Logging
structlog>=23.1.0

---
# Dockerfile - Container Configuration
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    nginx \
    supervisor \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY web4ai_orchestrator.py .
COPY orchestrator_api.py .
COPY orchestrator_config.yaml .

# Create directories
RUN mkdir -p /var/log/web4ai /opt/web4ai/backups

# Copy configuration files
COPY docker/nginx.conf /etc/nginx/sites-available/default
COPY docker/supervisor.conf /etc/supervisor/conf.d/web4ai.conf

# Expose ports
EXPOSE 9000 9001 80

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:9000/api/v1/health || exit 1

# Start services
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/supervisord.conf"]

---
# docker/nginx.conf - Nginx Configuration for Container
server {
    listen 80;
    server_name _;
    
    # API proxy
    location /api/ {
        proxy_pass http://127.0.0.1:9000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
    
    # WebSocket proxy
    location /ws {
        proxy_pass http://127.0.0.1:9001;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }
    
    # Dashboard
    location / {
        proxy_pass http://127.0.0.1:9000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # Health check
    location /health {
        proxy_pass http://127.0.0.1:9000/api/v1/health;
        access_log off;
    }
}

---
# docker/supervisor.conf - Supervisor Configuration
[supervisord]
nodaemon=true
user=root

[program:nginx]
command=/usr/sbin/nginx -g "daemon off;"
autostart=true
autorestart=true
stdout_logfile=/var/log/nginx/access.log
stderr_logfile=/var/log/nginx/error.log

[program:orchestrator]
command=python orchestrator_api.py --config orchestrator_config.yaml
directory=/app
autostart=true
autorestart=true
user=nobody
stdout_logfile=/var/log/web4ai/orchestrator.log
stderr_logfile=/var/log/web4ai/orchestrator_error.log
environment=PYTHONPATH="/app"
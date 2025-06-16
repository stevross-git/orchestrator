# Web4AI Network Orchestrator - Deployment & Integration Guide

## 🏗️ Architecture Overview

The Web4AI Network Orchestrator provides a **3-tier hierarchical architecture**:

```
🌐 ORCHESTRATOR TIER (Global Control)
    ├── Network topology management
    ├── Global load balancing
    ├── Cross-node task scheduling
    └── Performance optimization

📡 NODE MANAGER TIER (Regional Control) 
    ├── Multi-agent coordination
    ├── Local resource management
    ├── Agent lifecycle management
    └── Regional load balancing

🤖 AGENT TIER (Task Execution)
    ├── AI inference & training
    ├── Blockchain operations
    ├── Specialized workloads
    └── Real-time task execution
```

## 🚀 Quick Start

### 1. Installation

```bash
# Clone the orchestrator components
git clone https://github.com/your-repo/web4ai-orchestrator
cd web4ai-orchestrator

# Install dependencies
pip install -r requirements.txt

# Generate default configuration
python orchestrator_api.py --generate-config
```

### 2. Configuration

Edit `orchestrator_config.yaml`:

```yaml
orchestrator:
  id: "web4ai_main_orchestrator"
  port: 9000
  host: "0.0.0.0"
  heartbeat_interval: 30
  task_timeout: 300
  auto_discovery: true

network:
  discovery_endpoints:
    - "http://localhost:8080"    # Node 1
    - "http://localhost:8081"    # Node 2
    - "http://localhost:8082"    # Node 3
  max_nodes: 100
  min_nodes: 1
  
performance:
  cpu_threshold: 80
  memory_threshold: 85
  optimization_enabled: true
```

### 3. Launch Orchestrator

```bash
# Start the orchestrator API
python orchestrator_api.py --config orchestrator_config.yaml

# Or with custom settings
python orchestrator_api.py --host 0.0.0.0 --port 9000 --debug
```

## 🔧 Integration with Existing Web4AI Infrastructure

### Integrating with Your Node Manager

Update your existing node manager to register with the orchestrator:

```python
# In your enhanced_node/node_server.py
import requests
import json

class NodeManager:
    def __init__(self):
        self.orchestrator_url = "http://localhost:9000"
        self.node_id = "your_node_id"
        
    def register_with_orchestrator(self):
        """Register this node with the orchestrator"""
        registration_data = {
            'node_id': self.node_id,
            'host': self.host,
            'port': self.port,
            'capabilities': self.get_capabilities(),
            'agents': self.get_agent_list()
        }
        
        try:
            response = requests.post(
                f"{self.orchestrator_url}/api/v1/nodes/{self.node_id}/register",
                json=registration_data,
                timeout=10
            )
            
            if response.status_code == 200:
                print(f"✅ Registered with orchestrator: {self.node_id}")
                return True
            else:
                print(f"❌ Registration failed: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Registration error: {e}")
            return False
    
    def send_heartbeat_to_orchestrator(self):
        """Send heartbeat to orchestrator"""
        heartbeat_data = {
            'node_id': self.node_id,
            'status': 'active',
            'cpu_usage': self.get_cpu_usage(),
            'memory_usage': self.get_memory_usage(),
            'agents_status': self.get_agents_status(),
            'load_score': self.calculate_load_score()
        }
        
        try:
            response = requests.post(
                f"{self.orchestrator_url}/api/v1/nodes/{self.node_id}/heartbeat",
                json=heartbeat_data,
                timeout=5
            )
            return response.status_code == 200
        except:
            return False
```

### Integrating with Your Ultimate Agent

Update your agent to accept orchestrator tasks:

```python
# In your ultimate_agent/core/agent.py
from flask import Flask, request, jsonify

class UltimateAgent:
    def __init__(self):
        self.app = Flask(__name__)
        self.setup_orchestrator_endpoints()
    
    def setup_orchestrator_endpoints(self):
        """Setup endpoints for orchestrator communication"""
        
        @self.app.route('/api/v4/tasks/execute', methods=['POST'])
        def execute_orchestrator_task():
            """Execute task from orchestrator"""
            try:
                task_data = request.get_json()
                
                task_id = task_data['task_id']
                task_type = task_data['task_type']
                input_data = task_data['input_data']
                requirements = task_data.get('requirements', {})
                
                # Route to appropriate handler
                if task_type == 'ai_inference':
                    result = self.handle_ai_inference(input_data)
                elif task_type == 'blockchain_transaction':
                    result = self.handle_blockchain_task(input_data)
                elif task_type == 'distributed_training':
                    result = self.handle_training_task(input_data)
                else:
                    raise ValueError(f"Unknown task type: {task_type}")
                
                return jsonify({
                    'success': True,
                    'task_id': task_id,
                    'result': result,
                    'completed_at': time.time()
                })
                
            except Exception as e:
                return jsonify({
                    'success': False,
                    'task_id': task_data.get('task_id', 'unknown'),
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/v4/orchestrator/status', methods=['GET'])
        def get_orchestrator_status():
            """Get agent status for orchestrator"""
            return jsonify({
                'agent_id': self.agent_id,
                'status': 'active',
                'capabilities': self.capabilities,
                'current_tasks': len(self.active_tasks),
                'load_score': self.calculate_load(),
                'specialized_models': self.get_available_models()
            })
```

## 📊 API Usage Examples

### Submit AI Inference Task

```bash
curl -X POST http://localhost:9000/api/v1/tasks \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "task_type": "ai_inference",
    "priority": 2,
    "input_data": {
      "model": "transformer",
      "prompt": "Analyze this data",
      "parameters": {"temperature": 0.7}
    },
    "requirements": {
      "capabilities": ["ai_inference"],
      "min_memory": 20,
      "min_cpu": 10
    },
    "timeout": 60.0
  }'
```

### Submit Distributed Training Task

```bash
curl -X POST http://localhost:9000/api/v1/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "task_type": "distributed_training",
    "priority": 1,
    "input_data": {
      "model_type": "neural_network",
      "dataset": "large_dataset",
      "epochs": 100
    },
    "requirements": {
      "capabilities": ["ai_training", "distributed"],
      "min_memory": 50,
      "redundancy": 3
    },
    "timeout": 3600.0
  }'
```

### Get Network Status

```bash
curl http://localhost:9000/api/v1/status
```

### Monitor Performance

```bash
# Get basic metrics
curl http://localhost:9000/api/v1/metrics

# Get detailed performance metrics  
curl http://localhost:9000/api/v1/metrics/performance
```

## 🛠️ Advanced Configuration

### Load Balancing Strategies

```yaml
network:
  load_balance_algorithm: "weighted_round_robin"  # Options:
  # - "round_robin"          # Simple round robin
  # - "weighted_round_robin" # Based on node capacity
  # - "least_connections"    # Route to least busy node
  # - "resource_aware"       # Consider CPU/memory/GPU
  # - "latency_optimized"    # Minimize network latency
```

### Auto-Scaling Configuration

```yaml
performance:
  auto_scaling:
    enabled: true
    scale_up_threshold: 0.8      # Scale up when utilization > 80%
    scale_down_threshold: 0.2    # Scale down when utilization < 20%
    min_nodes: 2
    max_nodes: 50
    cooldown_period: 300         # Wait 5 minutes between scaling events
```

### Security Configuration

```yaml
security:
  api_key_required: true
  rate_limiting: true
  max_requests_per_minute: 1000
  encryption_enabled: true
  audit_logging: true
  allowed_ips:
    - "192.168.1.0/24"
    - "10.0.0.0/8"
```

## 📈 Monitoring & Observability

### Health Checks

```bash
# Basic health check
curl http://localhost:9000/api/v1/health

# Detailed status with metrics
curl http://localhost:9000/api/v1/status

# Node-specific health
curl http://localhost:9000/api/v1/nodes/node_id_123
```

### Performance Monitoring

The orchestrator provides comprehensive metrics:

- **Network Utilization**: Overall system load
- **Task Throughput**: Tasks completed per minute  
- **Success Rate**: Percentage of successful tasks
- **Latency Metrics**: Average response times
- **Resource Usage**: CPU, memory, GPU across nodes
- **Fault Detection**: Node failures and recovery

### Grafana Dashboard (Optional)

Create a Grafana dashboard to visualize metrics:

```json
{
  "dashboard": {
    "title": "Web4AI Network Orchestrator",
    "panels": [
      {
        "title": "Network Utilization",
        "type": "graph",
        "targets": [
          {
            "expr": "web4ai_network_utilization",
            "legendFormat": "Utilization %"
          }
        ]
      },
      {
        "title": "Active Nodes",
        "type": "stat",
        "targets": [
          {
            "expr": "web4ai_active_nodes",
            "legendFormat": "Nodes"
          }
        ]
      }
    ]
  }
}
```

### Streamlit Dashboard

For an interactive dashboard with built-in controls, run the Streamlit app:

```bash
streamlit run advanced_dashboard.py
```

This dashboard displays real-time metrics, node status, and provides buttons to
start, stop, or restart the orchestrator.

## 🔄 Task Lifecycle Management

### Task States

1. **Submitted** → Task received by orchestrator
2. **Queued** → Waiting for suitable node assignment  
3. **Scheduled** → Assigned to node(s)
4. **Running** → Executing on agent(s)
5. **Completed** → Successfully finished
6. **Failed** → Task failed (with retry logic)

### Retry Logic

```python
# Tasks are automatically retried based on:
- Network failures (connection timeouts)
- Node failures (heartbeat loss)  
- Agent failures (process crashes)
- Resource constraints (insufficient memory/CPU)

# Retry strategy:
max_retries: 3
retry_delay: exponential_backoff  # 1s, 2s, 4s, 8s...
retry_conditions: ["network_error", "node_failure", "timeout"]
```

## 🚨 Fault Tolerance

### Node Failure Handling

1. **Detection**: Missed heartbeats trigger fault detection
2. **Isolation**: Failed node marked as offline
3. **Recovery**: Tasks redistributed to healthy nodes
4. **Healing**: Automatic reconnection when node recovers

### Split-Brain Prevention

```yaml
consensus:
  enabled: true
  quorum_size: 3              # Minimum nodes for consensus
  leader_election: true       # Use leader election
  partition_tolerance: true   # Handle network partitions
```

## 📦 Deployment Options

### Docker Deployment

```dockerfile
# Dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 9000
CMD ["python", "orchestrator_api.py", "--host", "0.0.0.0", "--port", "9000"]
```

```yaml
# docker-compose.yml
version: '3.8'
services:
  orchestrator:
    build: .
    ports:
      - "9000:9000"
    environment:
      - ORCHESTRATOR_CONFIG=/app/config/orchestrator_config.yaml
    volumes:
      - ./config:/app/config
      - ./data:/app/data
    networks:
      - web4ai-network

  node1:
    image: web4ai/ultimate-agent:latest
    ports:
      - "8080:8080"
    environment:
      - NODE_ID=node1
      - ORCHESTRATOR_URL=http://orchestrator:9000
    networks:
      - web4ai-network

networks:
  web4ai-network:
    driver: bridge
```

### Kubernetes Deployment

```yaml
# orchestrator-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web4ai-orchestrator
spec:
  replicas: 1
  selector:
    matchLabels:
      app: web4ai-orchestrator
  template:
    metadata:
      labels:
        app: web4ai-orchestrator
    spec:
      containers:
      - name: orchestrator
        image: web4ai/orchestrator:latest
        ports:
        - containerPort: 9000
        env:
        - name: ORCHESTRATOR_CONFIG
          value: "/app/config/orchestrator_config.yaml"
        volumeMounts:
        - name: config
          mountPath: /app/config
      volumes:
      - name: config
        configMap:
          name: orchestrator-config

---
apiVersion: v1
kind: Service
metadata:
  name: orchestrator-service
spec:
  selector:
    app: web4ai-orchestrator
  ports:
  - protocol: TCP
    port: 9000
    targetPort: 9000
  type: LoadBalancer
```

## 🧪 Testing

### Unit Tests

```python
# test_orchestrator.py
import pytest
import asyncio
from web4ai_orchestrator import Web4AIOrchestrator, TaskRequest, TaskPriority

@pytest.mark.asyncio
async def test_task_submission():
    orchestrator = Web4AIOrchestrator("test_orch")
    
    task = TaskRequest(
        task_type="test_task",
        priority=TaskPriority.NORMAL,
        requirements={},
        input_data={"test": "data"},
        timeout=30.0
    )
    
    task_id = await orchestrator.submit_task(task)
    assert task_id is not None
    assert len(orchestrator.pending_tasks) == 1

@pytest.mark.asyncio  
async def test_node_registration():
    orchestrator = Web4AIOrchestrator("test_orch")
    
    # Mock node registration
    await orchestrator._register_node_from_endpoint("http://localhost:8080")
    
    assert len(orchestrator.nodes) > 0
```

### Integration Tests

```bash
# Run integration test suite
python -m pytest tests/ -v

# Test specific orchestrator functionality
python -m pytest tests/test_orchestrator.py -v

# Test API endpoints
python -m pytest tests/test_api.py -v
```

## 🎯 Best Practices

### Performance Optimization

1. **Node Placement**: Distribute nodes across availability zones
2. **Task Batching**: Group similar tasks for efficiency
3. **Connection Pooling**: Reuse HTTP connections between nodes
4. **Caching**: Cache frequent task results and node metadata
5. **Compression**: Use compression for large task payloads

### Security Hardening

1. **API Authentication**: Use strong API keys or JWT tokens
2. **Network Encryption**: Enable TLS for all communications
3. **Input Validation**: Validate all task inputs and parameters
4. **Rate Limiting**: Prevent API abuse and DoS attacks
5. **Audit Logging**: Log all orchestrator operations

### Monitoring Best Practices

1. **Alert Thresholds**: Set up alerts for critical metrics
2. **Log Aggregation**: Centralize logs from all components
3. **Health Dashboards**: Create real-time status dashboards
4. **Capacity Planning**: Monitor trends for scaling decisions
5. **SLA Tracking**: Track task completion times and success rates

## 🚀 Next Steps

1. **Deploy** the orchestrator in your environment
2. **Integrate** with your existing web4ai nodes
3. **Configure** monitoring and alerting
4. **Test** with your specific workloads
5. **Scale** based on performance requirements

For support and advanced features, check the [Web4AI documentation](https://github.com/your-repo/web4ai-docs) or join our [Discord community](https://discord.gg/web4ai).

---

**Happy orchestrating! 🎵🤖**
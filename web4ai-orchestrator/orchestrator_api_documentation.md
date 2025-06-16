# Web4AI Orchestrator API Documentation

## 📋 Overview

The Web4AI Orchestrator provides a comprehensive RESTful API for managing distributed AI networks. This API enables you to register nodes, submit tasks, monitor performance, and control the entire network topology.

### Base URL
```
http://localhost:9000/api/v1
```

### Response Format
All API responses follow this standard format:
```json
{
  "success": true|false,
  "data": {...},           // Present on successful requests
  "error": "string",       // Present on failed requests  
  "timestamp": "ISO8601",  // Optional timestamp
  "message": "string"      // Optional message
}
```

---

## 🔐 Authentication

Currently, the orchestrator supports optional API key authentication:

```bash
# If authentication is enabled
curl -H "Authorization: Bearer YOUR_API_KEY" http://localhost:9000/api/v1/status
```

---

## 🩺 Health & Status Endpoints

### GET /health
Health check endpoint - always responds quickly

**Response:**
```json
{
  "status": "healthy",
  "orchestrator_id": "orch_abc123",
  "timestamp": "2025-06-16T10:30:00Z",
  "version": "1.0.0",
  "system": {
    "cpu_usage": 25.4,
    "memory_usage": 68.2,
    "disk_usage": 45.1,
    "uptime": "2 days, 3:45:23"
  }
}
```

**Example:**
```bash
curl http://localhost:9000/api/v1/health
```

### GET /status
Comprehensive orchestrator status including network topology

**Response:**
```json
{
  "success": true,
  "data": {
    "orchestrator_id": "orch_abc123",
    "timestamp": 1718542200.123,
    "uptime": 185723.45,
    "network_metrics": {
      "total_nodes": 5,
      "active_nodes": 4,
      "total_agents": 12,
      "tasks_completed": 1205,
      "tasks_failed": 23,
      "average_response_time": 245.6,
      "network_utilization": 0.67,
      "throughput_per_minute": 45.2,
      "success_rate": 0.981
    },
    "nodes": {
      "total": 5,
      "active": 4,
      "by_status": {
        "active": 4,
        "offline": 1,
        "maintenance": 0,
        "degraded": 0,
        "error": 0
      }
    },
    "agents": {
      "total": 12,
      "by_node": {
        "node_001": 3,
        "node_002": 4,
        "node_003": 2,
        "node_004": 3
      }
    },
    "tasks": {
      "pending": 5,
      "active": 12,
      "completed": 1205,
      "failed": 23
    },
    "performance": {
      "avg_cpu_usage": 34.2,
      "avg_memory_usage": 56.7,
      "avg_network_latency": 12.4,
      "network_utilization": 0.67
    }
  },
  "api_stats": {
    "requests_total": 5642,
    "requests_success": 5598,
    "requests_error": 44,
    "start_time": "2025-06-14T08:15:00Z"
  }
}
```

**Example:**
```bash
curl http://localhost:9000/api/v1/status
```

---

## 🖥️ Node Management Endpoints

### GET /nodes
List all registered nodes in the network

**Response:**
```json
{
  "success": true,
  "nodes": {
    "enhanced-node-abc123": {
      "node_id": "enhanced-node-abc123",
      "host": "192.168.1.100",
      "port": 8090,
      "node_type": "enhanced_node",
      "status": "active",
      "capabilities": [
        "task_execution",
        "remote_control",
        "health_monitoring",
        "gpu_processing"
      ],
      "agents_count": 3,
      "cpu_usage": 45.2,
      "memory_usage": 62.8,
      "gpu_usage": 23.1,
      "load_score": 0.52,
      "last_heartbeat": 1718542180.456,
      "version": "3.4.0-advanced-remote-control",
      "location": "datacenter-01",
      "uptime": 125643.2
    }
  },
  "total_nodes": 5,
  "active_nodes": 4
}
```

**Example:**
```bash
curl http://localhost:9000/api/v1/nodes
```

### GET /nodes/{node_id}
Get detailed information about a specific node

**Parameters:**
- `node_id` (path): Unique node identifier

**Response:**
```json
{
  "success": true,
  "node": {
    "node_id": "enhanced-node-abc123",
    "host": "192.168.1.100",
    "port": 8090,
    "node_type": "enhanced_node",
    "status": "active",
    "capabilities": ["task_execution", "remote_control"],
    "agents_count": 3,
    "cpu_usage": 45.2,
    "memory_usage": 62.8,
    "gpu_usage": 23.1,
    "load_score": 0.52,
    "reliability_score": 0.95,
    "last_heartbeat": 1718542180.456,
    "version": "3.4.0-advanced-remote-control",
    "location": "datacenter-01",
    "tasks_completed": 234,
    "tasks_failed": 5,
    "agents": [
      {
        "agent_id": "agent_001",
        "agent_type": "ai_inference",
        "status": "active",
        "capabilities": ["llm_inference", "image_processing"],
        "tasks_running": 2,
        "tasks_completed": 156,
        "efficiency_score": 0.92,
        "specialized_models": ["gpt-4", "dall-e"],
        "last_activity": 1718542170.123
      }
    ]
  }
}
```

**Example:**
```bash
curl http://localhost:9000/api/v1/nodes/enhanced-node-abc123
```

### POST /nodes/{node_id}/register
Register a new node in the network

**Parameters:**
- `node_id` (path): Unique node identifier

**Request Body:**
```json
{
  "host": "192.168.1.100",
  "port": 8090,
  "node_type": "enhanced_node",
  "capabilities": [
    "task_execution",
    "remote_control", 
    "health_monitoring",
    "gpu_processing"
  ],
  "agents_count": 3,
  "version": "3.4.0-advanced-remote-control",
  "location": "datacenter-01",
  "metadata": {
    "deployment_type": "docker",
    "environment": "production"
  },
  "agents": [
    {
      "agent_id": "agent_001",
      "agent_type": "ai_inference",
      "capabilities": ["llm_inference", "image_processing"],
      "specialized_models": ["gpt-4", "dall-e"]
    }
  ]
}
```

**Response:**
```json
{
  "success": true,
  "message": "Node enhanced-node-abc123 registered successfully",
  "node_id": "enhanced-node-abc123"
}
```

**Example:**
```bash
curl -X POST http://localhost:9000/api/v1/nodes/enhanced-node-abc123/register \
  -H "Content-Type: application/json" \
  -d '{
    "host": "192.168.1.100",
    "port": 8090,
    "node_type": "enhanced_node",
    "capabilities": ["task_execution", "remote_control"],
    "version": "3.4.0"
  }'
```

### POST /nodes/{node_id}/heartbeat
Update node heartbeat and status information

**Parameters:**
- `node_id` (path): Node identifier

**Request Body:**
```json
{
  "status": "active",
  "cpu_usage": 45.2,
  "memory_usage": 62.8,
  "gpu_usage": 23.1,
  "load_score": 0.52,
  "tasks_running": 3,
  "agents_status": {
    "total_agents": 3,
    "active_agents": 3,
    "agent_list": ["agent_001", "agent_002", "agent_003"]
  },
  "timestamp": "2025-06-16T10:30:00Z"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Heartbeat updated"
}
```

**Example:**
```bash
curl -X POST http://localhost:9000/api/v1/nodes/enhanced-node-abc123/heartbeat \
  -H "Content-Type: application/json" \
  -d '{
    "status": "active",
    "cpu_usage": 45.2,
    "memory_usage": 62.8,
    "load_score": 0.52
  }'
```

### PUT /nodes/{node_id}/status
Update node status

**Parameters:**
- `node_id` (path): Node identifier

**Request Body:**
```json
{
  "status": "maintenance"
}
```

**Possible Status Values:**
- `active` - Node is operational and accepting tasks
- `degraded` - Node is operational but with reduced capacity
- `maintenance` - Node is in maintenance mode
- `offline` - Node is offline
- `error` - Node has errors

**Response:**
```json
{
  "success": true,
  "message": "Node status updated to maintenance",
  "old_status": "active",
  "new_status": "maintenance"
}
```

**Example:**
```bash
curl -X PUT http://localhost:9000/api/v1/nodes/enhanced-node-abc123/status \
  -H "Content-Type: application/json" \
  -d '{"status": "maintenance"}'
```

### DELETE /nodes/{node_id}
Unregister a node from the network

**Parameters:**
- `node_id` (path): Node identifier

**Response:**
```json
{
  "success": true,
  "message": "Node enhanced-node-abc123 unregistered successfully"
}
```

**Example:**
```bash
curl -X DELETE http://localhost:9000/api/v1/nodes/enhanced-node-abc123
```

---

## 📋 Task Management Endpoints

### POST /tasks
Submit a new task for execution

**Request Body:**
```json
{
  "task_id": "task_abc123",           // Optional - auto-generated if not provided
  "task_type": "ai_inference",        // Required
  "priority": 2,                      // Optional - 1=CRITICAL, 2=HIGH, 3=NORMAL, 4=LOW, 5=BACKGROUND
  "requirements": {                   // Optional
    "capabilities": ["gpu_processing"],
    "min_cpu": 20,                   // Minimum CPU percentage available
    "min_memory": 1024,              // Minimum memory in MB
    "preferred_nodes": ["node_001"],  // Preferred node IDs
    "exclude_nodes": ["node_003"]     // Nodes to avoid
  },
  "input_data": {                     // Task-specific data
    "model": "gpt-4",
    "prompt": "Explain quantum computing",
    "max_tokens": 500
  },
  "timeout": 300,                     // Timeout in seconds (optional)
  "max_retries": 3,                   // Maximum retry attempts (optional)
  "deadline": 1718542800,             // Unix timestamp deadline (optional)
  "callback_url": "https://myapp.com/webhook/task_complete", // Optional
  "metadata": {                       // Optional metadata
    "user_id": "user_123",
    "session_id": "session_456"
  }
}
```

**Response:**
```json
{
  "success": true,
  "task_id": "task_abc123",
  "message": "Task submitted successfully"
}
```

**Example:**
```bash
curl -X POST http://localhost:9000/api/v1/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "task_type": "ai_inference",
    "priority": 2,
    "input_data": {
      "model": "gpt-4",
      "prompt": "Explain quantum computing"
    },
    "timeout": 300
  }'
```

### GET /tasks
List all tasks with their current status

**Query Parameters:**
- `status` (optional): Filter by status (pending, active, completed, failed)
- `limit` (optional): Limit number of results (default: 50)
- `offset` (optional): Offset for pagination (default: 0)

**Response:**
```json
{
  "success": true,
  "tasks": {
    "pending": [
      {
        "task_id": "task_pending_001",
        "task_type": "ai_inference",
        "priority": 2,
        "created_at": 1718542100.123,
        "timeout": 300
      }
    ],
    "active": [
      {
        "task_id": "task_active_001",
        "task_type": "data_processing",
        "priority": 1,
        "assigned_nodes": ["enhanced-node-abc123"],
        "created_at": 1718542050.456,
        "timeout": 600
      }
    ],
    "completed": [
      {
        "task_id": "task_completed_001",
        "status": "completed",
        "execution_time": 45.6,
        "node_id": "enhanced-node-abc123",
        "completed_at": 1718542000.789
      }
    ],
    "failed": [
      {
        "task_id": "task_failed_001",
        "status": "failed",
        "error_message": "Node became unavailable",
        "node_id": "enhanced-node-xyz789",
        "completed_at": 1718541950.123
      }
    ]
  },
  "summary": {
    "pending_count": 5,
    "active_count": 12,
    "completed_count": 1205,
    "failed_count": 23
  }
}
```

**Example:**
```bash
# Get all tasks
curl http://localhost:9000/api/v1/tasks

# Get only active tasks
curl "http://localhost:9000/api/v1/tasks?status=active"

# Get with pagination
curl "http://localhost:9000/api/v1/tasks?limit=20&offset=40"
```

### GET /tasks/{task_id}
Get detailed information about a specific task

**Parameters:**
- `task_id` (path): Task identifier

**Response:**
```json
{
  "success": true,
  "task": {
    "task_id": "task_abc123",
    "task_type": "ai_inference",
    "status": "completed",
    "priority": 2,
    "assigned_nodes": ["enhanced-node-abc123"],
    "created_at": 1718542000.123,
    "completed_at": 1718542045.678,
    "timeout": 300,
    "retry_count": 0,
    "execution_time": 45.555,
    "node_id": "enhanced-node-abc123",
    "agent_id": "agent_001",
    "requirements": {
      "capabilities": ["gpu_processing"],
      "min_cpu": 20,
      "min_memory": 1024
    },
    "metadata": {
      "user_id": "user_123",
      "session_id": "session_456"
    },
    "performance_metrics": {
      "cpu_usage": 67.2,
      "memory_usage": 1536,
      "gpu_usage": 89.1,
      "network_io": 245.6
    }
  }
}
```

**Example:**
```bash
curl http://localhost:9000/api/v1/tasks/task_abc123
```

---

## 📊 Metrics & Monitoring Endpoints

### GET /metrics
Get comprehensive orchestrator metrics

**Response:**
```json
{
  "success": true,
  "metrics": {
    "timestamp": "2025-06-16T10:30:00Z",
    "network": {
      "total_nodes": 5,
      "active_nodes": 4,
      "total_agents": 12,
      "tasks_completed": 1205,
      "tasks_failed": 23,
      "average_response_time": 245.6,
      "network_utilization": 0.67,
      "uptime": 185723.45,
      "throughput_per_minute": 45.2,
      "success_rate": 0.981
    },
    "nodes": {
      "total": 5,
      "active": 4,
      "avg_cpu_usage": 34.2,
      "avg_memory_usage": 56.7,
      "avg_load_score": 0.52
    },
    "tasks": {
      "pending": 5,
      "active": 12,
      "completed_total": 1205,
      "failed_total": 23,
      "success_rate": 0.981
    },
    "api": {
      "requests_total": 5642,
      "requests_success": 5598,
      "requests_error": 44,
      "start_time": "2025-06-14T08:15:00Z"
    },
    "load_balancer": {
      "algorithm": "weighted_round_robin",
      "node_weights": {
        "enhanced-node-abc123": 0.85,
        "enhanced-node-def456": 0.92
      }
    }
  }
}
```

**Example:**
```bash
curl http://localhost:9000/api/v1/metrics
```

### GET /metrics/performance
Get performance analysis and optimization recommendations

**Response:**
```json
{
  "success": true,
  "performance_analysis": {
    "timestamp": 1718542200.123,
    "network_utilization": 0.67,
    "avg_response_time": 245.6,
    "task_throughput": 45.2,
    "recommendations": [
      {
        "type": "load_rebalancing",
        "priority": "medium",
        "description": "High response times detected, rebalance load",
        "details": {
          "current_avg_response_time": 245.6,
          "target_response_time": 150.0,
          "overloaded_nodes": ["enhanced-node-abc123"],
          "underloaded_nodes": ["enhanced-node-def456"]
        }
      },
      {
        "type": "auto_scaling",
        "priority": "low",
        "description": "Network utilization is optimal, no scaling needed",
        "details": {
          "current_utilization": 0.67,
          "target_utilization": 0.7,
          "action": "maintain"
        }
      }
    ]
  }
}
```

**Example:**
```bash
curl http://localhost:9000/api/v1/metrics/performance
```

---

## ⚙️ Control Endpoints

### POST /control/start
Start the orchestrator services

**Response:**
```json
{
  "success": true,
  "message": "Orchestrator started successfully",
  "orchestrator_id": "orch_abc123"
}
```

**Example:**
```bash
curl -X POST http://localhost:9000/api/v1/control/start
```

### POST /control/stop
Stop the orchestrator services

**Response:**
```json
{
  "success": true,
  "message": "Orchestrator stopped successfully"
}
```

**Example:**
```bash
curl -X POST http://localhost:9000/api/v1/control/stop
```

---

## 🔧 Configuration Endpoints

### GET /config
Get current orchestrator configuration

**Response:**
```json
{
  "success": true,
  "config": {
    "orchestrator": {
      "id": "web4ai_main_orchestrator",
      "port": 9000,
      "host": "0.0.0.0",
      "heartbeat_interval": 30,
      "task_timeout": 300,
      "auto_discovery": true
    },
    "network": {
      "discovery_endpoints": [
        "http://localhost:8080",
        "http://localhost:8090"
      ],
      "load_balance_algorithm": "weighted_round_robin",
      "max_nodes": 100,
      "min_nodes": 1
    },
    "performance": {
      "monitoring_enabled": true,
      "optimization_enabled": true,
      "cpu_threshold": 80,
      "memory_threshold": 85
    }
  }
}
```

**Example:**
```bash
curl http://localhost:9000/api/v1/config
```

### PUT /config
Update orchestrator configuration

**Request Body:**
```json
{
  "network": {
    "load_balance_algorithm": "least_connections",
    "max_nodes": 150
  },
  "performance": {
    "cpu_threshold": 85,
    "memory_threshold": 90
  }
}
```

**Response:**
```json
{
  "success": true,
  "message": "Configuration updated",
  "config": {
    // ... updated configuration
  }
}
```

**Example:**
```bash
curl -X PUT http://localhost:9000/api/v1/config \
  -H "Content-Type: application/json" \
  -d '{
    "performance": {
      "cpu_threshold": 85,
      "memory_threshold": 90
    }
  }'
```

---

## 🔌 WebSocket Real-time Updates

### GET /websocket/info
Get WebSocket connection information

**Response:**
```json
{
  "success": true,
  "websocket": {
    "enabled": true,
    "url": "ws://localhost:9001",
    "connected_clients": 5,
    "max_connections": 100
  }
}
```

### WebSocket Connection
Connect to real-time updates:

**URL:** `ws://localhost:9001`

**Message Types:**
- `initial_status` - Initial network status on connection
- `network_status` - Periodic network status updates (every 5 seconds)
- `node_registered` - New node registered
- `task_submitted` - New task submitted
- `task_completed` - Task completed
- `node_failure` - Node failure detected

**Example WebSocket Message:**
```json
{
  "type": "network_status",
  "data": {
    "orchestrator_id": "orch_abc123",
    "timestamp": 1718542200.123,
    "network_metrics": {
      "active_nodes": 4,
      "tasks_completed": 1206,
      "network_utilization": 0.65
    }
  },
  "timestamp": 1718542200.123
}
```

**JavaScript Example:**
```javascript
const ws = new WebSocket('ws://localhost:9001');

ws.onopen = function() {
    console.log('Connected to orchestrator');
};

ws.onmessage = function(event) {
    const message = JSON.parse(event.data);
    console.log('Received:', message.type, message.data);
    
    if (message.type === 'network_status') {
        updateDashboard(message.data);
    }
};

ws.onclose = function() {
    console.log('Disconnected from orchestrator');
};
```

---

## 🔄 Load Balancing Algorithms

The orchestrator supports multiple load balancing algorithms:

### 1. Round Robin (`round_robin`)
Simple round-robin distribution of tasks

### 2. Weighted Round Robin (`weighted_round_robin`) 
**Default** - Distribution based on node performance and reliability

### 3. Least Connections (`least_connections`)
Routes to the node with the fewest active connections/tasks

### 4. Resource Aware (`resource_aware`)
Routes based on available CPU, memory, and GPU resources

### 5. Latency Optimized (`latency_optimized`)
Routes to the node with the lowest network latency

**Configure via API:**
```bash
curl -X PUT http://localhost:9000/api/v1/config \
  -H "Content-Type: application/json" \
  -d '{
    "network": {
      "load_balance_algorithm": "resource_aware"
    }
  }'
```

---

## 🚨 Error Handling

### HTTP Status Codes
- `200` - Success
- `400` - Bad Request (invalid data)
- `401` - Unauthorized (invalid API key)
- `404` - Not Found (resource doesn't exist)
- `429` - Too Many Requests (rate limited)
- `500` - Internal Server Error
- `503` - Service Unavailable (orchestrator not running)

### Error Response Format
```json
{
  "success": false,
  "error": "Node not found",
  "timestamp": "2025-06-16T10:30:00Z",
  "details": {
    "code": "NODE_NOT_FOUND",
    "node_id": "invalid_node_123"
  }
}
```

### Common Error Codes
- `ORCHESTRATOR_NOT_STARTED` - Orchestrator services not running
- `NODE_NOT_FOUND` - Specified node doesn't exist
- `TASK_NOT_FOUND` - Specified task doesn't exist
- `INVALID_CONFIG` - Configuration validation failed
- `RATE_LIMITED` - Too many requests from client
- `AUTHENTICATION_FAILED` - Invalid API key

---

## 📝 Usage Examples

### Complete Node Lifecycle

```bash
# 1. Register a node
curl -X POST http://localhost:9000/api/v1/nodes/my-node-001/register \
  -H "Content-Type: application/json" \
  -d '{
    "host": "192.168.1.100",
    "port": 8090,
    "node_type": "enhanced_node",
    "capabilities": ["ai_inference", "data_processing"],
    "version": "3.4.0"
  }'

# 2. Send heartbeat
curl -X POST http://localhost:9000/api/v1/nodes/my-node-001/heartbeat \
  -H "Content-Type: application/json" \
  -d '{
    "status": "active",
    "cpu_usage": 25.5,
    "memory_usage": 45.2,
    "load_score": 0.35
  }'

# 3. Check node status
curl http://localhost:9000/api/v1/nodes/my-node-001

# 4. Submit task to be routed to optimal node
curl -X POST http://localhost:9000/api/v1/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "task_type": "ai_inference",
    "input_data": {"prompt": "Hello world"},
    "requirements": {"capabilities": ["ai_inference"]}
  }'

# 5. Monitor task progress
curl http://localhost:9000/api/v1/tasks/[TASK_ID]

# 6. Put node in maintenance
curl -X PUT http://localhost:9000/api/v1/nodes/my-node-001/status \
  -H "Content-Type: application/json" \
  -d '{"status": "maintenance"}'

# 7. Unregister node
curl -X DELETE http://localhost:9000/api/v1/nodes/my-node-001
```

### Monitoring Dashboard Integration

```javascript
// Real-time dashboard updates
const ws = new WebSocket('ws://localhost:9001');
let metricsChart, nodesChart;

// Initialize charts
function initCharts() {
    metricsChart = new Chart(document.getElementById('metricsChart'), {
        type: 'line',
        data: { datasets: [] }
    });
}

// Handle WebSocket messages
ws.onmessage = function(event) {
    const message = JSON.parse(event.data);
    
    if (message.type === 'network_status') {
        updateMetrics(message.data);
    }
};

// Update dashboard metrics
function updateMetrics(data) {
    document.getElementById('activeNodes').textContent = data.network_metrics.active_nodes;
    document.getElementById('utilization').textContent = 
        (data.network_metrics.network_utilization * 100).toFixed(1) + '%';
    
    // Update chart
    metricsChart.data.datasets[0].data.push({
        x: new Date(),
        y: data.network_metrics.network_utilization
    });
    metricsChart.update();
}

// Fetch additional data via REST API
async function updateNodesList() {
    const response = await fetch('/api/v1/nodes');
    const data = await response.json();
    
    if (data.success) {
        const nodesList = document.getElementById('nodesList');
        nodesList.innerHTML = '';
        
        Object.values(data.nodes).forEach(node => {
            const nodeElement = document.createElement('div');
            nodeElement.innerHTML = `
                <h4>${node.node_id}</h4>
                <p>Status: ${node.status}</p>
                <p>CPU: ${node.cpu_usage.toFixed(1)}%</p>
                <p>Memory: ${node.memory_usage.toFixed(1)}%</p>
            `;
            nodesList.appendChild(nodeElement);
        });
    }
}
```

### Bulk Operations Script

```python
import requests
import json
import time

# Orchestrator API client
class OrchestratorClient:
    def __init__(self, base_url="http://localhost:9000/api/v1"):
        self.base_url = base_url
    
    def submit_task(self, task_data):
        response = requests.post(f"{self.base_url}/tasks", json=task_data)
        return response.json()
    
    def get_task_status(self, task_id):
        response = requests.get(f"{self.base_url}/tasks/{task_id}")
        return response.json()
    
    def wait_for_task(self, task_id, timeout=300):
        start_time = time.time()
        while time.time() - start_time < timeout:
            result = self.get_task_status(task_id)
            if result['success']:
                status = result['task']['status']
                if status in ['completed', 'failed']:
                    return result['task']
            time.sleep(2)
        raise TimeoutError(f"Task {task_id} timed out")

# Example: Submit multiple tasks and wait for completion
client = OrchestratorClient()

tasks = []
for i in range(10):
    task_data = {
        "task_type": "data_processing",
        "input_data": {"batch_id": i, "data": f"batch_{i}_data"},
        "priority": 3
    }
    
    result = client.submit_task(task_data)
    if result['success']:
        tasks.append(result['task_id'])
        print(f"Submitted task {result['task_id']}")

# Wait for all tasks to complete
completed_tasks = []
for task_id in tasks:
    try:
        task_result = client.wait_for_task(task_id)
        completed_tasks.append(task_result)
        print(f"Task {task_id} completed with status: {task_result['status']}")
    except TimeoutError:
        print(f"Task {task_id} timed out")

print(f"Completed {len(completed_tasks)} out of {len(tasks)} tasks")
```

---

## 🚀 Getting Started

### 1. Start the Orchestrator
```bash
# Generate default configuration
python orchestrator_api.py --generate-config

# Start the orchestrator
python orchestrator_api.py --config orchestrator_config.yaml
```

### 2. Verify It's Running
```bash
curl http://localhost:9000/api/v1/health
```

### 3. Register Your First Node
```bash
curl -X POST http://localhost:9000/api/v1/nodes/test-node-001/register \
  -H "Content-Type: application/json" \
  -d '{
    "host": "localhost",
    "port": 8090,
    "node_type": "test_node",
    "capabilities": ["basic_processing"]
  }'
```

### 4. Submit Your First Task
```bash
curl -X POST http://localhost:9000/api/v1/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "task_type": "test_task",
    "input_data": {"message": "Hello, Web4AI!"}
  }'
```

### 5. Monitor via Dashboard
Open your browser to `http://localhost:9000` for the built-in dashboard.

---

## 📚 Additional Resources

- **WebSocket Events**: Real-time network state changes
- **Load Balancing**: Automatic optimal task distribution  
- **Fault Tolerance**: Automatic node failure detection and recovery
- **Performance Optimization**: AI-driven network optimization
- **Horizontal Scaling**: Dynamic node addition/removal
- **Security**: API key authentication and rate limiting

For advanced configuration and deployment options, see the complete orchestrator documentation.
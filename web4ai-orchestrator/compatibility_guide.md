# 🔗 Web4AI Orchestrator-Node Compatibility Guide

## 🎯 Overview

This guide ensures your **Web4AI Orchestrator** works seamlessly with your **Enhanced Nodes**. Follow these steps to achieve full compatibility and optimal performance.

## ✅ **Pre-Flight Checklist**

### **1. System Requirements**
- [ ] Python 3.7+ installed on all systems
- [ ] Network connectivity between orchestrator and nodes
- [ ] Required ports open (9000 for orchestrator, 5000+ for nodes)
- [ ] Sufficient resources (CPU, RAM, storage)

### **2. Orchestrator Setup**
- [ ] Orchestrator running on port 9000
- [ ] `orchestrator_config.yaml` properly configured
- [ ] Discovery endpoints pointing to node addresses
- [ ] Health check endpoint responding: `http://localhost:9000/api/v1/health`

### **3. Node Setup**
- [ ] Enhanced nodes running on assigned ports
- [ ] Integration module installed
- [ ] Configuration updated with orchestrator URL
- [ ] Health check responding: `http://localhost:5000/api/v3/agents`

## 🚀 **Step-by-Step Integration**

### **Step 1: Install Integration Module**

```bash
# Navigate to your enhanced_node directory
cd enhanced_node

# Run the integration setup script
python setup_orchestrator_integration.py
```

### **Step 2: Configure Orchestrator Discovery**

Update your `orchestrator_config.yaml`:

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
    - "http://localhost:5000"    # Enhanced Node 1
    - "http://localhost:5001"    # Enhanced Node 2  
    - "http://localhost:5002"    # Enhanced Node 3
  max_nodes: 100
  min_nodes: 1
  
performance:
  cpu_threshold: 80
  memory_threshold: 85
  optimization_enabled: true
```

### **Step 3: Configure Node Settings**

Update your `config/settings.py`:

```python
# Orchestrator Integration Settings
ORCHESTRATOR_ENABLED = True
ORCHESTRATOR_URL = "http://localhost:9000"
ORCHESTRATOR_HEARTBEAT_INTERVAL = 30
ORCHESTRATOR_REGISTRATION_TIMEOUT = 10
ORCHESTRATOR_AUTO_RETRY = True

# Node Identity
NODE_ID_PREFIX = "enhanced_node"
NODE_CAPABILITIES = [
    "agent_management",
    "task_control", 
    "remote_management",
    "ai_operations",
    "blockchain_support",
    "websocket_communication",
    "real_time_monitoring",
    "bulk_operations",
    "script_deployment"
]
```

### **Step 4: Start Services in Order**

```bash
# Terminal 1: Start Orchestrator
cd web4ai-orchestrator
python orchestrator_api.py --config orchestrator_config.yaml

# Terminal 2: Start Enhanced Node 1  
cd enhanced_node
python main.py

# Terminal 3: Start Enhanced Node 2 (if using multiple nodes)
cd enhanced_node_2
NODE_PORT=5001 python main.py

# Verify registration
curl http://localhost:9000/api/v1/nodes
```

## 📊 **Verification & Testing**

### **Test 1: Node Registration**
```bash
# Check if nodes are registered
curl -X GET http://localhost:9000/api/v1/nodes

# Expected response:
{
  "success": true,
  "nodes": {
    "enhanced_node_abc123": {
      "node_id": "enhanced_node_abc123",
      "status": "active",
      "capabilities": ["agent_management", "task_control", ...],
      "agents": [...]
    }
  },
  "total_nodes": 1
}
```

### **Test 2: Heartbeat Monitoring**
```bash
# Check orchestrator status
curl -X GET http://localhost:9000/api/v1/status

# Check node health
curl -X GET http://localhost:5000/api/v3/agents
```

### **Test 3: Task Distribution**
```bash
# Submit a test task to orchestrator
curl -X POST http://localhost:9000/api/v1/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "task_type": "test_task",
    "priority": "normal",
    "requirements": {
      "capabilities": ["agent_management"]
    },
    "input_data": {"test": "data"}
  }'
```

## 🔧 **Troubleshooting Common Issues**

### **Issue 1: Node Registration Fails**

**Symptoms:**
- Node starts but doesn't appear in orchestrator
- Registration timeout errors
- Connection refused errors

**Solutions:**
```bash
# Check orchestrator is running
curl http://localhost:9000/api/v1/health

# Check network connectivity
telnet localhost 9000

# Verify node configuration
grep -n "ORCHESTRATOR_URL" config/settings.py

# Check logs
tail -f logs/orchestrator_integration.log
```

### **Issue 2: Heartbeat Failures**

**Symptoms:**
- Node shows as "inactive" in orchestrator
- Intermittent connection losses
- Heartbeat timeout warnings

**Solutions:**
```bash
# Check heartbeat interval settings
# Increase timeout in both systems
ORCHESTRATOR_HEARTBEAT_INTERVAL = 60  # Increase to 60 seconds

# Check system resources
htop
df -h

# Monitor network latency
ping localhost
```

### **Issue 3: Task Routing Problems**

**Symptoms:**
- Tasks not being assigned to nodes
- "No suitable nodes" errors
- Tasks stuck in pending state

**Solutions:**
```bash
# Verify node capabilities match task requirements
curl http://localhost:9000/api/v1/nodes/enhanced_node_abc123

# Check task requirements
# Ensure capabilities list includes required features

# Test direct node communication
curl -X POST http://localhost:5000/api/v4/task-control/create-task \
  -H "Content-Type: application/json" \
  -d '{"task_type": "test"}'
```

## ⚡ **Performance Optimization**

### **1. Load Balancing Configuration**
```yaml
# In orchestrator_config.yaml
performance:
  load_balancing:
    algorithm: "weighted_round_robin"
    weight_cpu: 0.4
    weight_memory: 0.3
    weight_tasks: 0.3
  
  health_checks:
    interval: 30
    timeout: 5
    retries: 3
```

### **2. Connection Pool Settings**
```python
# In node settings
CONNECTION_POOL_SIZE = 10
CONNECTION_TIMEOUT = 30
KEEP_ALIVE = True
MAX_RETRIES = 3
```

### **3. Monitoring & Metrics**
```bash
# Enable detailed monitoring
ORCHESTRATOR_METRICS_ENABLED = True
NODE_PERFORMANCE_MONITORING = True
PROMETHEUS_METRICS_ENABLED = True

# View metrics
curl http://localhost:9000/api/v1/metrics
curl http://localhost:5000/api/v3/metrics
```

## 🔒 **Security & Production Deployment**

### **1. Authentication Setup**
```yaml
# orchestrator_config.yaml
security:
  api_key_required: true
  jwt_secret: "your-secret-key"
  token_expiry: 3600
```

### **2. SSL/TLS Configuration**
```yaml
# For production deployment
orchestrator:
  host: "0.0.0.0"
  port: 9000
  ssl_enabled: true
  ssl_cert: "/path/to/cert.pem"
  ssl_key: "/path/to/key.pem"
```

### **3. Firewall Rules**
```bash
# Allow orchestrator port
sudo ufw allow 9000/tcp

# Allow node ports
sudo ufw allow 5000:5010/tcp

# Restrict access to specific IPs if needed
sudo ufw allow from 192.168.1.0/24 to any port 9000
```

## 📋 **Health Monitoring Dashboard**

### **Orchestrator Dashboard**
- **URL:** `http://localhost:9000/dashboard`
- **Features:** Node status, task queue, performance metrics
- **Alerts:** Node failures, high load, task failures

### **Node Dashboard**  
- **URL:** `http://localhost:5000/`
- **Features:** Agent status, resource usage, task history
- **Integration:** Links to orchestrator dashboard

## 🔄 **Maintenance & Updates**

### **Rolling Updates**
```bash
# Update nodes one at a time
# 1. Stop node
# 2. Update code
# 3. Start node
# 4. Verify registration
# 5. Repeat for next node
```

### **Backup & Recovery**
```bash
# Backup orchestrator state
cp -r orchestrator_data/ backup/orchestrator_$(date +%Y%m%d)/

# Backup node data
cp -r enhanced_node/data/ backup/node_$(date +%Y%m%d)/
```

## ✅ **Success Indicators**

When everything is working correctly, you should see:

1. **Orchestrator Logs:**
   ```
   ✅ Node enhanced_node_abc123 registered successfully
   💓 Heartbeat received from enhanced_node_abc123
   🎯 Task task_123 assigned to enhanced_node_abc123
   ```

2. **Node Logs:**
   ```
   ✅ Successfully registered with orchestrator
   💓 Heartbeat sent successfully
   📋 Task received: task_123
   ```

3. **Dashboard Status:**
   - All nodes show "Active" status
   - Tasks are being distributed and completed
   - Performance metrics are within normal ranges
   - No error alerts or warnings

## 📞 **Getting Help**

If you encounter issues not covered in this guide:

1. **Check the logs** in both orchestrator and node systems
2. **Verify network connectivity** between all components
3. **Test API endpoints** individually to isolate problems
4. **Monitor resource usage** to identify bottlenecks
5. **Review configuration files** for syntax errors or typos

The integration is designed to be robust and self-healing, but proper configuration is essential for optimal performance.

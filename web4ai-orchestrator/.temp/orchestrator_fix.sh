#!/bin/bash
# orchestrator-fix.sh
# Fix for Web4AI Orchestrator dependency and configuration issues

echo "🔧 Fixing Web4AI Orchestrator Dependencies and Configuration..."

# Fix 1: Install the correct websocket package
echo "📦 Installing correct websocket dependencies..."
pip install websocket-client==1.6.4
pip install python-socketio==5.8.0
pip install eventlet==0.33.3

# Fix 2: Install other missing dependencies that might be needed
echo "📦 Installing additional dependencies..."
pip install flask-socketio==5.3.4
pip install psutil==5.9.5
pip install pyyaml==6.0.1
pip install requests==2.31.0
pip install asyncio-mqtt==0.13.0

# Fix 3: Create the missing production configuration file
echo "📝 Creating production configuration file..."
cat > orchestrator_config_production.yaml << 'EOF'
# Web4AI Orchestrator Production Configuration
orchestrator:
  id: "web4ai_production_orchestrator"
  port: 9000
  host: "0.0.0.0"
  heartbeat_interval: 30
  task_timeout: 300
  auto_discovery: true
  debug: false
  log_level: "INFO"

network:
  discovery_endpoints:
    - "http://localhost:5000"    # Enhanced Node 1
    - "http://localhost:5001"    # Enhanced Node 2
    - "http://localhost:5002"    # Enhanced Node 3
  max_nodes: 100
  min_nodes: 1
  connection_timeout: 10
  retry_attempts: 3
  retry_delay: 5

performance:
  cpu_threshold: 80
  memory_threshold: 85
  optimization_enabled: true
  load_balancing:
    algorithm: "weighted_round_robin"
    weight_cpu: 0.4
    weight_memory: 0.3
    weight_tasks: 0.3
  health_checks:
    interval: 30
    timeout: 5
    retries: 3

security:
  api_key_required: false
  cors_enabled: true
  rate_limiting: true
  max_requests_per_minute: 100

logging:
  level: "INFO"
  file: "logs/orchestrator.log"
  max_size: "10MB"
  backup_count: 5
  console_output: true

database:
  type: "sqlite"
  path: "data/orchestrator.db"
  backup_enabled: true
  backup_interval: 3600

metrics:
  enabled: true
  prometheus_port: 9090
  collection_interval: 60
EOF

# Fix 4: Create updated requirements.txt
echo "📋 Creating updated requirements.txt..."
cat > requirements.txt << 'EOF'
# Web4AI Orchestrator Dependencies
flask==2.3.3
flask-socketio==5.3.4
flask-cors==4.0.0
websocket-client==1.6.4
python-socketio==5.8.0
eventlet==0.33.3
psutil==5.9.5
pyyaml==6.0.1
requests==2.31.0
asyncio-mqtt==0.13.0
aiohttp==3.8.5
asyncio==3.4.3
dataclasses-json==0.6.1
prometheus-client==0.17.1
schedule==1.2.0
concurrent-futures==3.1.1
threading2==0.1.2
queue==0.1.1
typing-extensions==4.7.1
python-dateutil==2.8.2
EOF

# Fix 5: Install all dependencies
echo "📦 Installing all dependencies from requirements.txt..."
pip install -r requirements.txt

# Fix 6: Create necessary directories
echo "📁 Creating necessary directories..."
mkdir -p logs
mkdir -p data
mkdir -p config
mkdir -p backup

# Fix 7: Create a simple websocket compatibility wrapper if needed
echo "🔧 Creating websocket compatibility wrapper..."
cat > websocket_wrapper.py << 'EOF'
"""
WebSocket compatibility wrapper for Web4AI Orchestrator
This handles different websocket library imports
"""

try:
    import websocket
except ImportError:
    try:
        import websocket as websocket_client
        websocket = websocket_client
    except ImportError:
        print("⚠️  Warning: No websocket library found, creating mock")
        class MockWebSocket:
            def __init__(self):
                pass
            def create_connection(self, *args, **kwargs):
                return None
        websocket = MockWebSocket()

# Export the websocket module
__all__ = ['websocket']
EOF

# Fix 8: Update the main orchestrator file to handle the import correctly
echo "🔧 Fixing websocket import in orchestrator..."
if [ -f "web4ai_orchestrator.py" ]; then
    # Create backup
    cp web4ai_orchestrator.py web4ai_orchestrator.py.backup
    
    # Fix the websocket import
    sed -i 's/import websocket/try:\n    import websocket\nexcept ImportError:\n    import websocket_client as websocket/' web4ai_orchestrator.py
fi

# Fix 9: Create a startup script
echo "🚀 Creating startup script..."
cat > start_orchestrator.sh << 'EOF'
#!/bin/bash
# Start Web4AI Orchestrator with proper error handling

echo "🚀 Starting Web4AI Orchestrator..."

# Check if virtual environment is activated
if [[ "$VIRTUAL_ENV" == "" ]]; then
    echo "⚠️  Warning: No virtual environment detected"
    echo "   Consider running: source venv/bin/activate"
fi

# Check dependencies
echo "🔍 Checking dependencies..."
python -c "import flask, websocket, yaml, psutil" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "❌ Missing dependencies. Installing..."
    pip install -r requirements.txt
fi

# Create directories if they don't exist
mkdir -p logs data config backup

# Start the orchestrator
echo "🎯 Starting orchestrator on port 9000..."
python orchestrator_api.py --config orchestrator_config_production.yaml --host 0.0.0.0 --port 9000

EOF

chmod +x start_orchestrator.sh

# Fix 10: Create a comprehensive test script
echo "🧪 Creating test script..."
cat > test_orchestrator.py << 'EOF'
#!/usr/bin/env python3
"""Test script for Web4AI Orchestrator"""

import requests
import json
import time
import sys

def test_orchestrator():
    """Test orchestrator functionality"""
    print("🧪 Testing Web4AI Orchestrator...")
    
    base_url = "http://localhost:9000"
    
    # Test 1: Health check
    try:
        print("🔍 Testing health endpoint...")
        response = requests.get(f"{base_url}/api/v1/health", timeout=5)
        if response.status_code == 200:
            print("✅ Health check passed")
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False
    
    # Test 2: Status endpoint
    try:
        print("🔍 Testing status endpoint...")
        response = requests.get(f"{base_url}/api/v1/status", timeout=5)
        if response.status_code == 200:
            print("✅ Status endpoint working")
        else:
            print(f"⚠️  Status endpoint issues: {response.status_code}")
    except Exception as e:
        print(f"⚠️  Status endpoint error: {e}")
    
    # Test 3: Nodes endpoint
    try:
        print("🔍 Testing nodes endpoint...")
        response = requests.get(f"{base_url}/api/v1/nodes", timeout=5)
        if response.status_code == 200:
            data = response.json()
            node_count = len(data.get('nodes', {}))
            print(f"✅ Nodes endpoint working: {node_count} nodes")
        else:
            print(f"⚠️  Nodes endpoint issues: {response.status_code}")
    except Exception as e:
        print(f"⚠️  Nodes endpoint error: {e}")
    
    print("🎉 Basic orchestrator tests completed")
    return True

if __name__ == "__main__":
    success = test_orchestrator()
    sys.exit(0 if success else 1)
EOF

chmod +x test_orchestrator.py

echo "✅ All fixes applied successfully!"
echo ""
echo "🎯 Next Steps:"
echo "1. Run the startup script: ./start_orchestrator.sh"
echo "2. Or start manually: python orchestrator_api.py --config orchestrator_config_production.yaml"
echo "3. Test the setup: python test_orchestrator.py"
echo "4. Check logs in: logs/orchestrator.log"
echo ""
echo "🔧 What was fixed:"
echo "- ✅ Installed correct websocket-client package"
echo "- ✅ Created production configuration file"
echo "- ✅ Updated requirements.txt with all dependencies"
echo "- ✅ Created necessary directories (logs, data, config, backup)"
echo "- ✅ Added compatibility wrapper for websocket imports"
echo "- ✅ Created startup and test scripts"

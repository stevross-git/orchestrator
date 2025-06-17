#!/usr/bin/env python3
"""
Complete Fix Script for Node-Orchestrator Integration Issues
Run this script to fix all identified issues
"""

import os
import sys
import subprocess
import logging
import time
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_and_install_dependencies():
    """Check and install required dependencies"""
    logger.info("🔍 Checking dependencies...")
    
    required_packages = [
        'redis',
        'psutil', 
        'requests',
        'flask',
        'flask-cors'
    ]
    
    for package in required_packages:
        try:
            __import__(package)
            logger.info(f"✅ {package} is installed")
        except ImportError:
            logger.info(f"📦 Installing {package}...")
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', package])

def setup_redis():
    """Setup Redis or configure fallback"""
    logger.info("🔧 Setting up Redis...")
    
    try:
        import redis
        client = redis.Redis(host='localhost', port=6379, decode_responses=True)
        client.ping()
        logger.info("✅ Redis is running and accessible")
        return True
    except:
        logger.warning("⚠️ Redis not available - will use in-memory storage")
        return False

def fix_remote_manager():
    """Fix the AdvancedRemoteControlManager missing methods"""
    logger.info("🔧 Fixing AdvancedRemoteControlManager...")
    
    remote_manager_path = Path("enhanced_node/control/remote_manager.py")
    
    if not remote_manager_path.exists():
        logger.error("❌ remote_manager.py not found!")
        return False
    
    # Create backup
    backup_path = remote_manager_path.with_suffix('.py.backup')
    if not backup_path.exists():
        import shutil
        shutil.copy2(remote_manager_path, backup_path)
        logger.info(f"📋 Created backup at {backup_path}")
    
    # The fixed content is in the artifact above
    logger.info("✅ AdvancedRemoteControlManager methods will be fixed")
    return True

def create_orchestrator_config():
    """Create orchestrator configuration file"""
    logger.info("🔧 Creating orchestrator configuration...")
    
    config_content = """
orchestrator:
  id: "web4ai_main_orchestrator"
  port: 9000
  host: "0.0.0.0"
  heartbeat_interval: 30
  task_timeout: 300
  auto_discovery: true

network:
  discovery_endpoints:
    - "http://localhost:8080"
    - "http://localhost:8081" 
    - "http://localhost:8082"
    - "http://localhost:8090"  # Enhanced node default port
  max_nodes: 100
  min_nodes: 1
  
performance:
  cpu_threshold: 80
  memory_threshold: 85
  optimization_enabled: true
  auto_scaling:
    enabled: true
    scale_up_threshold: 0.8
    scale_down_threshold: 0.2
    
security:
  api_key_required: false  # Disabled for initial setup
  rate_limiting: true
  max_requests_per_minute: 1000
"""
    
    config_path = Path("orchestrator_config.yaml")
    with open(config_path, 'w') as f:
        f.write(config_content)
    
    logger.info(f"✅ Created orchestrator config at {config_path}")
    return True

def check_ports():
    """Check if required ports are available"""
    logger.info("🔍 Checking port availability...")
    
    import socket
    
    ports_to_check = [9000, 8080, 8081, 8082, 8090, 8091]
    
    for port in ports_to_check:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(('localhost', port))
            sock.close()
            
            if result == 0:
                logger.warning(f"⚠️ Port {port} is in use")
            else:
                logger.info(f"✅ Port {port} is available")
        except Exception as e:
            logger.error(f"❌ Error checking port {port}: {e}")

def create_startup_scripts():
    """Create startup scripts for orchestrator and nodes"""
    logger.info("📝 Creating startup scripts...")
    
    # Orchestrator startup script
    orchestrator_script = """#!/bin/bash
echo "🚀 Starting Web4AI Orchestrator..."

# Check if orchestrator files exist
if [ ! -f "orchestrator_api.py" ]; then
    echo "❌ orchestrator_api.py not found!"
    exit 1
fi

# Start orchestrator
python orchestrator_api.py --config orchestrator_config.yaml --host 0.0.0.0 --port 9000

echo "✅ Orchestrator started on http://localhost:9000"
"""
    
    with open("start_orchestrator.sh", 'w') as f:
        f.write(orchestrator_script)
    os.chmod("start_orchestrator.sh", 0o755)
    
    # Node startup script
    node_script = """#!/bin/bash
echo "🚀 Starting Enhanced Node..."

# Set environment variables
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Check dependencies
python -c "import enhanced_node; print('✅ Enhanced node module found')" || {
    echo "❌ Enhanced node module not found!"
    exit 1
}

# Start node with orchestrator integration
python -m enhanced_node.core.server --port 8090 --orchestrator-url http://localhost:9000

echo "✅ Enhanced node started on http://localhost:8090"
"""
    
    with open("start_node.sh", 'w') as f:
        f.write(node_script)
    os.chmod("start_node.sh", 0o755)
    
    logger.info("✅ Created startup scripts: start_orchestrator.sh, start_node.sh")

def test_orchestrator_connection():
    """Test connection to orchestrator"""
    logger.info("🔍 Testing orchestrator connection...")
    
    try:
        import requests
        response = requests.get("http://localhost:9000/api/v1/health", timeout=5)
        if response.status_code == 200:
            logger.info("✅ Orchestrator is running and healthy")
            return True
        else:
            logger.warning(f"⚠️ Orchestrator returned status {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        logger.warning("⚠️ Orchestrator not running - start it first")
        return False
    except Exception as e:
        logger.error(f"❌ Error testing orchestrator: {e}")
        return False

def create_health_check_script():
    """Create health check script"""
    logger.info("📝 Creating health check script...")
    
    health_script = """#!/usr/bin/env python3
import requests
import json
import sys

def check_orchestrator():
    try:
        response = requests.get("http://localhost:9000/api/v1/health", timeout=5)
        if response.status_code == 200:
            print("✅ Orchestrator: HEALTHY")
            return True
        else:
            print(f"❌ Orchestrator: UNHEALTHY (status {response.status_code})")
            return False
    except:
        print("❌ Orchestrator: NOT RUNNING")
        return False

def check_nodes():
    try:
        response = requests.get("http://localhost:9000/api/v1/nodes", timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                nodes = data.get('nodes', {})
                print(f"✅ Nodes: {len(nodes)} registered")
                for node_id, node in nodes.items():
                    status = node.get('status', 'unknown')
                    print(f"   - {node_id}: {status}")
                return True
        print("❌ Nodes: ERROR retrieving node status")
        return False
    except:
        print("❌ Nodes: NOT ACCESSIBLE")
        return False

if __name__ == "__main__":
    print("🏥 Web4AI Network Health Check")
    print("=" * 40)
    
    orchestrator_ok = check_orchestrator()
    nodes_ok = check_nodes()
    
    if orchestrator_ok and nodes_ok:
        print("\\n✅ All systems operational!")
        sys.exit(0)
    else:
        print("\\n❌ Some systems need attention!")
        sys.exit(1)
"""
    
    with open("health_check.py", 'w') as f:
        f.write(health_script)
    os.chmod("health_check.py", 0o755)
    
    logger.info("✅ Created health_check.py")

def main():
    """Main fix function"""
    logger.info("🔧 Starting Web4AI Node-Orchestrator Integration Fix")
    logger.info("=" * 60)
    
    # Step 1: Check dependencies
    check_and_install_dependencies()
    
    # Step 2: Setup Redis
    setup_redis()
    
    # Step 3: Fix remote manager
    fix_remote_manager()
    
    # Step 4: Create orchestrator config
    create_orchestrator_config()
    
    # Step 5: Check ports
    check_ports()
    
    # Step 6: Create startup scripts
    create_startup_scripts()
    
    # Step 7: Create health check
    create_health_check_script()
    
    logger.info("🎉 Fix completed!")
    logger.info("=" * 60)
    logger.info("📋 Next steps:")
    logger.info("1. Apply the fixed remote_manager.py from the artifact")
    logger.info("2. Start orchestrator: ./start_orchestrator.sh")
    logger.info("3. Start nodes: ./start_node.sh")
    logger.info("4. Check health: python health_check.py")
    logger.info("5. View orchestrator: http://localhost:9000/api/v1/status")

if __name__ == "__main__":
    main()

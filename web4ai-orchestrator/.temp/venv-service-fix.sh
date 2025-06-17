#!/bin/bash
# venv-service-fix.sh - Fix systemd service to use virtual environment

echo "🔧 Fixing SystemD Service to Use Virtual Environment"
echo "=================================================="

# Get current user and path
CURRENT_USER=$(whoami)
CURRENT_PATH=$(pwd)
VENV_PATH="$CURRENT_PATH/venv"

echo "👤 Current user: $CURRENT_USER"
echo "📁 Current path: $CURRENT_PATH"
echo "🐍 Virtual env: $VENV_PATH"

# Step 1: Stop the failing service
echo "1️⃣ Stopping the failing service..."
sudo systemctl stop web4ai-orchestrator

# Step 2: Install missing dependencies in the virtual environment first
echo "2️⃣ Installing missing dependencies in virtual environment..."
source $VENV_PATH/bin/activate
pip install websocket-client==1.6.4 flask-socketio==5.3.4 pyyaml==6.0.1 psutil==5.9.5 eventlet==0.33.3 flask-cors==4.0.0 requests==2.31.0
deactivate

# Step 3: Test the virtual environment has all dependencies
echo "3️⃣ Testing virtual environment dependencies..."
$VENV_PATH/bin/python -c "
try:
    import websocket_client as websocket
    print('✅ websocket-client works')
except ImportError as e:
    print(f'❌ websocket-client failed: {e}')

try:
    import flask
    print('✅ flask works')
except ImportError as e:
    print(f'❌ flask failed: {e}')

try:
    import yaml
    print('✅ yaml works')
except ImportError as e:
    print(f'❌ yaml failed: {e}')

try:
    import psutil
    print('✅ psutil works')
except ImportError as e:
    print(f'❌ psutil failed: {e}')
"

# Step 4: Update systemd service to use virtual environment
echo "4️⃣ Updating systemd service to use virtual environment..."
sudo tee /etc/systemd/system/web4ai-orchestrator.service > /dev/null << EOF
[Unit]
Description=Web4AI Orchestrator
After=network.target
Wants=network-online.target
After=network-online.target

[Service]
Type=simple
User=$CURRENT_USER
Group=$CURRENT_USER
WorkingDirectory=$CURRENT_PATH
Environment=PYTHONPATH=$CURRENT_PATH
Environment=PYTHONUNBUFFERED=1
Environment=PATH=$VENV_PATH/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
ExecStart=$VENV_PATH/bin/python orchestrator_api.py --config orchestrator_config_production.yaml --host 0.0.0.0 --port 9000
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

echo "✅ Updated systemd service to use virtual environment"

# Step 5: Create orchestrator config in current directory
echo "5️⃣ Creating orchestrator configuration in current directory..."
tee orchestrator_config_production.yaml > /dev/null << 'EOF'
orchestrator:
  id: "web4ai_production_orchestrator"
  port: 9000
  host: "0.0.0.0"
  heartbeat_interval: 30
  task_timeout: 300
  auto_discovery: true
  debug: false
  log_level: "INFO"
  domain: "orc.peoplesainetwork.com"
  
network:
  discovery_endpoints:
    - "http://localhost:5000"
    - "http://localhost:5001"
    - "http://localhost:5002"
  max_nodes: 100
  min_nodes: 1
  connection_timeout: 10
  retry_attempts: 3
  retry_delay: 5

performance:
  cpu_threshold: 80
  memory_threshold: 85
  optimization_enabled: true

security:
  api_key_required: false
  cors_enabled: true
  rate_limiting: true
  max_requests_per_minute: 100

logging:
  level: "INFO"
  file: "logs/orchestrator.log"
  console_output: true

database:
  type: "sqlite"
  path: "data/orchestrator.db"
EOF

# Step 6: Create necessary directories in current path
echo "6️⃣ Creating necessary directories..."
mkdir -p logs data config

# Step 7: Fix websocket import if needed
echo "7️⃣ Checking and fixing websocket import..."
if [ -f "web4ai_orchestrator.py" ]; then
    cp web4ai_orchestrator.py web4ai_orchestrator.py.backup
    
    python3 -c "
with open('web4ai_orchestrator.py', 'r') as f:
    content = f.read()

old_import = 'import websocket'
new_import = '''try:
    import websocket
except ImportError:
    import websocket_client as websocket'''

if old_import in content and 'websocket_client as websocket' not in content:
    content = content.replace(old_import, new_import)
    with open('web4ai_orchestrator.py', 'w') as f:
        f.write(content)
    print('✅ Fixed websocket import')
else:
    print('ℹ️ Websocket import already fixed or not found')
"
fi

# Step 8: Test the orchestrator manually first
echo "8️⃣ Testing orchestrator manually..."
$VENV_PATH/bin/python -c "
import sys
sys.path.insert(0, '.')
try:
    from orchestrator_api import *
    print('✅ Orchestrator imports work')
except Exception as e:
    print(f'❌ Orchestrator import failed: {e}')
"

# Step 9: Reload and start the service
echo "9️⃣ Reloading and starting the service..."
sudo systemctl daemon-reload
sudo systemctl start web4ai-orchestrator

# Wait for service to start
sleep 5

echo "📊 Checking service status..."
sudo systemctl status web4ai-orchestrator --no-pager -l

# Step 10: Test connectivity
echo "🔟 Testing orchestrator connectivity..."
if curl -s --connect-timeout 10 http://localhost:9000/api/v1/health >/dev/null 2>&1; then
    echo "✅ Orchestrator responding on port 9000"
    response=$(curl -s http://localhost:9000/api/v1/health)
    echo "   Response: $response"
    ORCHESTRATOR_WORKING=true
else
    echo "❌ Orchestrator not responding on port 9000"
    echo "📋 Recent logs:"
    sudo journalctl -u web4ai-orchestrator -n 10 --no-pager
    ORCHESTRATOR_WORKING=false
fi

# Step 11: Test external access and fix nginx if needed
echo "1️⃣1️⃣ Testing and fixing external access..."

# First, make sure nginx is configured correctly
echo "🌐 Configuring nginx..."
sudo tee /etc/nginx/sites-available/orc.peoplesainetwork.com > /dev/null << 'EOF'
server {
    listen 80;
    listen [::]:80;
    server_name orc.peoplesainetwork.com;
    
    # Allow Let's Encrypt challenge
    location /.well-known/acme-challenge/ {
        root /var/www/html;
        allow all;
    }
    
    # Main proxy
    location / {
        proxy_pass http://127.0.0.1:9000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
    
    # API endpoints
    location /api/ {
        proxy_pass http://127.0.0.1:9000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # CORS headers
        add_header Access-Control-Allow-Origin * always;
        add_header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, OPTIONS" always;
        add_header Access-Control-Allow-Headers "Content-Type, Authorization, X-Requested-With" always;
        
        if ($request_method = 'OPTIONS') {
            return 204;
        }
    }
    
    # Health check
    location /health {
        proxy_pass http://127.0.0.1:9000/api/v1/health;
        proxy_set_header Host $host;
        access_log off;
    }
}

# Default server block (fallback)
server {
    listen 80 default_server;
    listen [::]:80 default_server;
    server_name _;
    
    location / {
        proxy_pass http://127.0.0.1:9000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    location /api/ {
        proxy_pass http://127.0.0.1:9000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        add_header Access-Control-Allow-Origin * always;
        add_header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, OPTIONS" always;
        add_header Access-Control-Allow-Headers "Content-Type, Authorization, X-Requested-With" always;
        
        if ($request_method = 'OPTIONS') {
            return 204;
        }
    }
}
EOF

# Enable the site
sudo rm -f /etc/nginx/sites-enabled/default
sudo ln -sf /etc/nginx/sites-available/orc.peoplesainetwork.com /etc/nginx/sites-enabled/

# Test and reload nginx
sudo nginx -t
if [ $? -eq 0 ]; then
    sudo systemctl reload nginx
    echo "✅ Nginx configuration updated"
else
    echo "❌ Nginx configuration error"
fi

# Step 12: Test external access
echo "1️⃣2️⃣ Testing external access..."
sleep 3

echo "🔍 Testing direct IP access..."
if curl -s --connect-timeout 10 http://3.25.107.210/health >/dev/null 2>&1; then
    echo "✅ Direct IP access working"
    response=$(curl -s http://3.25.107.210/health)
    echo "   Response: $response"
    DIRECT_IP_WORKING=true
else
    echo "❌ Direct IP access not working"
    DIRECT_IP_WORKING=false
fi

echo "🔍 Testing domain access..."
if curl -s --connect-timeout 10 http://orc.peoplesainetwork.com/health >/dev/null 2>&1; then
    echo "✅ Domain access working"
    response=$(curl -s http://orc.peoplesainetwork.com/health)
    echo "   Response: $response"
    DOMAIN_WORKING=true
else
    echo "❌ Domain access not working"
    DOMAIN_WORKING=false
fi

# Step 13: Final summary
echo ""
echo "🎯 FINAL SUMMARY"
echo "================"

if [ "$ORCHESTRATOR_WORKING" = true ]; then
    echo "✅ Orchestrator: Running on port 9000"
else
    echo "❌ Orchestrator: Not running (check logs)"
fi

if [ "$DIRECT_IP_WORKING" = true ]; then
    echo "✅ Direct IP Access: Working"
else
    echo "❌ Direct IP Access: Not working (firewall/security group)"
fi

if [ "$DOMAIN_WORKING" = true ]; then
    echo "✅ Domain Access: Working"
else
    echo "❌ Domain Access: Not working (firewall/security group)"
fi

echo ""
echo "🌐 ACCESS URLS:"
echo "   🔧 Direct IP: http://3.25.107.210/health"
echo "   🌐 Domain: http://orc.peoplesainetwork.com/health"
echo "   🔌 API: http://orc.peoplesainetwork.com/api/v1/status"

echo ""
echo "🔧 MANAGEMENT COMMANDS:"
echo "   sudo systemctl status web4ai-orchestrator"
echo "   sudo journalctl -u web4ai-orchestrator -f"
echo "   sudo systemctl restart web4ai-orchestrator"
echo "   curl http://localhost:9000/api/v1/health"

if [ "$ORCHESTRATOR_WORKING" = true ] && [ "$DIRECT_IP_WORKING" = true ]; then
    echo ""
    echo "🎉 SUCCESS! Your Web4AI Orchestrator is running!"
    echo ""
    echo "🔒 To add SSL/HTTPS:"
    echo "   sudo certbot --nginx -d orc.peoplesainetwork.com"
elif [ "$ORCHESTRATOR_WORKING" = true ] && [ "$DIRECT_IP_WORKING" != true ]; then
    echo ""
    echo "⚠️ ORCHESTRATOR IS RUNNING but external access blocked"
    echo ""
    echo "🔥 AWS SECURITY GROUP SETTINGS NEEDED:"
    echo "   - Go to AWS EC2 Console → Security Groups"
    echo "   - Find your instance's security group"
    echo "   - Add these inbound rules:"
    echo "     HTTP (80) - Source: 0.0.0.0/0"
    echo "     HTTPS (443) - Source: 0.0.0.0/0"
    echo "     Custom (9000) - Source: 0.0.0.0/0"
else
    echo ""
    echo "❌ Issues remain - check the logs:"
    echo "   sudo journalctl -u web4ai-orchestrator -f"
fi

echo ""
echo "🔧 Fix completed! The service now uses your virtual environment."

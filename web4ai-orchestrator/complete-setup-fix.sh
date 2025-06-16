#!/bin/bash
# complete-setup-fix.sh - Fix all the issues and get orchestrator running

echo "🔧 Complete Setup Fix for Web4AI Orchestrator"
echo "============================================="

# Step 1: Install missing dependencies and tools
echo "1️⃣ Installing dependencies..."
sudo apt update
sudo apt install -y net-tools curl jq python3-pip

# Step 2: Install Python dependencies system-wide
echo "2️⃣ Installing Python dependencies system-wide..."
sudo /usr/bin/python3 -m pip install --upgrade pip
sudo /usr/bin/python3 -m pip install \
    websocket-client==1.6.4 \
    flask==2.3.3 \
    flask-socketio==5.3.4 \
    flask-cors==4.0.0 \
    pyyaml==6.0.1 \
    psutil==5.9.5 \
    eventlet==0.33.3 \
    requests==2.31.0

# Step 3: Create orchestrator directory and copy files
echo "3️⃣ Setting up orchestrator directory..."
sudo mkdir -p /opt/web4ai/orchestrator
sudo cp -r ./* /opt/web4ai/orchestrator/ 2>/dev/null || true
sudo mkdir -p /opt/web4ai/orchestrator/{logs,data,config}
sudo chown -R root:root /opt/web4ai/orchestrator

# Step 4: Fix websocket import if needed
echo "4️⃣ Fixing websocket import..."
if [ -f "/opt/web4ai/orchestrator/web4ai_orchestrator.py" ]; then
    sudo cp /opt/web4ai/orchestrator/web4ai_orchestrator.py /opt/web4ai/orchestrator/web4ai_orchestrator.py.backup
    
    sudo python3 -c "
import sys
with open('/opt/web4ai/orchestrator/web4ai_orchestrator.py', 'r') as f:
    content = f.read()

old_import = 'import websocket'
new_import = '''try:
    import websocket
except ImportError:
    import websocket_client as websocket'''

if old_import in content and 'websocket_client as websocket' not in content:
    content = content.replace(old_import, new_import)
    with open('/opt/web4ai/orchestrator/web4ai_orchestrator.py', 'w') as f:
        f.write(content)
    print('✅ Fixed websocket import')
else:
    print('ℹ️ Websocket import already fixed or not found')
"
fi

# Step 5: Create production configuration
echo "5️⃣ Creating production configuration..."
sudo tee /opt/web4ai/orchestrator/orchestrator_config_production.yaml > /dev/null << 'EOF'
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

# Step 6: Create systemd service
echo "6️⃣ Creating systemd service..."
sudo tee /etc/systemd/system/web4ai-orchestrator.service > /dev/null << 'EOF'
[Unit]
Description=Web4AI Orchestrator
After=network.target
Wants=network-online.target
After=network-online.target

[Service]
Type=simple
User=root
Group=root
WorkingDirectory=/opt/web4ai/orchestrator
Environment=PYTHONPATH=/opt/web4ai/orchestrator
Environment=PYTHONUNBUFFERED=1
ExecStart=/usr/bin/python3 orchestrator_api.py --config orchestrator_config_production.yaml --host 0.0.0.0 --port 9000
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# Step 7: Check and fix firewall
echo "7️⃣ Checking firewall configuration..."
if sudo ufw status | grep -q "Status: active"; then
    echo "🔥 UFW firewall is active - configuring rules..."
    sudo ufw allow 80/tcp
    sudo ufw allow 443/tcp
    sudo ufw allow 9000/tcp
    sudo ufw allow 22/tcp
    echo "✅ Firewall rules added"
else
    echo "ℹ️ UFW firewall not active"
fi

# Check if there are any other firewall rules
if iptables -L | grep -q "DROP\|REJECT"; then
    echo "⚠️ Other firewall rules detected. You may need to allow ports 80, 443, and 9000"
fi

# Step 8: Test orchestrator manually first
echo "8️⃣ Testing orchestrator startup..."
cd /opt/web4ai/orchestrator
echo "🧪 Quick test of orchestrator imports..."
sudo /usr/bin/python3 -c "
try:
    import websocket_client as websocket
    print('✅ websocket import works')
except ImportError as e:
    print(f'❌ websocket import failed: {e}')

try:
    import flask
    print('✅ flask import works')
except ImportError as e:
    print(f'❌ flask import failed: {e}')

try:
    import yaml
    print('✅ yaml import works')
except ImportError as e:
    print(f'❌ yaml import failed: {e}')
"

# Step 9: Start the service
echo "9️⃣ Starting web4ai-orchestrator service..."
sudo systemctl daemon-reload
sudo systemctl enable web4ai-orchestrator
sudo systemctl start web4ai-orchestrator

# Wait for service to start
sleep 5

echo "📊 Checking service status..."
sudo systemctl status web4ai-orchestrator --no-pager -l

# Step 10: Test if orchestrator is responding
echo "🔟 Testing orchestrator connectivity..."
if curl -s --connect-timeout 10 http://localhost:9000/api/v1/health >/dev/null 2>&1; then
    echo "✅ Orchestrator responding on port 9000"
    response=$(curl -s http://localhost:9000/api/v1/health)
    echo "   Response: $response"
    ORCHESTRATOR_RUNNING=true
else
    echo "❌ Orchestrator not responding on port 9000"
    echo "📋 Service logs:"
    sudo journalctl -u web4ai-orchestrator -n 20 --no-pager
    ORCHESTRATOR_RUNNING=false
fi

# Step 11: Test external HTTP access (for SSL verification)
echo "1️⃣1️⃣ Testing external HTTP access..."
if curl -s --connect-timeout 10 http://orc.peoplesainetwork.com/health >/dev/null 2>&1; then
    echo "✅ External HTTP access working"
    HTTP_WORKING=true
else
    echo "❌ External HTTP access not working"
    echo "   This could be due to:"
    echo "   - Firewall blocking port 80"
    echo "   - Security group not allowing HTTP traffic"  
    echo "   - Nginx not running properly"
    HTTP_WORKING=false
fi

# Step 12: Only attempt SSL if HTTP is working
if [ "$HTTP_WORKING" = true ] && [ "$ORCHESTRATOR_RUNNING" = true ]; then
    echo "1️⃣2️⃣ Attempting SSL certificate..."
    
    # Create web root for Let's Encrypt
    sudo mkdir -p /var/www/html/.well-known/acme-challenge
    sudo chown -R www-data:www-data /var/www/html
    
    # Try to get SSL certificate
    sudo certbot certonly \
        --webroot \
        --webroot-path=/var/www/html \
        -d orc.peoplesainetwork.com \
        --non-interactive \
        --agree-tos \
        --email admin@peoplesainetwork.com \
        --keep-until-expiring
    
    if [ $? -eq 0 ]; then
        echo "✅ SSL certificate obtained"
        
        # Update nginx config for HTTPS
        sudo tee /etc/nginx/sites-available/orc.peoplesainetwork.com > /dev/null << 'EOF'
# HTTP to HTTPS redirect
server {
    listen 80;
    listen [::]:80;
    server_name orc.peoplesainetwork.com;
    
    location /.well-known/acme-challenge/ {
        root /var/www/html;
        allow all;
    }
    
    location / {
        return 301 https://$server_name$request_uri;
    }
}

# HTTPS configuration
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name orc.peoplesainetwork.com;
    
    ssl_certificate /etc/letsencrypt/live/orc.peoplesainetwork.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/orc.peoplesainetwork.com/privkey.pem;
    
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    
    location / {
        proxy_pass http://127.0.0.1:9000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
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
    
    location /health {
        proxy_pass http://127.0.0.1:9000/api/v1/health;
        proxy_set_header Host $host;
        access_log off;
    }
    
    location /status {
        proxy_pass http://127.0.0.1:9000/api/v1/status;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF
        
        sudo nginx -t && sudo systemctl reload nginx
        
        # Enable auto-renewal
        sudo systemctl enable certbot.timer
        sudo systemctl start certbot.timer
        
        SSL_ENABLED=true
    else
        echo "❌ SSL certificate failed - continuing with HTTP only"
        SSL_ENABLED=false
    fi
else
    echo "1️⃣2️⃣ Skipping SSL setup (HTTP not working properly)"
    SSL_ENABLED=false
fi

# Step 13: Final testing
echo "1️⃣3️⃣ Final testing and summary..."
sleep 3

echo ""
echo "🎯 SETUP SUMMARY"
echo "================"

# Test orchestrator
if curl -s --connect-timeout 5 http://localhost:9000/api/v1/health >/dev/null 2>&1; then
    echo "✅ Orchestrator: Running on port 9000"
else
    echo "❌ Orchestrator: Not responding"
fi

# Test HTTP access
if curl -s --connect-timeout 5 http://orc.peoplesainetwork.com/health >/dev/null 2>&1; then
    echo "✅ HTTP Access: Working"
else
    echo "❌ HTTP Access: Not working (firewall/security group issue)"
fi

# Test HTTPS access
if [ "$SSL_ENABLED" = true ]; then
    if curl -s --connect-timeout 5 https://orc.peoplesainetwork.com/health >/dev/null 2>&1; then
        echo "✅ HTTPS Access: Working"
    else
        echo "❌ HTTPS Access: Not working"
    fi
fi

echo ""
echo "🌐 ACCESS URLS:"
if [ "$SSL_ENABLED" = true ]; then
    echo "   🔒 https://orc.peoplesainetwork.com (Primary)"
    echo "   🔗 http://orc.peoplesainetwork.com (Redirects to HTTPS)"
else
    echo "   🔗 http://orc.peoplesainetwork.com"
fi
echo "   🔧 Direct: http://3.25.107.210:9000 (for testing)"

echo ""
echo "🔧 NEXT STEPS:"
if [ "$ORCHESTRATOR_RUNNING" != true ]; then
    echo "   ❗ Fix orchestrator service:"
    echo "     sudo journalctl -u web4ai-orchestrator -f"
    echo "     sudo systemctl restart web4ai-orchestrator"
fi

if [ "$HTTP_WORKING" != true ]; then
    echo "   ❗ Fix external access (likely firewall/security group):"
    echo "     - Check AWS Security Group allows HTTP (port 80) and HTTPS (port 443)"
    echo "     - Check UFW: sudo ufw status"
    echo "     - Test direct: curl http://3.25.107.210/health"
fi

if [ "$SSL_ENABLED" != true ] && [ "$HTTP_WORKING" = true ]; then
    echo "   🔒 Retry SSL setup:"
    echo "     sudo certbot --nginx -d orc.peoplesainetwork.com"
fi

echo ""
echo "📋 MANAGEMENT COMMANDS:"
echo "   sudo systemctl status web4ai-orchestrator"
echo "   sudo journalctl -u web4ai-orchestrator -f"
echo "   sudo systemctl restart web4ai-orchestrator"
echo "   curl http://localhost:9000/api/v1/health"

echo ""
echo "🎉 Setup completed! Check the status above and fix any issues."

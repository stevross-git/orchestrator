#!/bin/bash
# immediate-domain-setup.sh - Quick setup without waiting for DNS/SSL

echo "⚡ Immediate Domain Setup for orc.peoplesainetwork.com"
echo "====================================================="

# Step 1: Create basic nginx configuration (HTTP only)
echo "1️⃣ Creating basic nginx configuration..."
sudo tee /etc/nginx/sites-available/orc.peoplesainetwork.com > /dev/null << 'EOF'
# Basic HTTP configuration for orc.peoplesainetwork.com
server {
    listen 80;
    listen [::]:80;
    server_name orc.peoplesainetwork.com;
    
    # Main application proxy
    location / {
        proxy_pass http://127.0.0.1:9000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Host $host;
        
        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
    
    # API endpoints with CORS
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
        
        # Handle preflight requests
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
    
    # Status endpoint
    location /status {
        proxy_pass http://127.0.0.1:9000/api/v1/status;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

# Also listen on default port 80 for any domain (fallback)
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

# Step 2: Enable the configuration
echo "2️⃣ Enabling nginx configuration..."
sudo rm -f /etc/nginx/sites-enabled/default
sudo rm -f /etc/nginx/sites-enabled/web4ai-orchestrator
sudo rm -f /etc/nginx/sites-enabled/orc.peoplesainetwork.com.temp
sudo ln -sf /etc/nginx/sites-available/orc.peoplesainetwork.com /etc/nginx/sites-enabled/

# Step 3: Test and reload nginx
echo "3️⃣ Testing and reloading nginx..."
sudo nginx -t
if [ $? -eq 0 ]; then
    sudo systemctl reload nginx
    echo "✅ Nginx configuration updated"
else
    echo "❌ Nginx configuration error"
    exit 1
fi

# Step 4: Update orchestrator config
echo "4️⃣ Updating orchestrator configuration..."
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
  external_url: "http://orc.peoplesainetwork.com"

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

# Step 5: Restart orchestrator
echo "5️⃣ Restarting orchestrator service..."
sudo systemctl restart web4ai-orchestrator

# Step 6: Test the setup
echo "6️⃣ Testing the setup..."
sleep 3

# Get server IP
server_ip=$(curl -s ipinfo.io/ip 2>/dev/null || curl -s icanhazip.com 2>/dev/null)

echo "🔍 Testing direct IP access..."
if curl -s --connect-timeout 5 http://$server_ip/health >/dev/null 2>&1; then
    echo "✅ Direct IP access working: http://$server_ip"
    response=$(curl -s http://$server_ip/health)
    echo "   Health response: $response"
else
    echo "❌ Direct IP access failed"
fi

echo ""
echo "🔍 Testing domain access (if DNS is configured)..."
if curl -s --connect-timeout 5 http://orc.peoplesainetwork.com/health >/dev/null 2>&1; then
    echo "✅ Domain access working: http://orc.peoplesainetwork.com"
    response=$(curl -s http://orc.peoplesainetwork.com/health)
    echo "   Health response: $response"
else
    echo "⚠️ Domain access not working yet (DNS may not be configured)"
fi

# Step 7: Show status
echo ""
echo "📊 Current Status:"
echo "=================="
sudo systemctl status web4ai-orchestrator --no-pager -l | head -10
echo ""
sudo systemctl status nginx --no-pager -l | head -5

echo ""
echo "🎯 SETUP COMPLETE!"
echo "=================="
echo ""
echo "📍 Your Web4AI Orchestrator is accessible at:"
echo "   🌐 http://$server_ip (Direct IP - Always works)"
echo "   🌐 http://orc.peoplesainetwork.com (Domain - If DNS configured)"
echo ""
echo "🔗 Key URLs:"
echo "   ❤️ Health: http://$server_ip/health"
echo "   📋 Status: http://$server_ip/status" 
echo "   🔌 API: http://$server_ip/api/v1/"
echo ""
echo "🔧 To add SSL/HTTPS later:"
echo "   1. Make sure DNS points to $server_ip"
echo "   2. Run: sudo certbot --nginx -d orc.peoplesainetwork.com"
echo ""
echo "📋 Management Commands:"
echo "   sudo systemctl status web4ai-orchestrator"
echo "   sudo journalctl -u web4ai-orchestrator -f"
echo "   sudo systemctl restart web4ai-orchestrator"
echo ""
echo "✅ Ready to connect your Enhanced Nodes!"

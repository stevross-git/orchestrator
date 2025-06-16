#!/bin/bash
# fix-ssl-setup.sh - Fix the SSL configuration issue

echo "🔧 Fixing SSL Setup for orc.peoplesainetwork.com"
echo "==============================================="

echo "1️⃣ Creating HTTP-only configuration first..."
sudo tee /etc/nginx/sites-available/orc.peoplesainetwork.com > /dev/null << 'EOF'
# HTTP configuration for orc.peoplesainetwork.com (Step 1: Before SSL)
server {
    listen 80;
    listen [::]:80;
    server_name orc.peoplesainetwork.com;
    
    # Allow Let's Encrypt challenge
    location /.well-known/acme-challenge/ {
        root /var/www/html;
        allow all;
    }
    
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
    
    # Health check endpoint
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
EOF

echo "2️⃣ Testing nginx configuration..."
sudo nginx -t
if [ $? -ne 0 ]; then
    echo "❌ Nginx configuration still has errors"
    exit 1
fi

echo "3️⃣ Reloading nginx..."
sudo systemctl reload nginx

echo "4️⃣ Creating web root for Let's Encrypt..."
sudo mkdir -p /var/www/html/.well-known/acme-challenge
sudo chown -R www-data:www-data /var/www/html

echo "5️⃣ Testing HTTP access..."
sleep 3
if curl -s --connect-timeout 10 http://orc.peoplesainetwork.com/health >/dev/null 2>&1; then
    echo "✅ HTTP access working"
    response=$(curl -s http://orc.peoplesainetwork.com/health)
    echo "   Response: $response"
else
    echo "❌ HTTP access failed - checking orchestrator status..."
    sudo systemctl status web4ai-orchestrator --no-pager -l
    echo "Continuing with SSL setup anyway..."
fi

echo "6️⃣ Obtaining SSL certificate..."
sudo certbot certonly \
    --webroot \
    --webroot-path=/var/www/html \
    -d orc.peoplesainetwork.com \
    --non-interactive \
    --agree-tos \
    --email admin@peoplesainetwork.com \
    --keep-until-expiring

if [ $? -eq 0 ]; then
    echo "✅ SSL certificate obtained successfully"
    
    echo "7️⃣ Creating HTTPS configuration..."
    sudo tee /etc/nginx/sites-available/orc.peoplesainetwork.com > /dev/null << 'EOF'
# HTTP to HTTPS redirect
server {
    listen 80;
    listen [::]:80;
    server_name orc.peoplesainetwork.com;
    
    # Allow Let's Encrypt challenge
    location /.well-known/acme-challenge/ {
        root /var/www/html;
        allow all;
    }
    
    # Redirect all other traffic to HTTPS
    location / {
        return 301 https://$server_name$request_uri;
    }
}

# HTTPS configuration
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name orc.peoplesainetwork.com;
    
    # SSL configuration
    ssl_certificate /etc/letsencrypt/live/orc.peoplesainetwork.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/orc.peoplesainetwork.com/privkey.pem;
    
    # SSL settings
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-RSA-AES128-SHA256:ECDHE-RSA-AES256-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    
    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options DENY always;
    add_header X-Content-Type-Options nosniff always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    
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
    
    # Health check endpoint
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
    
    # Dashboard
    location /dashboard {
        proxy_pass http://127.0.0.1:9000/dashboard;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF
    
    echo "8️⃣ Testing HTTPS configuration..."
    sudo nginx -t
    if [ $? -eq 0 ]; then
        echo "✅ HTTPS configuration valid"
        sudo systemctl reload nginx
    else
        echo "❌ HTTPS configuration error"
        exit 1
    fi
    
    echo "9️⃣ Setting up auto-renewal..."
    sudo systemctl enable certbot.timer
    sudo systemctl start certbot.timer
    
else
    echo "❌ Failed to obtain SSL certificate"
    echo "   Continuing with HTTP-only configuration"
fi

echo "🔟 Updating orchestrator configuration..."
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

echo "1️⃣1️⃣ Restarting orchestrator service..."
sudo systemctl restart web4ai-orchestrator

echo "1️⃣2️⃣ Final testing..."
sleep 5

echo "🔍 Testing HTTP..."
if curl -s --connect-timeout 10 http://orc.peoplesainetwork.com/health >/dev/null 2>&1; then
    echo "✅ HTTP working"
    response=$(curl -s http://orc.peoplesainetwork.com/health)
    echo "   Response: $response"
else
    echo "❌ HTTP not working"
fi

if [ -f "/etc/letsencrypt/live/orc.peoplesainetwork.com/fullchain.pem" ]; then
    echo "🔍 Testing HTTPS..."
    if curl -s --connect-timeout 10 https://orc.peoplesainetwork.com/health >/dev/null 2>&1; then
        echo "✅ HTTPS working"
        response=$(curl -s https://orc.peoplesainetwork.com/health)
        echo "   Response: $response"
    else
        echo "❌ HTTPS not working"
    fi
fi

echo ""
echo "🎉 SETUP COMPLETE!"
echo "=================="
echo ""
echo "🌐 Your Web4AI Orchestrator is now live at:"
if [ -f "/etc/letsencrypt/live/orc.peoplesainetwork.com/fullchain.pem" ]; then
    echo "   🔒 https://orc.peoplesainetwork.com (Primary - HTTPS)"
    echo "   🔗 http://orc.peoplesainetwork.com (Redirects to HTTPS)"
else
    echo "   🔗 http://orc.peoplesainetwork.com (HTTP only)"
fi
echo ""
echo "🔗 Key URLs:"
echo "   ❤️ Health Check: https://orc.peoplesainetwork.com/health"
echo "   📊 Status: https://orc.peoplesainetwork.com/status"
echo "   🎛️ Dashboard: https://orc.peoplesainetwork.com/dashboard"
echo "   🔌 API Base: https://orc.peoplesainetwork.com/api/v1/"
echo ""
echo "🔧 Management Commands:"
echo "   sudo systemctl status web4ai-orchestrator"
echo "   sudo journalctl -u web4ai-orchestrator -f"
echo "   sudo systemctl restart web4ai-orchestrator"
echo ""
echo "🎊 Your Web4AI Orchestrator is now live!"

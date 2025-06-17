#!/bin/bash
# setup-domain.sh - Configure orc.peoplesainetwork.com with SSL

echo "🌐 Setting up orc.peoplesainetwork.com"
echo "======================================"

# Step 1: Install Certbot for SSL certificates
echo "1️⃣ Installing Certbot for SSL certificates..."
sudo apt update
sudo apt install -y certbot python3-certbot-nginx

# Step 2: Create nginx configuration for the domain
echo "2️⃣ Creating nginx configuration for orc.peoplesainetwork.com..."
sudo tee /etc/nginx/sites-available/orc.peoplesainetwork.com > /dev/null << 'EOF'
# HTTP configuration (will be redirected to HTTPS)
server {
    listen 80;
    listen [::]:80;
    server_name orc.peoplesainetwork.com;
    
    # Allow Let's Encrypt challenge
    location /.well-known/acme-challenge/ {
        root /var/www/html;
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
    
    # SSL configuration (will be managed by Certbot)
    ssl_certificate /etc/letsencrypt/live/orc.peoplesainetwork.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/orc.peoplesainetwork.com/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;
    
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
        
        # Buffer settings
        proxy_buffering on;
        proxy_buffer_size 128k;
        proxy_buffers 4 256k;
        proxy_busy_buffers_size 256k;
    }
    
    # API endpoints with CORS
    location /api/ {
        proxy_pass http://127.0.0.1:9000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # CORS headers for API
        add_header Access-Control-Allow-Origin * always;
        add_header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, OPTIONS" always;
        add_header Access-Control-Allow-Headers "Content-Type, Authorization, X-Requested-With" always;
        add_header Access-Control-Max-Age 3600 always;
        
        # Handle preflight requests
        if ($request_method = 'OPTIONS') {
            return 204;
        }
    }
    
    # Health check endpoint (no auth required)
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
    
    # Static files (if any)
    location /static/ {
        proxy_pass http://127.0.0.1:9000/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
    
    # Robots.txt
    location /robots.txt {
        return 200 "User-agent: *\nDisallow: /api/\nAllow: /\n";
        add_header Content-Type text/plain;
    }
}
EOF

# Step 3: Remove default nginx site and enable our domain
echo "3️⃣ Enabling domain configuration..."
sudo rm -f /etc/nginx/sites-enabled/default
sudo rm -f /etc/nginx/sites-enabled/web4ai-orchestrator
sudo ln -sf /etc/nginx/sites-available/orc.peoplesainetwork.com /etc/nginx/sites-enabled/

# Step 4: Test nginx configuration
echo "4️⃣ Testing nginx configuration..."
sudo nginx -t
if [ $? -ne 0 ]; then
    echo "❌ Nginx configuration error. Exiting."
    exit 1
fi

# Step 5: Create initial HTTP-only configuration for SSL certificate generation
echo "5️⃣ Creating initial HTTP configuration for SSL setup..."
sudo tee /etc/nginx/sites-available/orc.peoplesainetwork.com.temp > /dev/null << 'EOF'
server {
    listen 80;
    listen [::]:80;
    server_name orc.peoplesainetwork.com;
    
    # Allow Let's Encrypt challenge
    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }
    
    # Temporary proxy for testing
    location / {
        proxy_pass http://127.0.0.1:9000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF

# Use temp configuration first
sudo rm -f /etc/nginx/sites-enabled/orc.peoplesainetwork.com
sudo ln -sf /etc/nginx/sites-available/orc.peoplesainetwork.com.temp /etc/nginx/sites-enabled/
sudo systemctl reload nginx

# Step 6: Check if DNS is properly configured
echo "6️⃣ Checking DNS configuration..."
if nslookup orc.peoplesainetwork.com >/dev/null 2>&1; then
    echo "✅ DNS appears to be configured"
    ip_address=$(dig +short orc.peoplesainetwork.com | tail -n1)
    current_ip=$(curl -s ipinfo.io/ip 2>/dev/null || curl -s icanhazip.com 2>/dev/null)
    
    if [ "$ip_address" = "$current_ip" ]; then
        echo "✅ DNS points to this server ($current_ip)"
        DNS_READY=true
    else
        echo "⚠️ DNS points to $ip_address but this server is $current_ip"
        echo "   Make sure your DNS A record points to $current_ip"
        DNS_READY=false
    fi
else
    echo "⚠️ DNS lookup failed for orc.peoplesainetwork.com"
    echo "   Make sure you have an A record pointing to this server's IP"
    DNS_READY=false
fi

# Step 7: Get SSL certificate
if [ "$DNS_READY" = true ]; then
    echo "7️⃣ Obtaining SSL certificate..."
    sudo certbot certonly --nginx -d orc.peoplesainetwork.com --non-interactive --agree-tos --email admin@peoplesainetwork.com
    
    if [ $? -eq 0 ]; then
        echo "✅ SSL certificate obtained successfully"
        
        # Switch to the full HTTPS configuration
        sudo rm -f /etc/nginx/sites-enabled/orc.peoplesainetwork.com.temp
        sudo ln -sf /etc/nginx/sites-available/orc.peoplesainetwork.com /etc/nginx/sites-enabled/
        sudo nginx -t && sudo systemctl reload nginx
        
        echo "✅ HTTPS configuration enabled"
    else
        echo "❌ Failed to obtain SSL certificate"
        echo "   Continuing with HTTP-only configuration"
    fi
else
    echo "7️⃣ Skipping SSL certificate (DNS not ready)"
    echo "   You can run this later: sudo certbot --nginx -d orc.peoplesainetwork.com"
fi

# Step 8: Update orchestrator configuration for the domain
echo "8️⃣ Updating orchestrator configuration..."
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
  external_url: "https://orc.peoplesainetwork.com"

performance:
  cpu_threshold: 80
  memory_threshold: 85
  optimization_enabled: true
  
cors:
  allowed_origins:
    - "https://orc.peoplesainetwork.com"
    - "http://orc.peoplesainetwork.com"
    - "*"  # Remove this in production if needed

security:
  api_key_required: false
  cors_enabled: true
  rate_limiting: true
  max_requests_per_minute: 100
  ssl_enabled: true
  domain: "orc.peoplesainetwork.com"

logging:
  level: "INFO"
  file: "logs/orchestrator.log"
  console_output: true
  access_log: true

database:
  type: "sqlite"
  path: "data/orchestrator.db"
  backup_enabled: true
  backup_interval: 3600
EOF

# Step 9: Restart services
echo "9️⃣ Restarting services..."
sudo systemctl restart web4ai-orchestrator
sudo systemctl reload nginx

# Step 10: Set up automatic SSL renewal
echo "🔟 Setting up automatic SSL renewal..."
sudo systemctl enable certbot.timer
sudo systemctl start certbot.timer

# Step 11: Configure firewall (if UFW is active)
echo "1️⃣1️⃣ Configuring firewall..."
if sudo ufw status | grep -q "Status: active"; then
    sudo ufw allow 'Nginx Full'
    sudo ufw allow 22/tcp
    sudo ufw allow 9000/tcp
    echo "✅ Firewall configured"
else
    echo "ℹ️ UFW not active, skipping firewall configuration"
fi

# Step 12: Test the setup
echo "1️⃣2️⃣ Testing the setup..."
sleep 3

echo "🔍 Testing HTTP connection..."
if curl -s --connect-timeout 10 http://orc.peoplesainetwork.com/health >/dev/null 2>&1; then
    echo "✅ HTTP connection working"
    http_response=$(curl -s http://orc.peoplesainetwork.com/health)
    echo "   Response: $http_response"
else
    echo "❌ HTTP connection failed"
fi

if [ "$DNS_READY" = true ] && [ -f "/etc/letsencrypt/live/orc.peoplesainetwork.com/fullchain.pem" ]; then
    echo "🔍 Testing HTTPS connection..."
    if curl -s --connect-timeout 10 https://orc.peoplesainetwork.com/health >/dev/null 2>&1; then
        echo "✅ HTTPS connection working"
        https_response=$(curl -s https://orc.peoplesainetwork.com/health)
        echo "   Response: $https_response"
    else
        echo "❌ HTTPS connection failed"
    fi
fi

# Final summary
echo ""
echo "🎉 DOMAIN SETUP COMPLETE!"
echo "========================="
echo ""
echo "🌐 Your Web4AI Orchestrator is now available at:"
echo "   🔗 https://orc.peoplesainetwork.com"
echo "   🔗 http://orc.peoplesainetwork.com (redirects to HTTPS)"
echo ""
echo "📊 Key URLs:"
echo "   🏠 Main Site: https://orc.peoplesainetwork.com"
echo "   ❤️ Health Check: https://orc.peoplesainetwork.com/health"
echo "   📋 Status: https://orc.peoplesainetwork.com/status"
echo "   🎛️ Dashboard: https://orc.peoplesainetwork.com/dashboard"
echo "   🔌 API Base: https://orc.peoplesainetwork.com/api/v1/"
echo ""
echo "🔧 Management:"
echo "   📋 Check status: sudo systemctl status web4ai-orchestrator"
echo "   📝 View logs: sudo journalctl -u web4ai-orchestrator -f"
echo "   🔄 Restart: sudo systemctl restart web4ai-orchestrator"
echo "   🌐 Nginx status: sudo systemctl status nginx"
echo ""
echo "🔒 SSL Certificate:"
if [ -f "/etc/letsencrypt/live/orc.peoplesainetwork.com/fullchain.pem" ]; then
    echo "   ✅ SSL certificate installed and active"
    echo "   🔄 Auto-renewal enabled via systemd timer"
    echo "   📅 Next renewal check: $(sudo certbot certificates | grep -A1 orc.peoplesainetwork.com | grep Expiry || echo 'Run: sudo certbot certificates')"
else
    echo "   ⚠️ SSL certificate not installed"
    echo "   📝 To install: sudo certbot --nginx -d orc.peoplesainetwork.com"
fi
echo ""
echo "🎯 Next Steps:"
echo "   1. Test all URLs above"
echo "   2. Configure your Enhanced Nodes to connect to: https://orc.peoplesainetwork.com"
echo "   3. Update any client applications to use the new domain"
echo ""
if [ "$DNS_READY" != true ]; then
    echo "⚠️ IMPORTANT: Make sure your DNS A record for orc.peoplesainetwork.com points to:"
    echo "   IP Address: $(curl -s ipinfo.io/ip 2>/dev/null || curl -s icanhazip.com 2>/dev/null)"
    echo ""
fi
echo "🎊 Your Web4AI Orchestrator is now live at orc.peoplesainetwork.com!"

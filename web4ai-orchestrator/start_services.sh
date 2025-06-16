#!/bin/bash
# start-services.sh - Start and verify all Web4AI Orchestrator services

echo "🚀 Starting Web4AI Orchestrator Services"
echo "========================================"

# Step 1: Start nginx
echo "1️⃣ Starting nginx service..."
sudo systemctl start nginx
if [ $? -eq 0 ]; then
    echo "✅ nginx started successfully"
    sudo systemctl enable nginx
    echo "✅ nginx enabled for auto-start"
else
    echo "❌ Failed to start nginx"
    echo "🔍 Checking nginx status..."
    sudo systemctl status nginx --no-pager -l
fi

# Step 2: Start the Web4AI Orchestrator service
echo ""
echo "2️⃣ Starting web4ai-orchestrator service..."
sudo systemctl start web4ai-orchestrator
if [ $? -eq 0 ]; then
    echo "✅ web4ai-orchestrator started successfully"
else
    echo "❌ Failed to start web4ai-orchestrator"
    echo "🔍 Checking service status..."
    sudo systemctl status web4ai-orchestrator --no-pager -l
fi

# Step 3: Enable auto-start
echo ""
echo "3️⃣ Enabling auto-start for services..."
sudo systemctl enable web4ai-orchestrator
sudo systemctl enable nginx

# Step 4: Check service status
echo ""
echo "4️⃣ Checking service status..."
echo "📊 Web4AI Orchestrator Status:"
sudo systemctl status web4ai-orchestrator --no-pager -l

echo ""
echo "📊 Nginx Status:"
sudo systemctl status nginx --no-pager -l

# Step 5: Test network connectivity
echo ""
echo "5️⃣ Testing network connectivity..."

# Test direct connection to orchestrator
echo "🔍 Testing direct orchestrator connection (port 9000)..."
timeout 5 bash -c "</dev/tcp/localhost/9000" 2>/dev/null
if [ $? -eq 0 ]; then
    echo "✅ Port 9000 is open"
else
    echo "❌ Cannot connect to port 9000"
fi

# Test nginx proxy
echo "🔍 Testing nginx proxy (port 80)..."
timeout 5 bash -c "</dev/tcp/localhost/80" 2>/dev/null
if [ $? -eq 0 ]; then
    echo "✅ Port 80 is open"
else
    echo "❌ Cannot connect to port 80"
fi

# Step 6: Test API endpoints
echo ""
echo "6️⃣ Testing API endpoints..."

# Wait a moment for services to fully start
sleep 3

# Test health endpoint directly
echo "🔍 Testing direct health endpoint..."
curl -s -o /dev/null -w "%{http_code}" http://localhost:9000/api/v1/health
if [ $? -eq 0 ]; then
    echo " ✅ Direct health endpoint responding"
else
    echo " ❌ Direct health endpoint not responding"
fi

# Test health endpoint through nginx
echo "🔍 Testing health endpoint through nginx..."
curl -s -o /dev/null -w "%{http_code}" http://localhost/api/v1/health
if [ $? -eq 0 ]; then
    echo " ✅ Nginx proxy health endpoint responding"
else
    echo " ❌ Nginx proxy health endpoint not responding"
fi

# Step 7: Show service logs
echo ""
echo "7️⃣ Recent service logs..."
echo "📋 Web4AI Orchestrator logs (last 10 lines):"
sudo journalctl -u web4ai-orchestrator -n 10 --no-pager

echo ""
echo "📋 Nginx error logs (if any):"
sudo tail -n 5 /var/log/nginx/error.log 2>/dev/null || echo "No nginx error logs found"

# Step 8: Display service information
echo ""
echo "8️⃣ Service Information"
echo "====================="
echo "🎯 Orchestrator Direct URL: http://localhost:9000"
echo "🌐 Orchestrator via Nginx: http://localhost"
echo "📊 Health Check: http://localhost/api/v1/health"
echo "📋 Status Check: http://localhost/api/v1/status"
echo "📱 Dashboard: http://localhost/dashboard"

# Step 9: Show monitoring commands
echo ""
echo "9️⃣ Monitoring Commands"
echo "====================="
echo "📊 Check orchestrator status: sudo systemctl status web4ai-orchestrator"
echo "📋 View orchestrator logs: sudo journalctl -u web4ai-orchestrator -f"
echo "🔄 Restart orchestrator: sudo systemctl restart web4ai-orchestrator"
echo "🛑 Stop orchestrator: sudo systemctl stop web4ai-orchestrator"
echo ""
echo "🌐 Check nginx status: sudo systemctl status nginx"
echo "📋 View nginx logs: sudo journalctl -u nginx -f"
echo "🔄 Restart nginx: sudo systemctl restart nginx"

# Step 10: Final verification
echo ""
echo "🔟 Final Verification"
echo "===================="
echo "🔍 Making test API call..."

# Try to get orchestrator status
response=$(curl -s http://localhost:9000/api/v1/health 2>/dev/null)
if [ $? -eq 0 ] && [[ $response == *"healthy"* ]]; then
    echo "✅ API is working! Response: $response"
    echo ""
    echo "🎉 SUCCESS! Web4AI Orchestrator is running properly!"
    echo ""
    echo "🎯 Next Steps:"
    echo "1. Visit http://localhost to access the orchestrator"
    echo "2. Check http://localhost/api/v1/status for detailed status"
    echo "3. Start your enhanced nodes to connect to the orchestrator"
    echo "4. Monitor logs with: sudo journalctl -u web4ai-orchestrator -f"
else
    echo "⚠️ API test failed. Checking what's happening..."
    echo "🔍 Orchestrator process status:"
    ps aux | grep orchestrator | grep -v grep
    echo ""
    echo "🔍 Port 9000 status:"
    netstat -tlnp | grep :9000 || ss -tlnp | grep :9000
    echo ""
    echo "📋 Recent logs:"
    sudo journalctl -u web4ai-orchestrator -n 20 --no-pager
fi

echo ""
echo "📞 Need help? Check the logs or run:"
echo "   sudo systemctl status web4ai-orchestrator"
echo "   sudo journalctl -u web4ai-orchestrator -f"

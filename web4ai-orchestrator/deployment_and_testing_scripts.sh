#!/bin/bash
# deploy.sh - Production Deployment Script

set -euo pipefail

# Configuration
ORCHESTRATOR_VERSION="1.0.0"
DEPLOYMENT_ENV="${1:-production}"
CONFIG_FILE="orchestrator_config_${DEPLOYMENT_ENV}.yaml"
BACKUP_DIR="/opt/web4ai/backups"
LOG_DIR="/var/log/web4ai"
SERVICE_NAME="web4ai-orchestrator"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
    exit 1
}

# Check prerequisites
check_prerequisites() {
    log "Checking prerequisites..."
    
    # Check if running as root or with sudo
    if [[ $EUID -ne 0 ]]; then
        error "This script must be run as root or with sudo"
    fi
    
    # Check required commands
    for cmd in python3 pip3 systemctl nginx; do
        if ! command -v $cmd &> /dev/null; then
            error "$cmd is required but not installed"
        fi
    done
    
    # Check Python version
    python_version=$(python3 -c "import sys; print('.'.join(map(str, sys.version_info[:2])))")
    if ! python3 -c "import sys; exit(0 if sys.version_info >= (3, 8) else 1)"; then
        error "Python 3.8+ is required, found $python_version"
    fi
    
    log "Prerequisites check passed"
}

# Create system user and directories
setup_system() {
    log "Setting up system..."
    
    # Create web4ai user if it doesn't exist
    if ! id "web4ai" &>/dev/null; then
        useradd -r -s /bin/bash -d /opt/web4ai -m web4ai
        log "Created web4ai user"
    fi
    
    # Create directories
    mkdir -p /opt/web4ai/{orchestrator,logs,backups,config}
    mkdir -p $LOG_DIR
    mkdir -p $BACKUP_DIR
    
    # Set permissions
    chown -R web4ai:web4ai /opt/web4ai
    chown -R web4ai:web4ai $LOG_DIR
    chmod 755 /opt/web4ai
    chmod 750 /opt/web4ai/logs
    chmod 750 $LOG_DIR
    
    log "System setup completed"
}

# Install Python dependencies
install_dependencies() {
    log "Installing Python dependencies..."
    
    # Create virtual environment
    if [ ! -d "/opt/web4ai/venv" ]; then
        python3 -m venv /opt/web4ai/venv
        log "Created virtual environment"
    fi
    
    # Activate virtual environment and install packages
    source /opt/web4ai/venv/bin/activate
    
    # Upgrade pip
    pip install --upgrade pip
    
    # Install orchestrator dependencies
    pip install -r requirements.txt
    
    log "Dependencies installed"
}

# Deploy application files
deploy_application() {
    log "Deploying application files..."
    
    # Stop service if running
    if systemctl is-active --quiet $SERVICE_NAME; then
        systemctl stop $SERVICE_NAME
        log "Stopped existing service"
    fi
    
    # Copy application files
    cp -r web4ai_orchestrator.py orchestrator_api.py /opt/web4ai/orchestrator/
    cp -r templates static /opt/web4ai/orchestrator/ 2>/dev/null || true
    
    # Copy configuration
    if [ -f "$CONFIG_FILE" ]; then
        cp $CONFIG_FILE /opt/web4ai/config/orchestrator_config.yaml
        log "Deployed configuration file"
    else
        warn "Configuration file $CONFIG_FILE not found, using default"
        python3 /opt/web4ai/orchestrator/orchestrator_api.py --generate-config
        mv orchestrator_config.yaml /opt/web4ai/config/
    fi
    
    # Set permissions
    chown -R web4ai:web4ai /opt/web4ai/orchestrator
    chmod +x /opt/web4ai/orchestrator/*.py
    
    log "Application files deployed"
}

# Create systemd service
create_service() {
    log "Creating systemd service..."
    
    cat > /etc/systemd/system/$SERVICE_NAME.service << EOF
[Unit]
Description=Web4AI Orchestrator
After=network.target redis.service
Wants=redis.service

[Service]
Type=simple
User=web4ai
Group=web4ai
WorkingDirectory=/opt/web4ai/orchestrator
Environment=PATH=/opt/web4ai/venv/bin
Environment=PYTHONPATH=/opt/web4ai/orchestrator
ExecStart=/opt/web4ai/venv/bin/python orchestrator_api.py --config /opt/web4ai/config/orchestrator_config.yaml
ExecReload=/bin/kill -HUP \$MAINPID
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=web4ai-orchestrator

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/web4ai/logs /var/log/web4ai /opt/web4ai/backups

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    systemctl enable $SERVICE_NAME
    
    log "Systemd service created"
}

# Configure nginx reverse proxy
configure_nginx() {
    log "Configuring nginx..."
    
    cat > /etc/nginx/sites-available/web4ai-orchestrator << EOF
server {
    listen 80;
    server_name orchestrator.web4ai.local localhost;
    
    # API proxy
    location /api/ {
        proxy_pass http://127.0.0.1:9000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
    }
    
    # WebSocket proxy
    location /ws {
        proxy_pass http://127.0.0.1:9001;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
    }
    
    # Dashboard
    location / {
        proxy_pass http://127.0.0.1:9000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
    
    # Health check (bypass proxy for direct access)
    location /health {
        proxy_pass http://127.0.0.1:9000/api/v1/health;
        access_log off;
    }
}
EOF

    # Enable site
    ln -sf /etc/nginx/sites-available/web4ai-orchestrator /etc/nginx/sites-enabled/
    
    # Test and reload nginx
    nginx -t
    systemctl reload nginx
    
    log "Nginx configured"
}

# Start services
start_services() {
    log "Starting services..."
    
    # Start orchestrator
    systemctl start $SERVICE_NAME
    
    # Wait for service to start
    sleep 5
    
    # Check if service is running
    if systemctl is-active --quiet $SERVICE_NAME; then
        log "Orchestrator service started successfully"
    else
        error "Failed to start orchestrator service"
    fi
    
    # Test health endpoint
    if curl -f http://localhost:9000/api/v1/health >/dev/null 2>&1; then
        log "Health check passed"
    else
        warn "Health check failed - service may still be starting"
    fi
}

# Create monitoring setup
setup_monitoring() {
    log "Setting up monitoring..."
    
    # Create log rotation
    cat > /etc/logrotate.d/web4ai << EOF
$LOG_DIR/*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 644 web4ai web4ai
    postrotate
        systemctl reload $SERVICE_NAME
    endscript
}
EOF

    # Create backup script
    cat > /opt/web4ai/backup.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/opt/web4ai/backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/orchestrator_backup_$DATE.tar.gz"

# Create backup
tar -czf $BACKUP_FILE \
    /opt/web4ai/config \
    /opt/web4ai/orchestrator \
    $LOG_DIR

# Keep only last 7 days of backups
find $BACKUP_DIR -name "orchestrator_backup_*.tar.gz" -mtime +7 -delete

echo "Backup created: $BACKUP_FILE"
EOF

    chmod +x /opt/web4ai/backup.sh
    chown web4ai:web4ai /opt/web4ai/backup.sh
    
    # Add to crontab
    (crontab -u web4ai -l 2>/dev/null; echo "0 2 * * * /opt/web4ai/backup.sh") | crontab -u web4ai -
    
    log "Monitoring setup completed"
}

# Firewall configuration
configure_firewall() {
    log "Configuring firewall..."
    
    if command -v ufw &> /dev/null; then
        ufw allow 80/tcp
        ufw allow 443/tcp
        ufw allow 9000/tcp
        ufw allow 9001/tcp
        log "UFW firewall rules added"
    elif command -v firewall-cmd &> /dev/null; then
        firewall-cmd --permanent --add-port=80/tcp
        firewall-cmd --permanent --add-port=443/tcp
        firewall-cmd --permanent --add-port=9000/tcp
        firewall-cmd --permanent --add-port=9001/tcp
        firewall-cmd --reload
        log "Firewalld rules added"
    else
        warn "No firewall detected - please configure manually"
    fi
}

# Main deployment function
main() {
    log "Starting Web4AI Orchestrator deployment (Environment: $DEPLOYMENT_ENV)"
    
    check_prerequisites
    setup_system
    install_dependencies
    deploy_application
    create_service
    configure_nginx
    setup_monitoring
    configure_firewall
    start_services
    
    log "Deployment completed successfully!"
    log "Orchestrator is available at:"
    log "  - Dashboard: http://localhost"
    log "  - API: http://localhost/api/v1"
    log "  - Health: http://localhost/health"
    log "  - Direct access: http://localhost:9000"
    
    log "Service management:"
    log "  - Status: systemctl status $SERVICE_NAME"
    log "  - Logs: journalctl -u $SERVICE_NAME -f"
    log "  - Restart: systemctl restart $SERVICE_NAME"
}

# Run main function
main "$@"

---
#!/bin/bash
# test_orchestrator.sh - Comprehensive Testing Script

set -euo pipefail

# Configuration
ORCHESTRATOR_URL="${ORCHESTRATOR_URL:-http://localhost:9000}"
API_KEY="${API_KEY:-}"
TEST_TIMEOUT=30

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Test statistics
TESTS_TOTAL=0
TESTS_PASSED=0
TESTS_FAILED=0

log() {
    echo -e "${BLUE}[TEST] $1${NC}"
}

success() {
    echo -e "${GREEN}[PASS] $1${NC}"
    ((TESTS_PASSED++))
}

fail() {
    echo -e "${RED}[FAIL] $1${NC}"
    ((TESTS_FAILED++))
}

warn() {
    echo -e "${YELLOW}[WARN] $1${NC}"
}

# API request helper
api_request() {
    local method="$1"
    local endpoint="$2"
    local data="${3:-}"
    local expected_status="${4:-200}"
    
    local auth_header=""
    if [ -n "$API_KEY" ]; then
        auth_header="-H Authorization: Bearer $API_KEY"
    fi
    
    local response
    local status_code
    
    if [ -n "$data" ]; then
        response=$(curl -s -w "HTTPSTATUS:%{http_code}" \
            -X "$method" \
            -H "Content-Type: application/json" \
            $auth_header \
            -d "$data" \
            "$ORCHESTRATOR_URL$endpoint" || echo "HTTPSTATUS:000")
    else
        response=$(curl -s -w "HTTPSTATUS:%{http_code}" \
            -X "$method" \
            $auth_header \
            "$ORCHESTRATOR_URL$endpoint" || echo "HTTPSTATUS:000")
    fi
    
    status_code=$(echo "$response" | grep -o "HTTPSTATUS:[0-9]*" | cut -d: -f2)
    body=$(echo "$response" | sed "s/HTTPSTATUS:[0-9]*//")
    
    if [ "$status_code" = "$expected_status" ]; then
        echo "$body"
        return 0
    else
        echo "Expected status $expected_status, got $status_code: $body" >&2
        return 1
    fi
}

# Test health endpoint
test_health() {
    log "Testing health endpoint..."
    ((TESTS_TOTAL++))
    
    if response=$(api_request GET "/api/v1/health"); then
        if echo "$response" | jq -e '.status == "healthy"' > /dev/null; then
            success "Health endpoint is working"
        else
            fail "Health endpoint returned incorrect status"
        fi
    else
        fail "Health endpoint is not accessible"
    fi
}

# Test status endpoint
test_status() {
    log "Testing status endpoint..."
    ((TESTS_TOTAL++))
    
    if response=$(api_request GET "/api/v1/status"); then
        if echo "$response" | jq -e '.success == true' > /dev/null; then
            success "Status endpoint is working"
            
            # Extract useful info
            orchestrator_id=$(echo "$response" | jq -r '.data.orchestrator_id')
            active_nodes=$(echo "$response" | jq -r '.data.nodes.active')
            log "Orchestrator ID: $orchestrator_id"
            log "Active nodes: $active_nodes"
        else
            fail "Status endpoint returned error"
        fi
    else
        fail "Status endpoint is not accessible"
    fi
}

# Test node registration
test_node_registration() {
    log "Testing node registration..."
    ((TESTS_TOTAL++))
    
    local node_id="test-node-$(date +%s)"
    local node_data='{
        "host": "127.0.0.1",
        "port": 8080,
        "node_type": "test_node",
        "capabilities": ["test_capability"],
        "version": "1.0.0-test"
    }'
    
    if response=$(api_request POST "/api/v1/nodes/$node_id/register" "$node_data"); then
        if echo "$response" | jq -e '.success == true' > /dev/null; then
            success "Node registration successful"
            
            # Test node retrieval
            log "Testing node retrieval..."
            ((TESTS_TOTAL++))
            if response=$(api_request GET "/api/v1/nodes/$node_id"); then
                if echo "$response" | jq -e '.success == true' > /dev/null; then
                    success "Node retrieval successful"
                else
                    fail "Node retrieval failed"
                fi
            else
                fail "Node retrieval request failed"
            fi
            
            # Cleanup: unregister node
            api_request DELETE "/api/v1/nodes/$node_id" "" "200" > /dev/null || true
        else
            fail "Node registration returned error"
        fi
    else
        fail "Node registration request failed"
    fi
}

# Test task submission
test_task_submission() {
    log "Testing task submission..."
    ((TESTS_TOTAL++))
    
    local task_data='{
        "task_type": "test_task",
        "priority": 3,
        "input_data": {"test": true},
        "timeout": 60
    }'
    
    if response=$(api_request POST "/api/v1/tasks" "$task_data"); then
        if echo "$response" | jq -e '.success == true' > /dev/null; then
            task_id=$(echo "$response" | jq -r '.task_id')
            success "Task submission successful (ID: $task_id)"
            
            # Test task retrieval
            log "Testing task retrieval..."
            ((TESTS_TOTAL++))
            if response=$(api_request GET "/api/v1/tasks/$task_id"); then
                if echo "$response" | jq -e '.success == true' > /dev/null; then
                    success "Task retrieval successful"
                else
                    fail "Task retrieval failed"
                fi
            else
                fail "Task retrieval request failed"
            fi
        else
            fail "Task submission returned error"
        fi
    else
        fail "Task submission request failed"
    fi
}

# Test metrics endpoint
test_metrics() {
    log "Testing metrics endpoint..."
    ((TESTS_TOTAL++))
    
    if response=$(api_request GET "/api/v1/metrics"); then
        if echo "$response" | jq -e '.success == true' > /dev/null; then
            success "Metrics endpoint is working"
            
            # Check for expected metrics
            network_utilization=$(echo "$response" | jq -r '.metrics.network.network_utilization')
            total_nodes=$(echo "$response" | jq -r '.metrics.nodes.total')
            log "Network utilization: $network_utilization"
            log "Total nodes: $total_nodes"
        else
            fail "Metrics endpoint returned error"
        fi
    else
        fail "Metrics endpoint is not accessible"
    fi
}

# Test configuration endpoints
test_configuration() {
    log "Testing configuration endpoints..."
    ((TESTS_TOTAL++))
    
    if response=$(api_request GET "/api/v1/config"); then
        if echo "$response" | jq -e '.success == true' > /dev/null; then
            success "Configuration retrieval successful"
            
            # Test configuration update
            log "Testing configuration update..."
            ((TESTS_TOTAL++))
            local config_update='{"network": {"max_nodes": 150}}'
            if response=$(api_request PUT "/api/v1/config" "$config_update"); then
                if echo "$response" | jq -e '.success == true' > /dev/null; then
                    success "Configuration update successful"
                else
                    fail "Configuration update returned error"
                fi
            else
                fail "Configuration update request failed"
            fi
        else
            fail "Configuration retrieval returned error"
        fi
    else
        fail "Configuration endpoint is not accessible"
    fi
}

# Test WebSocket connection
test_websocket() {
    log "Testing WebSocket connection..."
    ((TESTS_TOTAL++))
    
    # Get WebSocket info
    if response=$(api_request GET "/api/v1/websocket/info"); then
        ws_url=$(echo "$response" | jq -r '.websocket.url')
        log "WebSocket URL: $ws_url"
        
        # Simple WebSocket test using Python
        python3 << EOF
import asyncio
import websockets
import json
import sys

async def test_websocket():
    try:
        uri = "$ws_url"
        async with websockets.connect(uri, timeout=5) as websocket:
            # Wait for initial message
            message = await asyncio.wait_for(websocket.recv(), timeout=5)
            data = json.loads(message)
            if data.get('type') == 'initial_status':
                print("WebSocket test successful")
                sys.exit(0)
            else:
                print("Unexpected message type")
                sys.exit(1)
    except Exception as e:
        print(f"WebSocket test failed: {e}")
        sys.exit(1)

asyncio.run(test_websocket())
EOF
        
        if [ $? -eq 0 ]; then
            success "WebSocket connection test successful"
        else
            fail "WebSocket connection test failed"
        fi
    else
        fail "WebSocket info endpoint failed"
    fi
}

# Load testing
test_load() {
    log "Running load test..."
    ((TESTS_TOTAL++))
    
    local concurrent_requests=10
    local total_requests=100
    
    log "Sending $total_requests requests with $concurrent_requests concurrent connections..."
    
    # Use Apache Bench if available
    if command -v ab &> /dev/null; then
        if ab -n $total_requests -c $concurrent_requests -H "Content-Type: application/json" \
           "$ORCHESTRATOR_URL/api/v1/health" > /tmp/ab_results.txt 2>&1; then
            
            requests_per_sec=$(grep "Requests per second" /tmp/ab_results.txt | awk '{print $4}')
            time_per_request=$(grep "Time per request" /tmp/ab_results.txt | head -1 | awk '{print $4}')
            
            success "Load test completed - $requests_per_sec req/sec, ${time_per_request}ms per request"
        else
            fail "Load test failed"
        fi
    else
        # Simple curl-based load test
        local start_time=$(date +%s)
        local success_count=0
        
        for i in $(seq 1 $total_requests); do
            if curl -s -f "$ORCHESTRATOR_URL/api/v1/health" > /dev/null; then
                ((success_count++))
            fi
        done
        
        local end_time=$(date +%s)
        local duration=$((end_time - start_time))
        local rps=$((total_requests / duration))
        
        if [ $success_count -eq $total_requests ]; then
            success "Load test completed - $rps req/sec (simplified test)"
        else
            fail "Load test failed - only $success_count/$total_requests succeeded"
        fi
    fi
}

# Performance benchmark
benchmark_performance() {
    log "Running performance benchmark..."
    
    # Create test nodes
    local node_count=5
    local node_ids=()
    
    log "Creating $node_count test nodes..."
    for i in $(seq 1 $node_count); do
        local node_id="bench-node-$i"
        local node_data='{
            "host": "127.0.0.1",
            "port": '$(( 8080 + i ))',
            "node_type": "benchmark_node",
            "capabilities": ["benchmark"],
            "version": "1.0.0-bench"
        }'
        
        if api_request POST "/api/v1/nodes/$node_id/register" "$node_data" > /dev/null; then
            node_ids+=("$node_id")
            log "Created node: $node_id"
        fi
    done
    
    # Submit multiple tasks
    local task_count=50
    local task_ids=()
    
    log "Submitting $task_count test tasks..."
    local start_time=$(date +%s.%N)
    
    for i in $(seq 1 $task_count); do
        local task_data='{
            "task_type": "benchmark_task",
            "priority": 3,
            "input_data": {"iteration": '$i'},
            "timeout": 30
        }'
        
        if response=$(api_request POST "/api/v1/tasks" "$task_data"); then
            task_id=$(echo "$response" | jq -r '.task_id')
            task_ids+=("$task_id")
        fi
    done
    
    local end_time=$(date +%s.%N)
    local duration=$(echo "$end_time - $start_time" | bc)
    local tps=$(echo "scale=2; $task_count / $duration" | bc)
    
    log "Task submission rate: $tps tasks/second"
    
    # Cleanup
    log "Cleaning up test nodes..."
    for node_id in "${node_ids[@]}"; do
        api_request DELETE "/api/v1/nodes/$node_id" "" "200" > /dev/null || true
    done
}

# Generate test report
generate_report() {
    log "Generating test report..."
    
    local report_file="test_report_$(date +%Y%m%d_%H%M%S).txt"
    
    cat > "$report_file" << EOF
Web4AI Orchestrator Test Report
Generated: $(date)
Orchestrator URL: $ORCHESTRATOR_URL

Test Results:
=============
Total Tests: $TESTS_TOTAL
Passed: $TESTS_PASSED
Failed: $TESTS_FAILED
Success Rate: $(( TESTS_PASSED * 100 / TESTS_TOTAL ))%

Test Details:
=============
$(if [ $TESTS_PASSED -eq $TESTS_TOTAL ]; then
    echo "✅ All tests passed successfully!"
else
    echo "❌ Some tests failed. Check the output above for details."
fi)

System Information:
==================
Date: $(date)
User: $(whoami)
OS: $(uname -a)
Python: $(python3 --version)
Curl: $(curl --version | head -1)

Orchestrator Status:
===================
EOF

    # Add orchestrator status to report
    if response=$(api_request GET "/api/v1/status" 2>/dev/null); then
        echo "$response" | jq '.' >> "$report_file"
    else
        echo "Failed to retrieve orchestrator status" >> "$report_file"
    fi
    
    log "Test report saved to: $report_file"
}

# Main test function
main() {
    log "Starting Web4AI Orchestrator Test Suite"
    log "Target: $ORCHESTRATOR_URL"
    log "Timeout: ${TEST_TIMEOUT}s"
    
    # Basic functionality tests
    test_health
    test_status
    test_node_registration
    test_task_submission
    test_metrics
    test_configuration
    test_websocket
    
    # Performance tests
    test_load
    benchmark_performance
    
    # Generate report
    generate_report
    
    # Summary
    log "Test Summary:"
    log "Total: $TESTS_TOTAL, Passed: $TESTS_PASSED, Failed: $TESTS_FAILED"
    
    if [ $TESTS_FAILED -eq 0 ]; then
        success "All tests passed! 🎉"
        exit 0
    else
        fail "Some tests failed! 😞"
        exit 1
    fi
}

# Check dependencies
check_dependencies() {
    for cmd in curl jq python3 bc; do
        if ! command -v $cmd &> /dev/null; then
            echo "Error: $cmd is required but not installed"
            exit 1
        fi
    done
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --url)
            ORCHESTRATOR_URL="$2"
            shift 2
            ;;
        --api-key)
            API_KEY="$2"
            shift 2
            ;;
        --timeout)
            TEST_TIMEOUT="$2"
            shift 2
            ;;
        --help)
            echo "Usage: $0 [--url URL] [--api-key KEY] [--timeout SECONDS]"
            echo "  --url        Orchestrator URL (default: http://localhost:9000)"
            echo "  --api-key    API key for authentication"
            echo "  --timeout    Test timeout in seconds (default: 30)"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Run tests
check_dependencies
main
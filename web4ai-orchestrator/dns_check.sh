#!/bin/bash
# quick-dns-check.sh - Check DNS and setup domain

echo "🔍 Quick DNS Check for orc.peoplesainetwork.com"
echo "==============================================="

# Get current server IP
current_ip=$(curl -s ipinfo.io/ip 2>/dev/null || curl -s icanhazip.com 2>/dev/null)
echo "🖥️ Current server IP: $current_ip"

# Check DNS resolution
echo "🌐 Checking DNS resolution..."
domain_ip=$(dig +short orc.peoplesainetwork.com 2>/dev/null | tail -n1)

if [ -z "$domain_ip" ]; then
    echo "❌ DNS not configured for orc.peoplesainetwork.com"
    echo ""
    echo "📋 TO FIX DNS:"
    echo "1. Go to your domain registrar (Namecheap, GoDaddy, etc.)"
    echo "2. Create an A record:"
    echo "   Name: orc"
    echo "   Type: A"
    echo "   Value: $current_ip"
    echo "   TTL: 300 (5 minutes)"
    echo ""
    echo "3. Wait 5-15 minutes for DNS propagation"
    echo "4. Then run the domain setup script"
    echo ""
    echo "🧪 Test DNS with: nslookup orc.peoplesainetwork.com"
    exit 1
elif [ "$domain_ip" = "$current_ip" ]; then
    echo "✅ DNS correctly points to this server ($current_ip)"
    echo "🚀 Ready to proceed with domain setup!"
    exit 0
else
    echo "⚠️ DNS points to $domain_ip but this server is $current_ip"
    echo ""
    echo "📋 TO FIX:"
    echo "Update your A record to point to: $current_ip"
    echo "Current A record points to: $domain_ip"
    echo ""
    echo "Wait 5-15 minutes after updating, then run setup again."
    exit 1
fi

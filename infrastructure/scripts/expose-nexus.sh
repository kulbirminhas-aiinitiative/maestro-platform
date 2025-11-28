#!/bin/bash
# Script to help expose Nexus for public access
# Use for initial setup only - close access after configuration

set -e

echo "=================================================="
echo "Nexus Public Access Helper"
echo "=================================================="
echo ""

# Get instance metadata
echo "Getting instance information..."
INSTANCE_ID=$(curl -s http://169.254.169.254/latest/meta-data/instance-id 2>/dev/null || echo "unknown")
PUBLIC_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4 2>/dev/null || echo "unknown")
PRIVATE_IP=$(curl -s http://169.254.169.254/latest/meta-data/local-ipv4 2>/dev/null || echo "unknown")

echo "Instance ID: $INSTANCE_ID"
echo "Public IP:   $PUBLIC_IP"
echo "Private IP:  $PRIVATE_IP"
echo ""

# Check if Nexus is running
echo "Checking Nexus status..."
if docker ps | grep -q maestro-nexus; then
    echo "✓ Nexus container is running"

    # Check if port is bound
    if docker port maestro-nexus | grep -q "0.0.0.0:28081"; then
        echo "✓ Nexus port 28081 is bound to all interfaces"
    else
        echo "❌ Nexus port not properly bound"
        exit 1
    fi
else
    echo "❌ Nexus container is not running"
    echo "Start with: docker-compose -f docker-compose.artifacts-minimal.yml up -d"
    exit 1
fi

echo ""
echo "=================================================="
echo "Access Options"
echo "=================================================="
echo ""

echo "Option 1: SSH Tunnel (Most Secure - Recommended)"
echo "------------------------------------------------"
echo "From your local machine, run:"
echo ""
echo "  ssh -L 28081:localhost:28081 ec2-user@$PUBLIC_IP"
echo ""
echo "Then access Nexus at: http://localhost:28081"
echo ""

echo "Option 2: Update AWS Security Group (Temporary)"
echo "------------------------------------------------"
echo "Run this from a machine with AWS CLI configured:"
echo ""

# Get your external IP
MY_IP=$(curl -s https://ifconfig.me 2>/dev/null || curl -s https://api.ipify.org 2>/dev/null || echo "YOUR_IP")

cat <<'EOF'
# Get instance security group
INSTANCE_ID=$(curl -s http://169.254.169.254/latest/meta-data/instance-id)
SG_ID=$(aws ec2 describe-instances --instance-ids $INSTANCE_ID \
  --query 'Reservations[0].Instances[0].SecurityGroups[0].GroupId' \
  --output text)

# Get your current IP
MY_IP=$(curl -s https://ifconfig.me)

# Open port 28081 for your IP only
aws ec2 authorize-security-group-ingress \
  --group-id $SG_ID \
  --protocol tcp \
  --port 28081 \
  --cidr ${MY_IP}/32 \
  --description "Nexus Setup - Temporary"

echo "✓ Port 28081 opened for $MY_IP"
EOF

echo ""
echo "Or manually via AWS Console:"
echo "  1. Go to EC2 Console"
echo "  2. Select instance: $INSTANCE_ID"
echo "  3. Security tab → Security Group"
echo "  4. Edit Inbound Rules → Add Rule"
echo "  5. Type: Custom TCP, Port: 28081, Source: My IP"
echo "  6. Save"
echo ""

echo "Option 3: Test Local Access First"
echo "------------------------------------------------"
echo "From this EC2 instance:"
echo ""
echo "  curl -I http://localhost:28081"
echo ""
echo "Expected: HTTP/1.1 200 OK"
echo ""

echo "=================================================="
echo "After Opening Access"
echo "=================================================="
echo ""
echo "1. Access Nexus Web UI:"
if [ "$PUBLIC_IP" != "unknown" ]; then
    echo "   http://$PUBLIC_IP:28081"
else
    echo "   http://YOUR_PUBLIC_IP:28081"
fi
echo ""
echo "2. Login:"
echo "   Username: admin"
echo "   Password: nexus_admin_2025_change_me"
echo ""
echo "3. Follow setup guide:"
echo "   /infrastructure/docs/NEXUS_PYPI_SETUP.md"
echo ""
echo "4. After setup, secure access:"
echo "   - Remove security group rule"
echo "   - Or use SSH tunnel for ongoing access"
echo ""

echo "=================================================="
echo "Quick Test"
echo "=================================================="
echo ""
echo "Testing local access..."
if curl -s -f http://localhost:28081 > /dev/null 2>&1; then
    echo "✓ Nexus is accessible locally on port 28081"
    echo ""
    echo "If you can't access from your browser, the issue is"
    echo "AWS Security Group - follow Option 2 above"
else
    echo "❌ Nexus is not responding on localhost:28081"
    echo ""
    echo "Check Nexus logs:"
    echo "  docker logs maestro-nexus --tail 50"
fi

echo ""
echo "=================================================="
echo "Security Reminder"
echo "=================================================="
echo ""
echo "⚠️  Remember to close public access after setup!"
echo ""
echo "To remove security group rule:"
echo ""
cat <<'EOF'
aws ec2 revoke-security-group-ingress \
  --group-id $SG_ID \
  --protocol tcp \
  --port 28081 \
  --cidr ${MY_IP}/32
EOF
echo ""
echo "Or use SSH tunnel for all future access (no security group changes needed)"
echo ""

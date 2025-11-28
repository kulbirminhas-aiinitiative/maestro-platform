#!/bin/bash
# Maestro Platform - Simple Demo Deployment
# Deploys Infrastructure + Quality Fabric + Templates + Gateway

set -e

# Configuration
DEMO_SERVER="${DEMO_SERVER:-18.134.157.225}"
DEMO_USER="${DEMO_USER:-ec2-user}"
DEMO_PATH="/home/${DEMO_USER}/projects/maestro-platform"
SSH_KEY="${SSH_KEY:-~/projects/genesis-dev.pem}"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Maestro Platform - Demo Deployment"
echo "  Target: $DEMO_SERVER"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Check SSH connectivity
echo -e "${BLUE}[1/5] Checking SSH connectivity...${NC}"
if ! ssh -i "$SSH_KEY" -o ConnectTimeout=10 ${DEMO_USER}@${DEMO_SERVER} "echo 'Connected'" &> /dev/null; then
    echo -e "${RED}ERROR: Cannot connect to demo server${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Connected to demo server${NC}"
echo ""

# Deploy Infrastructure
echo -e "${BLUE}[2/5] Deploying Infrastructure (postgres, redis, monitoring)...${NC}"
ssh -i "$SSH_KEY" ${DEMO_USER}@${DEMO_SERVER} bash << 'EOF'
set -e
cd /home/ec2-user/projects/maestro-platform/infrastructure

# Start shared infrastructure
docker-compose -f docker-compose.infrastructure.yml --env-file .env up -d maestro-postgres maestro-redis maestro-prometheus maestro-grafana

echo "Waiting for infrastructure to be healthy..."
sleep 15

# Verify infrastructure
docker ps --filter name=maestro-postgres --filter name=maestro-redis --format "{{.Names}}: {{.Status}}"
EOF

echo -e "${GREEN}✓ Infrastructure deployed${NC}"
echo ""

# Deploy Quality Fabric
echo -e "${BLUE}[3/5] Deploying Quality Fabric...${NC}"
ssh -i "$SSH_KEY" ${DEMO_USER}@${DEMO_SERVER} bash << 'EOF'
set -e
cd /home/ec2-user/projects/maestro-platform/quality-fabric

# Stop old instance
docker-compose down 2>/dev/null || true

# Start with shared infrastructure
docker-compose up -d

echo "Waiting for Quality Fabric to be healthy..."
sleep 10

# Verify health
for i in {1..30}; do
    if curl -sf http://localhost:8000/api/health > /dev/null 2>&1; then
        echo "✓ Quality Fabric is healthy!"
        curl -s http://localhost:8000/api/health
        break
    fi
    if [ $i -eq 30 ]; then
        echo "ERROR: Quality Fabric failed to become healthy"
        docker logs quality-fabric --tail 30
        exit 1
    fi
    echo "Waiting... ($i/30)"
    sleep 2
done
EOF

echo -e "${GREEN}✓ Quality Fabric deployed${NC}"
echo ""

# Deploy Templates
echo -e "${BLUE}[4/5] Deploying Templates...${NC}"
ssh -i "$SSH_KEY" ${DEMO_USER}@${DEMO_SERVER} bash << 'EOF'
set -e
cd /home/ec2-user/projects/maestro-platform/maestro-templates

# Stop old instance
docker-compose down 2>/dev/null || true

# Start with shared infrastructure
docker-compose --env-file .env.shared up -d

echo "Waiting for Templates to be healthy..."
sleep 10

# Verify (health check from inside container since no external port)
docker exec maestro-templates-registry curl -sf http://localhost:9600/health || echo "Templates starting..."
EOF

echo -e "${GREEN}✓ Templates deployed${NC}"
echo ""

# Deploy Gateway
echo -e "${BLUE}[5/5] Deploying Gateway...${NC}"
ssh -i "$SSH_KEY" ${DEMO_USER}@${DEMO_SERVER} bash << 'EOF'
set -e
cd /home/ec2-user/projects/maestro-platform/maestro-engine

# Stop old instance
docker-compose -f docker-compose.gateway.yml down 2>/dev/null || true

# Start Gateway
REDIS_PASSWORD=maestro_redis_secure_2025 GATEWAY_PORT=9080 \
  docker-compose -f docker-compose.gateway.yml up -d

echo "Waiting for Gateway to be healthy..."
sleep 10

# Verify health
for i in {1..20}; do
    if curl -sf http://localhost:9080/health > /dev/null 2>&1; then
        echo "✓ Gateway is healthy!"
        curl -s http://localhost:9080/health
        break
    fi
    if [ $i -eq 20 ]; then
        echo "ERROR: Gateway failed to become healthy"
        docker logs maestro-gateway --tail 30
        exit 1
    fi
    echo "Waiting... ($i/20)"
    sleep 2
done
EOF

echo -e "${GREEN}✓ Gateway deployed${NC}"
echo ""

# Final Verification
echo -e "${BLUE}[VERIFICATION] Testing all services via Gateway...${NC}"
ssh -i "$SSH_KEY" ${DEMO_USER}@${DEMO_SERVER} bash << 'EOF'
echo "Testing Gateway health..."
curl -s http://localhost:9080/health | head -3

echo -e "\nTesting Quality Fabric via Gateway..."
curl -s http://localhost:9080/api/v1/quality/api/health | head -3

echo -e "\nTesting Templates via Gateway..."
curl -s http://localhost:9080/api/v1/templates/health | head -3

echo -e "\nRunning containers:"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -E "maestro-gateway|quality-fabric|maestro-templates-registry|maestro-postgres|maestro-redis|NAMES"
EOF

echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✓ DEPLOYMENT COMPLETE${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "Access URLs:"
echo "  Gateway: http://$DEMO_SERVER:9080/health"
echo "  Quality Fabric (via Gateway): http://$DEMO_SERVER:9080/api/v1/quality/api/health"
echo "  Templates (via Gateway): http://$DEMO_SERVER:9080/api/v1/templates/health"
echo ""

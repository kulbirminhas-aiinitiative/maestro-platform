#!/bin/bash
# ==============================================================================
# Maestro Monitoring Stack Deployment Script
# MD-2030: Deploy Prometheus/Grafana Monitoring Stack to Demo Server
# Part of EPIC MD-1979: Service Resilience & Operational Hardening
# ==============================================================================

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

# Script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

echo -e "${BLUE}============================================${NC}"
echo -e "${BLUE}   Maestro Monitoring Stack Deployment${NC}"
echo -e "${BLUE}============================================${NC}"
echo ""

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check if port is in use
port_in_use() {
    lsof -i ":$1" >/dev/null 2>&1
}

# Check prerequisites
echo -e "${YELLOW}Checking prerequisites...${NC}"

if ! command_exists docker; then
    echo -e "${RED}ERROR: Docker is not installed${NC}"
    exit 1
fi

if ! command_exists docker-compose; then
    # Try docker compose (v2)
    if ! docker compose version >/dev/null 2>&1; then
        echo -e "${RED}ERROR: Docker Compose is not installed${NC}"
        exit 1
    fi
    COMPOSE_CMD="docker compose"
else
    COMPOSE_CMD="docker-compose"
fi

echo -e "${GREEN}✓ Docker and Docker Compose available${NC}"

# Check if ports are available
echo ""
echo -e "${YELLOW}Checking port availability...${NC}"

PORTS_TO_CHECK="9090 9093 23000 9100"
PORTS_IN_USE=""

for port in $PORTS_TO_CHECK; do
    if port_in_use $port; then
        PORTS_IN_USE="$PORTS_IN_USE $port"
    fi
done

if [ -n "$PORTS_IN_USE" ]; then
    echo -e "${YELLOW}WARNING: The following ports are already in use:${PORTS_IN_USE}${NC}"
    echo -e "${YELLOW}Existing containers may be running. Proceeding will restart them.${NC}"
fi

echo -e "${GREEN}✓ Port check complete${NC}"

# Navigate to script directory
cd "$SCRIPT_DIR"

# Stop existing containers
echo ""
echo -e "${YELLOW}Stopping existing monitoring containers (if any)...${NC}"
$COMPOSE_CMD -f docker-compose.monitoring.yml down 2>/dev/null || true
echo -e "${GREEN}✓ Cleanup complete${NC}"

# Start monitoring stack
echo ""
echo -e "${YELLOW}Starting monitoring stack...${NC}"
$COMPOSE_CMD -f docker-compose.monitoring.yml up -d

# Wait for services to be healthy
echo ""
echo -e "${YELLOW}Waiting for services to become healthy...${NC}"

MAX_WAIT=60
WAIT_INTERVAL=5
ELAPSED=0

while [ $ELAPSED -lt $MAX_WAIT ]; do
    PROMETHEUS_HEALTHY=$(docker inspect --format='{{.State.Health.Status}}' maestro-prometheus 2>/dev/null || echo "unknown")
    GRAFANA_HEALTHY=$(docker inspect --format='{{.State.Health.Status}}' maestro-grafana 2>/dev/null || echo "unknown")

    if [ "$PROMETHEUS_HEALTHY" = "healthy" ] && [ "$GRAFANA_HEALTHY" = "healthy" ]; then
        echo -e "${GREEN}✓ All services are healthy${NC}"
        break
    fi

    echo "  Prometheus: $PROMETHEUS_HEALTHY, Grafana: $GRAFANA_HEALTHY (waiting...)"
    sleep $WAIT_INTERVAL
    ELAPSED=$((ELAPSED + WAIT_INTERVAL))
done

if [ $ELAPSED -ge $MAX_WAIT ]; then
    echo -e "${YELLOW}WARNING: Services may not be fully healthy yet. Check docker logs.${NC}"
fi

# Display service status
echo ""
echo -e "${BLUE}============================================${NC}"
echo -e "${BLUE}   Deployment Summary${NC}"
echo -e "${BLUE}============================================${NC}"
echo ""

echo -e "${GREEN}Services deployed:${NC}"
$COMPOSE_CMD -f docker-compose.monitoring.yml ps

echo ""
echo -e "${GREEN}Access URLs:${NC}"
echo "  • Prometheus:   http://localhost:9090"
echo "  • Alertmanager: http://localhost:9093"
echo "  • Grafana:      http://localhost:23000"
echo ""
echo -e "${GREEN}Grafana Credentials:${NC}"
echo "  • Username: admin"
echo "  • Password: maestro_admin"
echo ""

# Test Prometheus targets
echo -e "${YELLOW}Checking Prometheus targets...${NC}"
sleep 2
TARGETS=$(curl -s http://localhost:9090/api/v1/targets 2>/dev/null | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    active = data.get('data', {}).get('activeTargets', [])
    for t in active:
        status = t.get('health', 'unknown')
        job = t.get('labels', {}).get('job', 'unknown')
        print(f'  - {job}: {status}')
except:
    print('  Unable to fetch targets (Prometheus may still be starting)')
" 2>/dev/null)

if [ -n "$TARGETS" ]; then
    echo "$TARGETS"
else
    echo "  Prometheus targets will be available shortly at http://localhost:9090/targets"
fi

echo ""
echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}   Deployment Complete!${NC}"
echo -e "${GREEN}============================================${NC}"
echo ""
echo "Next steps:"
echo "1. Access Grafana at http://localhost:23000"
echo "2. Navigate to Dashboards → Maestro → Maestro Service Health"
echo "3. Configure alert notification channels as needed"
echo ""
echo "To view logs:"
echo "  docker logs -f maestro-prometheus"
echo "  docker logs -f maestro-grafana"
echo ""
echo "To stop the monitoring stack:"
echo "  cd $SCRIPT_DIR && $COMPOSE_CMD -f docker-compose.monitoring.yml down"
echo ""

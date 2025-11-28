#!/bin/bash
# Maestro Platform - Automated Infrastructure Deployment
# This script handles EVERYTHING - no manual steps required!

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

log_info "===================================================================="
log_info "Maestro Platform - Centralized Infrastructure Deployment"
log_info "===================================================================="

# Step 1: Check prerequisites
log_info "Step 1/7: Checking prerequisites..."
command -v docker >/dev/null 2>&1 || { log_error "Docker is not installed. Aborting."; exit 1; }
command -v docker-compose >/dev/null 2>&1 || { log_error "Docker Compose is not installed. Aborting."; exit 1; }
log_success "Prerequisites OK"

# Step 2: Create required directories
log_info "Step 2/7: Creating directory structure..."
mkdir -p monitoring/grafana/dashboards/{platform,quality-fabric,maestro-v2,maestro-frontend}
mkdir -p databases/postgres/init-scripts
mkdir -p monitoring/prometheus
for dir in monitoring/grafana/dashboards/{platform,quality-fabric,maestro-v2,maestro-frontend}; do
    touch $dir/.gitkeep
done
log_success "Directories created"

# Step 3: Check/load environment configuration
log_info "Step 3/7: Loading environment configuration..."
if [ ! -f ".env.infrastructure" ]; then
    log_error ".env.infrastructure file not found!"
    log_info "Please create .env.infrastructure with required variables."
    exit 1
fi
set -a
source .env.infrastructure
set +a
log_success "Environment loaded"

# Step 4: Find available ports (auto-resolve conflicts)
log_info "Step 4/7: Detecting port availability..."
find_available_port() {
    local start_port=$1
    local port=$start_port
    while lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; do
        port=$((port + 1))
    done
    echo $port
}

# Auto-detect and use available ports
export MAESTRO_POSTGRES_PORT=${MAESTRO_POSTGRES_PORT:-$(find_available_port 25432)}
export MAESTRO_REDIS_PORT=${MAESTRO_REDIS_PORT:-$(find_available_port 27379)}
export PROMETHEUS_PORT=${PROMETHEUS_PORT:-$(find_available_port 29090)}
export GRAFANA_PORT=${GRAFANA_PORT:-$(find_available_port 23000)}

log_success "Ports allocated:"
log_info "  PostgreSQL: $MAESTRO_POSTGRES_PORT"
log_info "  Redis:      $MAESTRO_REDIS_PORT"
log_info "  Prometheus: $PROMETHEUS_PORT"
log_info "  Grafana:    $GRAFANA_PORT"

# Step 5: Stop existing infrastructure (if any)
log_info "Step 5/7: Cleaning up existing infrastructure..."
docker-compose -f docker-compose.infrastructure.yml down --remove-orphans >/dev/null 2>&1 || true
log_success "Cleanup complete"

# Step 6: Start infrastructure
log_info "Step 6/7: Starting centralized infrastructure..."
docker-compose -f docker-compose.infrastructure.yml up -d

# Step 7: Wait for health checks
log_info "Step 7/7: Waiting for services to be healthy..."
sleep 10

# Check service health
check_service_health() {
    local service=$1
    local max_attempts=30
    local attempt=1
    
    log_info "Checking $service health..."
    while [ $attempt -le $max_attempts ]; do
        if docker inspect --format='{{.State.Health.Status}}' $service 2>/dev/null | grep -q "healthy"; then
            log_success "$service is healthy"
            return 0
        fi
        echo -n "."
        sleep 2
        attempt=$((attempt + 1))
    done
    log_warning "$service did not become healthy (may not have healthcheck)"
    return 1
}

check_service_health "maestro-postgres"
check_service_health "maestro-redis"
check_service_health "maestro-prometheus"
check_service_health "maestro-grafana"

# Summary
log_info "===================================================================="
log_success "Infrastructure deployment complete!"
log_info "===================================================================="
log_info ""
log_info "Access URLs:"
log_info "  Grafana:    http://localhost:$GRAFANA_PORT"
log_info "    Username: ${MAESTRO_GRAFANA_ADMIN_USER:-admin}"
log_info "    Password: (from .env.infrastructure)"
log_info ""
log_info "  Prometheus: http://localhost:$PROMETHEUS_PORT"
log_info ""
log_info "Connection Strings (for services):"
log_info "  PostgreSQL: postgresql://quality_fabric:<password>@maestro-postgres:5432/quality_fabric"
log_info "  Redis:      redis://:<password>@maestro-redis:6379/0"
log_info ""
log_info "Network: maestro-network"
log_info ""
log_info "To view logs:"
log_info "  docker-compose -f docker-compose.infrastructure.yml logs -f"
log_info ""
log_info "===================================================================="

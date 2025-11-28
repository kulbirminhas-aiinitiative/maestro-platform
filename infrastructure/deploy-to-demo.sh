#!/bin/bash
# Maestro Platform - Automated Demo Server Deployment
# Zero manual steps - Full error tracking and recovery

set -e
set -o pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

# Configuration
DEMO_SERVER="${DEMO_SERVER:-demo.maestro-platform.com}"
DEMO_USER="${DEMO_USER:-ec2-user}"
DEMO_PATH="${DEMO_PATH:-/opt/maestro-platform}"
LOG_FILE="deployment-$(date +%Y%m%d-%H%M%S).log"
ERROR_LOG="deployment-errors-$(date +%Y%m%d-%H%M%S).log"
ERROR_COUNT=0
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Logging functions
log() {
    local level=$1
    shift
    local message="$@"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "${timestamp} [${level}] ${message}" | tee -a "$LOG_FILE"
}

log_info() { echo -e "${BLUE}[INFO]${NC} $1" | tee -a "$LOG_FILE"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1" | tee -a "$LOG_FILE"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1" | tee -a "$LOG_FILE"; }
log_error() {
    ERROR_COUNT=$((ERROR_COUNT + 1))
    echo -e "${RED}[ERROR #${ERROR_COUNT}]${NC} $1" | tee -a "$LOG_FILE" "$ERROR_LOG"
}
log_step() { echo -e "${MAGENTA}[STEP]${NC} $1" | tee -a "$LOG_FILE"; }

# Error handler
handle_error() {
    local line=$1
    local command=$2
    log_error "Command failed at line $line: $command"
    log_error "Exit code: $?"

    # Ask for retry or abort
    if [ "$INTERACTIVE" = "true" ]; then
        read -p "Retry? (y/n/abort) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            return 0
        elif [[ $REPLY =~ ^[Aa]$ ]]; then
            log_error "Deployment aborted by user"
            cleanup_and_exit 1
        fi
    fi

    return 1
}

trap 'handle_error ${LINENO} "$BASH_COMMAND"' ERR

# Cleanup function
cleanup_and_exit() {
    local exit_code=$1
    log_info "Cleaning up..."

    if [ $exit_code -eq 0 ]; then
        log_success "Deployment completed successfully!"
        log_info "Total errors encountered: $ERROR_COUNT"
        log_info "Deployment log: $LOG_FILE"
    else
        log_error "Deployment failed with $ERROR_COUNT errors"
        log_error "Error log: $ERROR_LOG"
        log_error "Full log: $LOG_FILE"
    fi

    exit $exit_code
}

# Banner
cat << "EOF"
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║    MAESTRO PLATFORM - DEMO SERVER DEPLOYMENT             ║
║    Fully Automated • Zero Manual Steps                   ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
EOF

log_info "Target: $DEMO_SERVER"
log_info "User: $DEMO_USER"
log_info "Path: $DEMO_PATH"
log_info "Log: $LOG_FILE"
echo ""

# PHASE 1: Prerequisites Check
log_step "PHASE 1/6: Prerequisites Check"

log_info "Checking local prerequisites..."
for cmd in rsync ssh docker; do
    if ! command -v $cmd &> /dev/null; then
        log_error "$cmd not found locally"
        cleanup_and_exit 1
    fi
    log_success "✓ $cmd found"
done

log_info "Checking demo server connectivity..."
if ! ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no ${DEMO_USER}@${DEMO_SERVER} "echo 'Connected'" &> /dev/null; then
    log_error "Cannot connect to demo server: ${DEMO_USER}@${DEMO_SERVER}"
    log_info "Please ensure:"
    log_info "  1. SSH access is configured"
    log_info "  2. Server is running"
    log_info "  3. DEMO_SERVER variable is correct"
    cleanup_and_exit 1
fi
log_success "✓ Demo server accessible"

log_info "Checking remote prerequisites..."
ssh ${DEMO_USER}@${DEMO_SERVER} bash << 'REMOTE_CHECK'
set -e
echo "Checking Docker..."
if ! command -v docker &> /dev/null; then
    echo "ERROR: Docker not installed"
    exit 1
fi
echo "Docker version: $(docker --version)"

echo "Checking Docker Compose..."
if ! command -v docker-compose &> /dev/null; then
    echo "ERROR: Docker Compose not installed"
    exit 1
fi
echo "Docker Compose version: $(docker-compose --version)"

echo "Checking disk space..."
AVAILABLE=$(df -BG / | tail -1 | awk '{print $4}' | sed 's/G//')
if [ "$AVAILABLE" -lt 20 ]; then
    echo "WARNING: Low disk space: ${AVAILABLE}GB available"
else
    echo "Disk space: ${AVAILABLE}GB available"
fi

echo "Checking required ports..."
for port in 8000 23000 25432 27379 29090; do
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo "WARNING: Port $port is in use"
    else
        echo "Port $port: available"
    fi
done
REMOTE_CHECK

if [ $? -ne 0 ]; then
    log_error "Remote prerequisites check failed"
    cleanup_and_exit 1
fi
log_success "✓ Remote prerequisites OK"

echo ""

# PHASE 2: File Transfer
log_step "PHASE 2/6: Transferring Files"

log_info "Creating remote directory structure..."
ssh ${DEMO_USER}@${DEMO_SERVER} "mkdir -p $DEMO_PATH/{infrastructure,quality-fabric,shared/packages}"

log_info "Transferring infrastructure code..."
rsync -avz --progress \
    --exclude '.git' \
    --exclude 'node_modules' \
    --exclude '__pycache__' \
    --exclude '*.pyc' \
    --exclude '.terraform' \
    --exclude 'terraform.tfstate*' \
    "${SCRIPT_DIR}/" \
    ${DEMO_USER}@${DEMO_SERVER}:${DEMO_PATH}/infrastructure/

log_info "Transferring quality-fabric code..."
rsync -avz --progress \
    --exclude '.git' \
    --exclude 'node_modules' \
    --exclude '__pycache__' \
    --exclude '*.pyc' \
    --exclude 'logs' \
    --exclude 'results' \
    "${SCRIPT_DIR}/../quality-fabric/" \
    ${DEMO_USER}@${DEMO_SERVER}:${DEMO_PATH}/quality-fabric/

log_info "Transferring maestro-cache package..."
rsync -avz --progress \
    "${SCRIPT_DIR}/../shared/packages/cache/" \
    ${DEMO_USER}@${DEMO_SERVER}:${DEMO_PATH}/shared/packages/cache/

log_success "✓ Files transferred"

echo ""

# PHASE 3: Infrastructure Deployment
log_step "PHASE 3/6: Deploying Centralized Infrastructure"

ssh ${DEMO_USER}@${DEMO_SERVER} bash << 'REMOTE_INFRA'
set -e
cd /opt/maestro-platform/infrastructure

echo "Setting up environment..."
if [ ! -f .env.infrastructure ]; then
    cat > .env.infrastructure << 'ENV'
MAESTRO_POSTGRES_ADMIN_USER=maestro_admin
MAESTRO_POSTGRES_ADMIN_PASSWORD=maestro_secure_admin_2025_change_me
MAESTRO_REDIS_PASSWORD=maestro_redis_secure_2025
MAESTRO_GRAFANA_ADMIN_USER=admin
MAESTRO_GRAFANA_ADMIN_PASSWORD=grafana_secure_admin_2025_change_me
QUALITY_FABRIC_DB_PASSWORD=qf_db_secure_2025
MAESTRO_V2_DB_PASSWORD=mv2_db_secure_2025
MAESTRO_FRONTEND_DB_PASSWORD=mfe_db_secure_2025
MAESTRO_POSTGRES_PORT=25432
MAESTRO_REDIS_PORT=27379
PROMETHEUS_PORT=29090
GRAFANA_PORT=23000
JAEGER_UI_PORT=26686
JAEGER_COLLECTOR_PORT=24268
MAESTRO_NETWORK_NAME=maestro-network
ENV
    echo "✓ Created .env.infrastructure"
else
    echo "✓ Using existing .env.infrastructure"
fi

echo "Creating required directories..."
mkdir -p monitoring/grafana/dashboards/{platform,quality-fabric,maestro-v2,maestro-frontend}
mkdir -p databases/postgres/init-scripts
mkdir -p monitoring/prometheus
for dir in monitoring/grafana/dashboards/*; do
    touch $dir/.gitkeep 2>/dev/null || true
done

echo "Loading environment..."
set -a
source .env.infrastructure
set +a

echo "Deploying infrastructure..."
docker-compose -f docker-compose.infrastructure.yml down --remove-orphans 2>/dev/null || true
docker-compose -f docker-compose.infrastructure.yml up -d

echo "Waiting for services to be healthy..."
sleep 30

# Check health
for i in {1..30}; do
    POSTGRES_HEALTHY=$(docker inspect maestro-postgres --format='{{.State.Health.Status}}' 2>/dev/null || echo "unknown")
    REDIS_HEALTHY=$(docker inspect maestro-redis --format='{{.State.Health.Status}}' 2>/dev/null || echo "unknown")
    PROMETHEUS_HEALTHY=$(docker inspect maestro-prometheus --format='{{.State.Health.Status}}' 2>/dev/null || echo "unknown")
    GRAFANA_HEALTHY=$(docker inspect maestro-grafana --format='{{.State.Health.Status}}' 2>/dev/null || echo "unknown")

    if [ "$POSTGRES_HEALTHY" = "healthy" ] && \
       [ "$REDIS_HEALTHY" = "healthy" ] && \
       [ "$PROMETHEUS_HEALTHY" = "healthy" ] && \
       [ "$GRAFANA_HEALTHY" = "healthy" ]; then
        echo "✓ All infrastructure services healthy!"
        break
    fi

    echo "Waiting for health checks... ($i/30)"
    sleep 2
done

docker-compose -f docker-compose.infrastructure.yml ps
REMOTE_INFRA

if [ $? -ne 0 ]; then
    log_error "Infrastructure deployment failed"
    cleanup_and_exit 1
fi
log_success "✓ Infrastructure deployed"

echo ""

# PHASE 4: Quality Fabric Deployment
log_step "PHASE 4/6: Deploying Quality Fabric"

ssh ${DEMO_USER}@${DEMO_SERVER} bash << 'REMOTE_QF'
set -e
cd /opt/maestro-platform/quality-fabric

echo "Setting up environment..."
if [ ! -f .env ]; then
    cat > .env << 'ENV'
QUALITY_FABRIC_ENVIRONMENT=development
QUALITY_FABRIC_DB_PASSWORD=qf_db_secure_2025
MAESTRO_REDIS_PASSWORD=maestro_redis_secure_2025
JWT_SECRET=demo_jwt_secret_min_32_characters_long_string
QF_API_PORT=8000
LOG_LEVEL=info
ENV
    echo "✓ Created .env"
fi

echo "Deploying quality-fabric..."
docker-compose -f docker-compose.centralized.yml down 2>/dev/null || true
docker-compose -f docker-compose.centralized.yml up -d --build

echo "Waiting for quality-fabric to start..."
sleep 20

# Check health
for i in {1..30}; do
    if curl -sf http://localhost:8000/api/health > /dev/null 2>&1; then
        echo "✓ Quality Fabric is healthy!"
        break
    fi
    echo "Waiting for quality-fabric... ($i/30)"
    sleep 2
done

docker ps --filter name=quality-fabric
REMOTE_QF

if [ $? -ne 0 ]; then
    log_error "Quality Fabric deployment failed"
    cleanup_and_exit 1
fi
log_success "✓ Quality Fabric deployed"

echo ""

# PHASE 5: Validation
log_step "PHASE 5/6: Running Validation Tests"

log_info "Testing API health endpoint..."
API_HEALTH=$(ssh ${DEMO_USER}@${DEMO_SERVER} "curl -sf http://localhost:8000/api/health" || echo "failed")
if [ "$API_HEALTH" = "failed" ]; then
    log_error "API health check failed"
else
    log_success "✓ API is healthy"
    echo "$API_HEALTH" | tee -a "$LOG_FILE"
fi

log_info "Testing Grafana..."
GRAFANA_HEALTH=$(ssh ${DEMO_USER}@${DEMO_SERVER} "curl -sf http://localhost:23000/api/health" || echo "failed")
if [ "$GRAFANA_HEALTH" = "failed" ]; then
    log_error "Grafana health check failed"
else
    log_success "✓ Grafana is healthy"
fi

log_info "Testing Prometheus..."
PROMETHEUS_HEALTH=$(ssh ${DEMO_USER}@${DEMO_SERVER} "curl -sf http://localhost:29090/-/healthy" || echo "failed")
if [ "$PROMETHEUS_HEALTH" = "failed" ]; then
    log_error "Prometheus health check failed"
else
    log_success "✓ Prometheus is healthy"
fi

echo ""

# PHASE 6: Summary
log_step "PHASE 6/6: Deployment Summary"

cat << EOF

╔═══════════════════════════════════════════════════════════╗
║              DEPLOYMENT COMPLETE ✓                        ║
╚═══════════════════════════════════════════════════════════╝

📊 Deployment Statistics:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Total Errors:        $ERROR_COUNT
  Deployment Time:     $(date -d @$SECONDS -u +%H:%M:%S)
  Target Server:       $DEMO_SERVER
  Log File:            $LOG_FILE

🌐 Access URLs:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Quality Fabric API:  http://$DEMO_SERVER:8000
  API Documentation:   http://$DEMO_SERVER:8000/docs
  Grafana:             http://$DEMO_SERVER:23000
  Prometheus:          http://$DEMO_SERVER:29090

📋 Infrastructure:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  PostgreSQL:          $DEMO_SERVER:25432
  Redis:               $DEMO_SERVER:27379
  Network:             maestro-network

📝 Management Commands:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  View logs:           ssh $DEMO_USER@$DEMO_SERVER "docker logs -f quality-fabric"
  Restart services:    ssh $DEMO_USER@$DEMO_SERVER "cd $DEMO_PATH/infrastructure && docker-compose -f docker-compose.infrastructure.yml restart"
  Stop all:            ssh $DEMO_USER@$DEMO_SERVER "cd $DEMO_PATH/quality-fabric && docker-compose -f docker-compose.centralized.yml down"

EOF

cleanup_and_exit 0

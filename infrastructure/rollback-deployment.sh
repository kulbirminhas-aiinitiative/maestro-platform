#!/bin/bash
# Maestro Platform - Complete Rollback Script
# Returns demo server to ground zero (clean state)

set -e
set -o pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
DEMO_SERVER="${DEMO_SERVER:-18.134.157.225}"
DEMO_USER="${DEMO_USER:-ec2-user}"
DEMO_PATH="${DEMO_PATH:-/opt/maestro-platform}"
SSH_KEY="${SSH_KEY:-~/projects/genesis-dev.pem}"

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

cat << "EOF"
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║    MAESTRO PLATFORM - COMPLETE ROLLBACK                  ║
║    Returns Server to Ground Zero                         ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
EOF

echo ""
log_warning "This will COMPLETELY REMOVE all Maestro Platform components from:"
log_warning "  Server: $DEMO_SERVER"
log_warning "  Path: $DEMO_PATH"
echo ""
read -p "Are you sure you want to continue? (yes/no): " -r
if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
    log_info "Rollback cancelled"
    exit 0
fi
echo ""

log_info "Starting complete rollback..."
echo ""

# Execute rollback on remote server
ssh -i "$SSH_KEY" ${DEMO_USER}@${DEMO_SERVER} bash << 'REMOTE_ROLLBACK'
set -e

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "STEP 1: Stopping All Maestro Containers"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Stop quality-fabric
if [ -d "/opt/maestro-platform/quality-fabric" ]; then
    cd /opt/maestro-platform/quality-fabric
    docker-compose -f docker-compose.centralized.yml down -v 2>/dev/null || true
    echo "✓ Quality Fabric stopped"
fi

# Stop infrastructure
if [ -d "/opt/maestro-platform/infrastructure" ]; then
    cd /opt/maestro-platform/infrastructure
    docker-compose -f docker-compose.infrastructure.yml down -v 2>/dev/null || true
    echo "✓ Infrastructure stopped"
fi

# Stop any remaining maestro containers
echo ""
echo "Stopping any remaining Maestro containers..."
docker ps -a --filter "name=maestro" --filter "name=quality-fabric" -q | xargs -r docker stop
docker ps -a --filter "name=maestro" --filter "name=quality-fabric" -q | xargs -r docker rm -f
echo "✓ All Maestro containers stopped and removed"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "STEP 2: Removing Docker Resources"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Remove volumes
echo "Removing Docker volumes..."
docker volume ls --filter "name=maestro" --filter "name=quality-fabric" -q | xargs -r docker volume rm 2>/dev/null || true
echo "✓ Docker volumes removed"

# Remove network
echo "Removing maestro-network..."
docker network rm maestro-network 2>/dev/null || echo "  (network already removed)"
echo "✓ Docker network removed"

# Remove images
echo "Removing Maestro images..."
docker images --filter "reference=quality-fabric*" -q | xargs -r docker rmi -f 2>/dev/null || true
docker images --filter "reference=maestro*" -q | xargs -r docker rmi -f 2>/dev/null || true
echo "✓ Docker images removed"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "STEP 3: Removing Files and Directories"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ -d "/opt/maestro-platform" ]; then
    echo "Removing /opt/maestro-platform..."
    sudo rm -rf /opt/maestro-platform
    echo "✓ Directory removed"
else
    echo "✓ Directory already removed"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "STEP 4: Cleaning BuildX Resources"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Remove buildx builder
docker buildx rm maestro-builder 2>/dev/null || echo "  (builder already removed)"

# Stop buildkit container
docker ps -a --filter "name=buildx_buildkit" -q | xargs -r docker rm -f 2>/dev/null || true
echo "✓ BuildX resources cleaned"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "STEP 5: Verification"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

echo ""
echo "Remaining Maestro containers:"
CONTAINERS=$(docker ps -a --filter "name=maestro" --filter "name=quality-fabric" --format "{{.Names}}" || echo "None")
if [ -z "$CONTAINERS" ]; then
    echo "  ✓ None found (clean)"
else
    echo "  $CONTAINERS"
fi

echo ""
echo "Remaining Maestro volumes:"
VOLUMES=$(docker volume ls --filter "name=maestro" --filter "name=quality-fabric" -q || echo "None")
if [ -z "$VOLUMES" ]; then
    echo "  ✓ None found (clean)"
else
    echo "  $VOLUMES"
fi

echo ""
echo "Remaining Maestro networks:"
NETWORKS=$(docker network ls --filter "name=maestro" --format "{{.Name}}" || echo "None")
if [ -z "$NETWORKS" ]; then
    echo "  ✓ None found (clean)"
else
    echo "  $NETWORKS"
fi

echo ""
echo "Directory status:"
if [ -d "/opt/maestro-platform" ]; then
    echo "  ⚠️  /opt/maestro-platform still exists"
else
    echo "  ✓ /opt/maestro-platform removed (clean)"
fi

REMOTE_ROLLBACK

if [ $? -eq 0 ]; then
    echo ""
    log_success "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    log_success "ROLLBACK COMPLETE - Server at Ground Zero"
    log_success "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    log_info "The demo server is now in a clean state."
    log_info "Ready for fresh deployment with: ./deploy-to-demo-enhanced.sh"
    echo ""
else
    log_error "Rollback encountered errors"
    exit 1
fi

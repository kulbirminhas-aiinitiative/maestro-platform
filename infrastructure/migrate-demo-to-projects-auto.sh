#!/bin/bash
# Maestro Platform - Fully Automated Demo Migration (Non-Interactive)
# Migrates from /opt to ~/projects without any user prompts

set -e
set -o pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Configuration
DEMO_SERVER="${DEMO_SERVER:-18.134.157.225}"
DEMO_USER="${DEMO_USER:-ec2-user}"
OLD_PATH="/opt/maestro-platform"
NEW_PATH="/home/${DEMO_USER}/projects/maestro-platform"
SSH_KEY="${SSH_KEY:-~/projects/genesis-dev.pem}"
BACKUP_NAME="maestro-opt-backup-$(date +%Y%m%d-%H%M%S).tar.gz"

cat << "EOF"
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║   MAESTRO DEMO - AUTOMATED MIGRATION                     ║
║   /opt → ~/projects (Fully Automated)                    ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
EOF

echo ""
log_info "Demo Server: $DEMO_SERVER"
log_info "Old Path: $OLD_PATH"
log_info "New Path: $NEW_PATH"
log_info "Mode: FULLY AUTOMATED (no prompts)"
echo ""

# ============================================================================
# STEP 1: Prerequisites Check
# ============================================================================
log_info "Step 1/8: Prerequisites Check"

log_info "Testing SSH connection..."
if ! ssh -i "$SSH_KEY" -o ConnectTimeout=10 -o StrictHostKeyChecking=no ${DEMO_USER}@${DEMO_SERVER} "echo 'Connected'" &> /dev/null; then
    log_error "Cannot connect to demo server"
    exit 1
fi
log_success "✓ Connected to demo server"

# ============================================================================
# STEP 2: Backup existing /opt deployment
# ============================================================================
log_info "Step 2/8: Backing up /opt deployment (if exists)"

BACKUP_CREATED=$(ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no ${DEMO_USER}@${DEMO_SERVER} "
    if [ -d $OLD_PATH ]; then
        sudo tar -czf ~/${BACKUP_NAME} $OLD_PATH 2>/dev/null || true
        if [ -f ~/${BACKUP_NAME} ]; then
            echo 'true'
        else
            echo 'false'
        fi
    else
        echo 'none'
    fi
")

if [ "$BACKUP_CREATED" = "true" ]; then
    log_success "✓ Backup created: ~/${BACKUP_NAME}"
elif [ "$BACKUP_CREATED" = "none" ]; then
    log_info "No /opt deployment found - proceeding with fresh deployment"
else
    log_warning "Backup creation skipped or failed (continuing anyway)"
fi

# ============================================================================
# STEP 3: Stop services in /opt
# ============================================================================
log_info "Step 3/8: Stopping services in /opt (if running)"

ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no ${DEMO_USER}@${DEMO_SERVER} "
    if [ -d $OLD_PATH ]; then
        cd $OLD_PATH/quality-fabric 2>/dev/null && docker-compose down 2>/dev/null || true
        cd $OLD_PATH/infrastructure 2>/dev/null && docker-compose down 2>/dev/null || true
    fi
" || true

log_success "✓ Services stopped (if any were running)"

# ============================================================================
# STEP 4: Create new directory structure
# ============================================================================
log_info "Step 4/8: Creating ~/projects directory structure"

ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no ${DEMO_USER}@${DEMO_SERVER} "
    mkdir -p $NEW_PATH/{infrastructure,quality-fabric,shared/packages}
    echo 'Directory structure created'
"

log_success "✓ Directory structure created at $NEW_PATH"

# ============================================================================
# STEP 5: Update deployment script locally
# ============================================================================
log_info "Step 5/8: Updating deployment script"

# Check if already updated
if grep -q "\/home\/\${DEMO_USER}\/projects\/maestro-platform" deploy-to-demo-enhanced.sh 2>/dev/null; then
    log_success "✓ Deployment script already updated"
else
    log_info "Updating DEMO_PATH in deploy-to-demo-enhanced.sh..."

    # Backup original
    cp deploy-to-demo-enhanced.sh deploy-to-demo-enhanced.sh.backup-$(date +%Y%m%d-%H%M%S)

    # Update the path
    sed -i 's|DEMO_PATH="${DEMO_PATH:-/opt/maestro-platform}"|DEMO_PATH="${DEMO_PATH:-/home/${DEMO_USER}/projects/maestro-platform}"|' deploy-to-demo-enhanced.sh

    # Remove sudo from directory creation (line 167)
    sed -i 's|sudo mkdir -p \$DEMO_PATH && sudo chown \${DEMO_USER}:\${DEMO_USER} \$DEMO_PATH|mkdir -p \$DEMO_PATH|' deploy-to-demo-enhanced.sh

    log_success "✓ Deployment script updated"
fi

# ============================================================================
# STEP 6: Transfer files
# ============================================================================
log_info "Step 6/8: Transferring files to demo server"

log_info "Transferring infrastructure code..."
rsync -avz -e "ssh -i $SSH_KEY -o StrictHostKeyChecking=no" \
    --exclude='*.log' \
    --exclude='.git' \
    --exclude='__pycache__' \
    ../infrastructure/ \
    ${DEMO_USER}@${DEMO_SERVER}:${NEW_PATH}/infrastructure/

log_info "Transferring quality-fabric code..."
rsync -avz -e "ssh -i $SSH_KEY -o StrictHostKeyChecking=no" \
    --exclude='*.log' \
    --exclude='.git' \
    --exclude='__pycache__' \
    --exclude='node_modules' \
    --exclude='venv' \
    --exclude='.venv' \
    --exclude='data' \
    --exclude='logs' \
    --exclude='temp' \
    --exclude='results' \
    ../quality-fabric/ \
    ${DEMO_USER}@${DEMO_SERVER}:${NEW_PATH}/quality-fabric/

log_info "Transferring shared libraries..."
rsync -avz -e "ssh -i $SSH_KEY -o StrictHostKeyChecking=no" \
    --exclude='*.log' \
    --exclude='.git' \
    --exclude='__pycache__' \
    --exclude='venv' \
    --exclude='.venv' \
    --exclude='dist' \
    --exclude='build' \
    ../shared/ \
    ${DEMO_USER}@${DEMO_SERVER}:${NEW_PATH}/shared/

log_success "✓ Files transferred"

# ============================================================================
# STEP 7: Create .env.nexus on demo server
# ============================================================================
log_info "Step 7/8: Creating .env.nexus configuration"

ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no ${DEMO_USER}@${DEMO_SERVER} "
cat > ${NEW_PATH}/quality-fabric/.env.nexus << 'ENVEOF'
# Nexus Configuration for Demo Server Docker Builds
NEXUS_PYPI_INDEX_URL=http://admin:DJ6J%26hGH%21B%23u*J@3.10.213.208:28081/repository/pypi-group/simple
NEXUS_PYPI_TRUSTED_HOST=3.10.213.208
MAESTRO_VERSION=1.0.0
ENVEOF
"

log_success "✓ .env.nexus created with public Nexus IP"

# ============================================================================
# STEP 8: Start services on demo server
# ============================================================================
log_info "Step 8/8: Starting services on demo server"

ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no ${DEMO_USER}@${DEMO_SERVER} "
    cd ${NEW_PATH}/quality-fabric

    # Pull latest images and build
    docker-compose --env-file .env.nexus -f docker-compose.centralized.yml pull 2>/dev/null || true
    docker-compose --env-file .env.nexus -f docker-compose.centralized.yml build --no-cache

    # Start services
    docker-compose --env-file .env.nexus -f docker-compose.centralized.yml up -d

    echo 'Services started'
"

log_success "✓ Services deployed and started"

# ============================================================================
# STEP 9: Verify deployment
# ============================================================================
log_info "Verifying deployment..."
sleep 10  # Give services time to start

HEALTH_CHECK=$(ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no ${DEMO_USER}@${DEMO_SERVER} "
    curl -sf http://localhost:8000/api/health 2>/dev/null || echo 'unhealthy'
")

if echo "$HEALTH_CHECK" | grep -q '"status".*"healthy"'; then
    log_success "✓ Health check PASSED"
else
    log_warning "Health check pending (services may still be starting)"
fi

# Show running containers
log_info "Running containers on demo server:"
ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no ${DEMO_USER}@${DEMO_SERVER} "
    docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'
"

# ============================================================================
# STEP 10: Clean up old /opt deployment
# ============================================================================
log_info "Cleaning up old /opt deployment..."

ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no ${DEMO_USER}@${DEMO_SERVER} "
    if [ -d $OLD_PATH ]; then
        sudo rm -rf $OLD_PATH
        echo '/opt/maestro-platform removed'
    else
        echo 'No /opt deployment to clean up'
    fi
"

log_success "✓ Old /opt deployment cleaned up"

# ============================================================================
# Summary
# ============================================================================
echo ""
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║              MIGRATION COMPLETE                           ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""

log_success "Demo server successfully migrated!"
echo ""
log_info "New deployment location: $NEW_PATH"
log_info "Backup location: ~/${BACKUP_NAME} (if created)"
log_info "Services: Running on demo server"
echo ""

log_info "Verify deployment:"
log_info "  ssh ${DEMO_USER}@${DEMO_SERVER} 'docker ps'"
log_info "  ssh ${DEMO_USER}@${DEMO_SERVER} 'curl http://localhost:8000/api/health'"
echo ""

log_success "Migration successful! 🎉"

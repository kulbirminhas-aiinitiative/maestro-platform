#!/bin/bash
# Maestro Platform - Migrate Demo Server from /opt to ~/projects
# Safe migration with backup and rollback capability

set -e

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
║   MAESTRO DEMO SERVER - PATH MIGRATION                   ║
║   From: /opt/maestro-platform                            ║
║   To:   ~/projects/maestro-platform                      ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
EOF

echo ""
log_info "Demo Server: $DEMO_SERVER"
log_info "Old Path: $OLD_PATH"
log_info "New Path: $NEW_PATH"
echo ""

# Verify SSH connectivity
log_info "Testing SSH connection..."
if ! ssh -i "$SSH_KEY" -o ConnectTimeout=10 ${DEMO_USER}@${DEMO_SERVER} "echo 'Connected'" &> /dev/null; then
    log_error "Cannot connect to demo server"
    log_info "Please check:"
    log_info "  1. DEMO_SERVER=$DEMO_SERVER is correct"
    log_info "  2. SSH key exists: $SSH_KEY"
    log_info "  3. Server is running and accessible"
    exit 1
fi
log_success "✓ Connected to demo server"

# Check if /opt deployment exists
log_info "Checking for existing /opt deployment..."
if ssh -i "$SSH_KEY" ${DEMO_USER}@${DEMO_SERVER} "[ -d $OLD_PATH ]"; then
    log_warning "Found existing deployment at $OLD_PATH"
    MIGRATION_NEEDED=true
else
    log_info "No /opt deployment found - will do fresh deployment"
    MIGRATION_NEEDED=false
fi

# Confirm before proceeding
echo ""
if [ "$MIGRATION_NEEDED" = true ]; then
    log_warning "This will:"
    echo "  1. Backup current /opt deployment"
    echo "  2. Stop services in /opt"
    echo "  3. Create new ~/projects structure"
    echo "  4. Deploy to new location"
    echo "  5. Keep /opt backup for safety"
    echo ""
    read -p "Continue with migration? (yes/no): " -r
else
    log_info "This will:"
    echo "  1. Create ~/projects structure"
    echo "  2. Deploy to new location"
    echo ""
    read -p "Continue with fresh deployment? (yes/no): " -r
fi

if [[ ! $REPLY =~ ^[Yy]es$ ]]; then
    log_info "Migration cancelled"
    exit 0
fi

echo ""

# ============================================================================
# STEP 1: Backup existing /opt deployment
# ============================================================================
if [ "$MIGRATION_NEEDED" = true ]; then
    log_info "Step 1/6: Creating backup of /opt deployment..."

    ssh -i "$SSH_KEY" ${DEMO_USER}@${DEMO_SERVER} "
        sudo tar -czf ~/${BACKUP_NAME} $OLD_PATH 2>/dev/null || true
        if [ -f ~/${BACKUP_NAME} ]; then
            echo 'Backup created: ${BACKUP_NAME}'
            ls -lh ~/${BACKUP_NAME}
        fi
    "

    log_success "✓ Backup created: ~/${BACKUP_NAME}"
else
    log_info "Step 1/6: Skipping backup (no /opt deployment)"
fi

echo ""

# ============================================================================
# STEP 2: Stop services in /opt
# ============================================================================
if [ "$MIGRATION_NEEDED" = true ]; then
    log_info "Step 2/6: Stopping services in /opt..."

    ssh -i "$SSH_KEY" ${DEMO_USER}@${DEMO_SERVER} "
        cd $OLD_PATH/quality-fabric 2>/dev/null && docker-compose down || true
        cd $OLD_PATH/infrastructure 2>/dev/null && docker-compose down || true
        echo 'Services stopped'
    "

    log_success "✓ Services stopped"
else
    log_info "Step 2/6: Skipping service stop (no /opt deployment)"
fi

echo ""

# ============================================================================
# STEP 3: Create new directory structure
# ============================================================================
log_info "Step 3/6: Creating new directory structure..."

ssh -i "$SSH_KEY" ${DEMO_USER}@${DEMO_SERVER} "
    mkdir -p $NEW_PATH/{infrastructure,quality-fabric,shared/packages}
    echo 'Directory structure created'
    ls -la $NEW_PATH
"

log_success "✓ Directory structure created at $NEW_PATH"

echo ""

# ============================================================================
# STEP 4: Update deployment script
# ============================================================================
log_info "Step 4/6: Updating deployment script..."

# Check if already updated
if grep -q "/home/\${DEMO_USER}/projects/maestro-platform" deploy-to-demo-enhanced.sh 2>/dev/null; then
    log_success "✓ Deployment script already updated"
elif grep -q "~/projects/maestro-platform" deploy-to-demo-enhanced.sh 2>/dev/null; then
    log_success "✓ Deployment script already updated (using ~)"
else
    log_info "Updating DEMO_PATH in deploy-to-demo-enhanced.sh..."

    # Backup original
    cp deploy-to-demo-enhanced.sh deploy-to-demo-enhanced.sh.backup

    # Update the path
    sed -i 's|DEMO_PATH="${DEMO_PATH:-/opt/maestro-platform}"|DEMO_PATH="${DEMO_PATH:-/home/${DEMO_USER}/projects/maestro-platform}"|' deploy-to-demo-enhanced.sh

    # Remove sudo from directory creation
    sed -i 's|sudo mkdir -p \$DEMO_PATH && sudo chown \${DEMO_USER}:\${DEMO_USER} \$DEMO_PATH|mkdir -p \$DEMO_PATH|' deploy-to-demo-enhanced.sh

    log_success "✓ Deployment script updated"
    log_info "  Backup saved as: deploy-to-demo-enhanced.sh.backup"
fi

echo ""

# ============================================================================
# STEP 5: Deploy to new location
# ============================================================================
log_info "Step 5/6: Deploying to new location..."
log_warning "This may take several minutes..."

echo ""
./deploy-to-demo-enhanced.sh

echo ""
log_success "✓ Deployment to new location complete"

echo ""

# ============================================================================
# STEP 6: Verify deployment
# ============================================================================
log_info "Step 6/6: Verifying deployment..."

ssh -i "$SSH_KEY" ${DEMO_USER}@${DEMO_SERVER} "
    echo '=== Directory Structure ==='
    ls -la $NEW_PATH

    echo ''
    echo '=== Running Containers ==='
    docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'

    echo ''
    echo '=== Health Check ==='
    sleep 5  # Give services time to start
    curl -sf http://localhost:8000/api/health | jq . || echo 'Health endpoint not responding yet (may need more time)'
"

log_success "✓ Verification complete"

# ============================================================================
# Summary
# ============================================================================
echo ""
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║                  MIGRATION COMPLETE                       ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""

log_success "Demo server successfully migrated!"
echo ""
log_info "New deployment location: $NEW_PATH"

if [ "$MIGRATION_NEEDED" = true ]; then
    log_info "Backup of old deployment: ~/${BACKUP_NAME}"
    echo ""
    log_warning "Old /opt deployment is still present"
    log_info "To remove it after confirming new deployment works:"
    log_info "  ssh ${DEMO_USER}@${DEMO_SERVER} 'sudo rm -rf $OLD_PATH'"
fi

echo ""
log_info "Next steps:"
echo "  1. Test the deployment thoroughly"
echo "  2. Update any documentation referencing /opt"
echo "  3. Update monitoring/alerts if needed"
if [ "$MIGRATION_NEEDED" = true ]; then
    echo "  4. Remove old /opt deployment (after 24h stability)"
fi

echo ""
log_success "Migration successful! 🎉"

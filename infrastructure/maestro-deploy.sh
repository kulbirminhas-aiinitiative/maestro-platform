#!/bin/bash
# Maestro Platform - Master Deployment Script
# Orchestrates: Terraform + Ansible + Docker Compose
# Usage: ./maestro-deploy.sh [environment]

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_step() { echo -e "${MAGENTA}[STEP]${NC} $1"; }

# Configuration
ENVIRONMENT=${1:-demo}
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Display banner
cat << "EOF"
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║    MAESTRO PLATFORM - INFRASTRUCTURE DEPLOYMENT          ║
║    Automated • Reproducible • Production-Ready           ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
EOF

log_info "Environment: $ENVIRONMENT"
log_info "Deployment started at: $(date)"
echo ""

# Step 1: Prerequisites Check
log_step "1/8: Checking Prerequisites"
PREREQ_OK=true

for cmd in docker terraform ansible-playbook; do
    if ! command -v $cmd &> /dev/null; then
        log_error "$cmd not found. Please install it first."
        PREREQ_OK=false
    else
        version=$($cmd --version 2>&1 | head -n1)
        log_info "✓ $cmd: $version"
    fi
done

if [ "$PREREQ_OK" = false ]; then
    log_error "Prerequisites not met. Exiting."
    exit 1
fi
log_success "Prerequisites OK"
echo ""

# Step 2: Load Environment Configuration
log_step "2/8: Loading Configuration"
if [ ! -f ".env.infrastructure" ]; then
    log_error ".env.infrastructure not found!"
    exit 1
fi

set -a
source .env.infrastructure
set +a

# Export as Terraform variables
export TF_VAR_postgres_admin_password="$MAESTRO_POSTGRES_ADMIN_PASSWORD"
export TF_VAR_redis_password="$MAESTRO_REDIS_PASSWORD"
export TF_VAR_grafana_admin_password="$MAESTRO_GRAFANA_ADMIN_PASSWORD"

log_success "Configuration loaded"
echo ""

# Step 3: Create Required Directories
log_step "3/8: Setting Up Directory Structure"
mkdir -p {
    monitoring/grafana/dashboards/{platform,quality-fabric,maestro-v2,maestro-frontend},
    databases/postgres/init-scripts,
    monitoring/prometheus,
    logs,
    backups
}
for dir in monitoring/grafana/dashboards/*; do
    touch $dir/.gitkeep 2>/dev/null || true
done
log_success "Directories ready"
echo ""

# Step 4: Stop Existing Infrastructure (if any)
log_step "4/8: Cleaning Up Existing Resources"
docker-compose -f docker-compose.infrastructure.yml down --remove-orphans 2>/dev/null || true
cd terraform/environments/$ENVIRONMENT
terraform destroy -auto-approve 2>/dev/null || true
cd "$SCRIPT_DIR"
log_success "Cleanup complete"
echo ""

# Step 5: Terraform Infrastructure Provisioning
log_step "5/8: Provisioning Infrastructure with Terraform"
cd terraform/environments/$ENVIRONMENT

log_info "Initializing Terraform..."
terraform init -upgrade

log_info "Planning infrastructure..."
terraform plan -out=tfplan

log_info "Applying infrastructure..."
terraform apply -auto-approve tfplan

log_success "Terraform infrastructure deployed"
cd "$SCRIPT_DIR"
echo ""

# Step 6: Configuration Management with Ansible
log_step "6/8: Running Ansible Configuration"
if [ -f "ansible/playbooks/post-deploy-config.yml" ]; then
    log_info "Applying Ansible configuration..."
    ansible-playbook \
        -i ansible/inventory/$ENVIRONMENT.ini \
        ansible/playbooks/post-deploy-config.yml \
        -e "environment=$ENVIRONMENT" || true
    log_success "Ansible configuration applied"
else
    log_warning "Ansible playbook not found, skipping..."
fi
echo ""

# Step 7: Health Checks
log_step "7/8: Running Health Checks"
HEALTH_OK=true

check_service() {
    local name=$1
    local url=$2
    local max_attempts=30
    local attempt=1

    log_info "Checking $name..."
    while [ $attempt -le $max_attempts ]; do
        if curl -sf "$url" > /dev/null 2>&1; then
            log_success "$name is healthy ✓"
            return 0
        fi
        echo -n "."
        sleep 2
        attempt=$((attempt + 1))
    done
    echo ""
    log_warning "$name health check failed"
    HEALTH_OK=false
    return 1
}

check_service "Prometheus" "http://localhost:$PROMETHEUS_PORT/-/healthy"
check_service "Grafana" "http://localhost:$GRAFANA_PORT/api/health"

if [ "$HEALTH_OK" = true ]; then
    log_success "All services healthy ✓"
else
    log_warning "Some services may need manual verification"
fi
echo ""

# Step 8: Display Summary
log_step "8/8: Deployment Summary"
cat << EOF

╔═══════════════════════════════════════════════════════════╗
║                 DEPLOYMENT SUCCESSFUL ✓                   ║
╚═══════════════════════════════════════════════════════════╝

Environment: $ENVIRONMENT
Deployed at: $(date)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ACCESS URLS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  📊 Grafana:       http://localhost:$GRAFANA_PORT
     Username:      ${MAESTRO_GRAFANA_ADMIN_USER:-admin}
     Password:      (from .env.infrastructure)

  📈 Prometheus:    http://localhost:$PROMETHEUS_PORT
     Targets:       http://localhost:$PROMETHEUS_PORT/targets

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CONNECTION STRINGS (for services)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

PostgreSQL:
  postgresql://quality_fabric:<pass>@maestro-postgres-$ENVIRONMENT:5432/quality_fabric

Redis:
  redis://:<pass>@maestro-redis-$ENVIRONMENT:6379/0

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
USEFUL COMMANDS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

View logs:
  docker logs -f maestro-postgres-$ENVIRONMENT
  docker logs -f maestro-grafana-$ENVIRONMENT

Backup PostgreSQL:
  docker exec maestro-postgres-$ENVIRONMENT pg_dumpall -U maestro_admin > backup_\$(date +%Y%m%d).sql

Terraform commands:
  cd terraform/environments/$ENVIRONMENT
  terraform plan
  terraform destroy

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Next: Deploy your services (quality-fabric, maestro-v2, etc.)
They will automatically connect to this centralized infrastructure.

EOF

log_success "Deployment Complete! 🎉"

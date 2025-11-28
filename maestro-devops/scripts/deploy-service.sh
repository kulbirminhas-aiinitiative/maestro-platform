#!/usr/bin/env bash
#
# Maestro Unified Service Deployment Script
#
# Deploy any Maestro service to the demo server using a standardized approach
#
# Usage:
#   ./scripts/deploy-service.sh <service-name>
#   ./scripts/deploy-service.sh --list
#   ./scripts/deploy-service.sh --all
#
# Services:
#   infrastructure     - Redis, PostgreSQL
#   maestro-engine     - Guardian/Accelerator modes
#   maestro-templates  - Template service
#   quality-fabric     - Quality assessment
#   gateway            - API gateway
#   frontend           - maestro-frontend-production
#
# Environment Variables:
#   DEMO_SERVER   - Demo server hostname or IP (default: 3.10.213.208)
#   DEMO_USER     - SSH username (default: ec2-user)
#   SSH_KEY_PATH  - Path to SSH key
#

set -euo pipefail

# Script directories
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Configuration
DEMO_SERVER="${DEMO_SERVER:-3.10.213.208}"
DEMO_USER="${DEMO_USER:-ec2-user}"
SSH_KEY_PATH="${SSH_KEY_PATH:-}"
DEPLOY_PATH="${DEPLOY_PATH:-/opt/maestro}"

# Service definitions
declare -A SERVICE_REPOS=(
    ["infrastructure"]="maestro-platform"
    ["maestro-engine"]="maestro-platform/maestro-engine"
    ["maestro-templates"]="maestro-platform/maestro-templates"
    ["quality-fabric"]="maestro-platform/quality-fabric"
    ["gateway"]="maestro-platform/maestro-engine"
    ["frontend"]="maestro-frontend-production"
)

declare -A SERVICE_PORTS=(
    ["infrastructure"]="5432,6379"
    ["maestro-engine"]="5000,4001"
    ["maestro-templates"]="9600"
    ["quality-fabric"]="8000"
    ["gateway"]="8080"
    ["frontend"]="4300,3100"
)

declare -A SERVICE_HEALTH=(
    ["infrastructure"]=""
    ["maestro-engine"]="http://localhost:5000/health"
    ["maestro-templates"]="http://localhost:9600/health"
    ["quality-fabric"]="http://localhost:8000/api/health"
    ["gateway"]="http://localhost:8080/health"
    ["frontend"]="http://localhost:4300/health,http://localhost:3100/health"
)

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Logging
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[✓]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[⚠]${NC} $1"; }
log_error() { echo -e "${RED}[✗]${NC} $1"; }
log_step() { echo -e "${CYAN}[STEP]${NC} $1"; }

# Get SSH command
get_ssh_cmd() {
    if [ -n "$SSH_KEY_PATH" ]; then
        echo "ssh -i $SSH_KEY_PATH -o StrictHostKeyChecking=no $DEMO_USER@$DEMO_SERVER"
    else
        echo "ssh -o StrictHostKeyChecking=no $DEMO_USER@$DEMO_SERVER"
    fi
}

# Get SCP command
get_scp_cmd() {
    if [ -n "$SSH_KEY_PATH" ]; then
        echo "scp -i $SSH_KEY_PATH -o StrictHostKeyChecking=no"
    else
        echo "scp -o StrictHostKeyChecking=no"
    fi
}

# List available services
list_services() {
    echo "Available services:"
    echo ""
    for service in "${!SERVICE_REPOS[@]}"; do
        local ports="${SERVICE_PORTS[$service]}"
        echo "  $service"
        echo "    Repository: ${SERVICE_REPOS[$service]}"
        echo "    Ports: $ports"
        echo ""
    done
}

# Check SSH connectivity
check_connectivity() {
    log_step "Checking connectivity to $DEMO_SERVER..."

    local ssh_cmd=$(get_ssh_cmd)

    if $ssh_cmd "echo 'connected'" &>/dev/null; then
        log_success "SSH connection established"
        return 0
    else
        log_error "Cannot connect to $DEMO_SERVER"
        return 1
    fi
}

# Send deployment notification
notify() {
    local event="$1"
    local service="$2"
    local message="${3:-}"

    if [ -f "$SCRIPT_DIR/notify-deployment.sh" ]; then
        ENVIRONMENT="demo" "$SCRIPT_DIR/notify-deployment.sh" "$event" "Service: $service. $message" 2>/dev/null || true
    fi
}

# Deploy infrastructure (Redis, PostgreSQL)
deploy_infrastructure() {
    log_step "Deploying infrastructure services..."

    local ssh_cmd=$(get_ssh_cmd)

    # Check if Redis is already running and healthy
    log_info "Checking existing Redis..."
    if $ssh_cmd "docker exec maestro-redis redis-cli ping 2>/dev/null" | grep -q "PONG"; then
        log_success "Redis is already running and healthy"
        local redis_exists=true
    elif $ssh_cmd "redis-cli ping 2>/dev/null" | grep -q "PONG"; then
        log_success "Redis is running (non-Docker) and healthy"
        local redis_exists=true
    else
        local redis_exists=false
    fi

    # Check if PostgreSQL is already running and healthy
    log_info "Checking existing PostgreSQL..."
    if $ssh_cmd "docker exec maestro-postgres pg_isready -U maestro 2>/dev/null"; then
        log_success "PostgreSQL is already running and healthy"
        local postgres_exists=true
    elif $ssh_cmd "pg_isready -h localhost -p 5432 2>/dev/null"; then
        log_success "PostgreSQL is running (non-Docker) and healthy"
        local postgres_exists=true
    else
        local postgres_exists=false
    fi

    # If both services are running, we're done
    if $redis_exists && $postgres_exists; then
        log_success "Infrastructure services are already deployed and healthy"
        return 0
    fi

    # Create deploy directory
    $ssh_cmd "sudo mkdir -p $DEPLOY_PATH/infrastructure && sudo chown -R \$USER:\$USER $DEPLOY_PATH"

    # Only stop/remove if we need to redeploy
    if ! $redis_exists; then
        log_info "Stopping existing Redis container..."
        $ssh_cmd "docker stop maestro-redis 2>/dev/null || true"
        $ssh_cmd "docker rm maestro-redis 2>/dev/null || true"
    fi

    if ! $postgres_exists; then
        log_info "Stopping existing PostgreSQL container..."
        $ssh_cmd "docker stop maestro-postgres 2>/dev/null || true"
        $ssh_cmd "docker rm maestro-postgres 2>/dev/null || true"
    fi

    $ssh_cmd "cat > $DEPLOY_PATH/infrastructure/docker-compose.yml << 'INFRA_EOF'
version: '3.8'

services:
  redis:
    image: redis:7-alpine
    container_name: maestro-redis
    ports:
      - \"6379:6379\"
    volumes:
      - redis-data:/data
    command: redis-server --appendonly yes
    healthcheck:
      test: [\"CMD\", \"redis-cli\", \"ping\"]
      interval: 10s
      timeout: 3s
      retries: 3
    restart: unless-stopped

  postgresql:
    image: postgres:16-alpine
    container_name: maestro-postgres
    environment:
      POSTGRES_DB: maestro
      POSTGRES_USER: maestro
      POSTGRES_PASSWORD: \${POSTGRES_PASSWORD:-maestro_demo_2024}
    ports:
      - \"5432:5432\"
    volumes:
      - postgres-data:/var/lib/postgresql/data
    healthcheck:
      test: [\"CMD-SHELL\", \"pg_isready -U maestro\"]
      interval: 10s
      timeout: 3s
      retries: 3
    restart: unless-stopped

volumes:
  redis-data:
  postgres-data:
INFRA_EOF"

    # Start infrastructure
    $ssh_cmd "cd $DEPLOY_PATH/infrastructure && docker compose up -d"

    # Wait for services to be healthy
    sleep 10

    # Verify
    if $ssh_cmd "docker exec maestro-redis redis-cli ping" | grep -q "PONG"; then
        log_success "Redis is healthy"
    else
        log_error "Redis health check failed"
        return 1
    fi

    if $ssh_cmd "docker exec maestro-postgres pg_isready -U maestro" &>/dev/null; then
        log_success "PostgreSQL is healthy"
    else
        log_error "PostgreSQL health check failed"
        return 1
    fi

    log_success "Infrastructure deployed successfully"
}

# Deploy a Docker-based service
deploy_docker_service() {
    local service="$1"
    local image_name="$2"
    local container_name="$3"
    local ports="$4"
    local env_vars="${5:-}"
    local health_endpoint="${6:-}"

    log_step "Deploying $service..."

    local ssh_cmd=$(get_ssh_cmd)

    # Build port mapping
    local port_args=""
    IFS=',' read -ra PORT_ARRAY <<< "$ports"
    for port in "${PORT_ARRAY[@]}"; do
        port_args="$port_args -p $port:$port"
    done

    # Stop existing container
    $ssh_cmd "docker stop $container_name 2>/dev/null || true"
    $ssh_cmd "docker rm $container_name 2>/dev/null || true"

    # Pull latest image or build
    log_info "Pulling/building $image_name..."

    # Start container
    local docker_cmd="docker run -d --name $container_name $port_args --restart unless-stopped"

    # Add environment variables
    if [ -n "$env_vars" ]; then
        docker_cmd="$docker_cmd $env_vars"
    fi

    # Add network
    docker_cmd="$docker_cmd --network host"

    docker_cmd="$docker_cmd $image_name"

    $ssh_cmd "$docker_cmd"

    # Wait for startup
    sleep 15

    # Health check
    if [ -n "$health_endpoint" ]; then
        log_info "Checking health at $health_endpoint..."
        if $ssh_cmd "curl -sf $health_endpoint" &>/dev/null; then
            log_success "$service is healthy"
        else
            log_warning "$service health check failed (service may still be starting)"
        fi
    fi

    log_success "$service deployed"
}

# Deploy maestro-engine
deploy_maestro_engine() {
    log_step "Deploying maestro-engine..."

    local ssh_cmd=$(get_ssh_cmd)

    # For now, use docker-compose approach
    $ssh_cmd "mkdir -p $DEPLOY_PATH/maestro-engine"

    $ssh_cmd "cat > $DEPLOY_PATH/maestro-engine/docker-compose.yml << 'ENGINE_EOF'
version: '3.8'

services:
  maestro-engine:
    image: maestro-engine:latest
    container_name: maestro-engine
    ports:
      - \"5000:5000\"
      - \"4001:4001\"
    environment:
      - ENVIRONMENT=demo
      - LOG_LEVEL=INFO
      - REDIS_URL=redis://localhost:6379/0
      - DATABASE_URL=postgresql://maestro:maestro_demo_2024@localhost:5432/maestro
      - TEMPLATE_SERVICE_URL=http://localhost:9600
      - QUALITY_FABRIC_URL=http://localhost:8000
      - JWT_SECRET=\${JWT_SECRET:-demo_jwt_secret_2024}
      - ANTHROPIC_API_KEY=\${ANTHROPIC_API_KEY}
    network_mode: host
    restart: unless-stopped
    healthcheck:
      test: [\"CMD\", \"curl\", \"-f\", \"http://localhost:5000/health\"]
      interval: 30s
      timeout: 10s
      retries: 3

ENGINE_EOF"

    log_info "Note: maestro-engine requires ANTHROPIC_API_KEY to be set"
    log_info "Build and push maestro-engine:latest image first, or deploy from source"

    log_success "maestro-engine configuration created at $DEPLOY_PATH/maestro-engine"
}

# Deploy maestro-templates
deploy_maestro_templates() {
    log_step "Deploying maestro-templates..."

    local ssh_cmd=$(get_ssh_cmd)

    $ssh_cmd "mkdir -p $DEPLOY_PATH/maestro-templates"

    $ssh_cmd "cat > $DEPLOY_PATH/maestro-templates/docker-compose.yml << 'TEMPLATES_EOF'
version: '3.8'

services:
  maestro-templates:
    image: maestro-templates:latest
    container_name: maestro-templates
    ports:
      - \"9600:9600\"
    environment:
      - PORT=9600
      - DATABASE_URL=postgresql://maestro:maestro_demo_2024@localhost:5432/maestro
      - REDIS_URL=redis://localhost:6379/0
      - ENVIRONMENT=demo
      - LOG_LEVEL=INFO
    network_mode: host
    restart: unless-stopped
    healthcheck:
      test: [\"CMD\", \"curl\", \"-f\", \"http://localhost:9600/health\"]
      interval: 30s
      timeout: 10s
      retries: 3
    volumes:
      - template-storage:/app/storage

volumes:
  template-storage:

TEMPLATES_EOF"

    log_success "maestro-templates configuration created at $DEPLOY_PATH/maestro-templates"
}

# Deploy quality-fabric
deploy_quality_fabric() {
    log_step "Deploying quality-fabric..."

    local ssh_cmd=$(get_ssh_cmd)

    $ssh_cmd "mkdir -p $DEPLOY_PATH/quality-fabric"

    $ssh_cmd "cat > $DEPLOY_PATH/quality-fabric/docker-compose.yml << 'QF_EOF'
version: '3.8'

services:
  quality-fabric:
    image: quality-fabric:latest
    container_name: quality-fabric
    ports:
      - \"8000:8000\"
    environment:
      - PORT=8000
      - REDIS_URL=redis://localhost:6379/1
      - DATABASE_URL=postgresql://maestro:maestro_demo_2024@localhost:5432/maestro
      - ENVIRONMENT=demo
      - LOG_LEVEL=INFO
    network_mode: host
    restart: unless-stopped
    healthcheck:
      test: [\"CMD\", \"curl\", \"-f\", \"http://localhost:8000/health\"]
      interval: 30s
      timeout: 10s
      retries: 3

QF_EOF"

    log_success "quality-fabric configuration created at $DEPLOY_PATH/quality-fabric"
}

# Deploy gateway
deploy_gateway() {
    log_step "Deploying gateway..."

    local ssh_cmd=$(get_ssh_cmd)

    $ssh_cmd "mkdir -p $DEPLOY_PATH/gateway"

    $ssh_cmd "cat > $DEPLOY_PATH/gateway/docker-compose.yml << 'GW_EOF'
version: '3.8'

services:
  gateway:
    image: maestro-gateway:latest
    container_name: maestro-gateway
    ports:
      - \"8080:8080\"
    environment:
      - PORT=8080
      - ENVIRONMENT=demo
      - MAESTRO_ENGINE_URL=http://localhost:5000
      - TEMPLATES_URL=http://localhost:9600
      - QUALITY_FABRIC_URL=http://localhost:8000
      - FRONTEND_URL=http://localhost:4300
      - BACKEND_URL=http://localhost:3100
    network_mode: host
    restart: unless-stopped
    healthcheck:
      test: [\"CMD\", \"curl\", \"-f\", \"http://localhost:8080/health\"]
      interval: 30s
      timeout: 10s
      retries: 3

GW_EOF"

    log_success "gateway configuration created at $DEPLOY_PATH/gateway"
}

# Deploy frontend (maestro-frontend-production)
deploy_frontend() {
    log_step "Deploying maestro-frontend-production..."

    # Use existing deploy-demo.sh script
    if [ -f "$SCRIPT_DIR/deploy-demo.sh" ]; then
        log_info "Using existing deploy-demo.sh script..."
        DEMO_SERVER="$DEMO_SERVER" DEMO_USER="$DEMO_USER" SSH_KEY_PATH="$SSH_KEY_PATH" \
            "$SCRIPT_DIR/deploy-demo.sh"
    else
        log_error "deploy-demo.sh not found"
        return 1
    fi

    log_success "Frontend deployed"
}

# Deploy a specific service
deploy_service() {
    local service="$1"

    notify "started" "$service"

    case "$service" in
        infrastructure)
            deploy_infrastructure
            ;;
        maestro-engine)
            deploy_maestro_engine
            ;;
        maestro-templates)
            deploy_maestro_templates
            ;;
        quality-fabric)
            deploy_quality_fabric
            ;;
        gateway)
            deploy_gateway
            ;;
        frontend)
            deploy_frontend
            ;;
        *)
            log_error "Unknown service: $service"
            list_services
            return 1
            ;;
    esac

    local result=$?

    if [ $result -eq 0 ]; then
        notify "succeeded" "$service"
    else
        notify "failed" "$service"
    fi

    return $result
}

# Deploy all services in order
deploy_all() {
    log_info "Deploying all services in order..."

    local services=(
        "infrastructure"
        "maestro-engine"
        "maestro-templates"
        "quality-fabric"
        "gateway"
        "frontend"
    )

    for service in "${services[@]}"; do
        echo ""
        log_info "=========================================="
        log_info "Deploying: $service"
        log_info "=========================================="

        if ! deploy_service "$service"; then
            log_error "Failed to deploy $service"
            return 1
        fi

        sleep 5
    done

    echo ""
    log_success "All services deployed successfully!"
}

# Show usage
usage() {
    echo "Usage: $0 <service-name|--list|--all>"
    echo ""
    echo "Options:"
    echo "  <service-name>  Deploy specific service"
    echo "  --list          List available services"
    echo "  --all           Deploy all services in order"
    echo "  --status        Show status of all services"
    echo "  -h, --help      Show this help"
    echo ""
    echo "Environment:"
    echo "  DEMO_SERVER=$DEMO_SERVER"
    echo "  DEMO_USER=$DEMO_USER"
    echo ""
    echo "Examples:"
    echo "  $0 infrastructure"
    echo "  $0 frontend"
    echo "  $0 --all"
}

# Check service status
check_status() {
    log_info "Checking service status on $DEMO_SERVER..."

    local ssh_cmd=$(get_ssh_cmd)

    echo ""
    echo "Docker containers:"
    $ssh_cmd "docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'" 2>/dev/null || echo "Unable to get container status"

    echo ""
    echo "Health endpoints:"
    for service in "${!SERVICE_HEALTH[@]}"; do
        local endpoints="${SERVICE_HEALTH[$service]}"
        if [ -n "$endpoints" ]; then
            IFS=',' read -ra ENDPOINTS <<< "$endpoints"
            for endpoint in "${ENDPOINTS[@]}"; do
                if $ssh_cmd "curl -sf $endpoint" &>/dev/null; then
                    echo -e "  ${GREEN}✓${NC} $service: $endpoint"
                else
                    echo -e "  ${RED}✗${NC} $service: $endpoint"
                fi
            done
        fi
    done
}

# Main
main() {
    case "${1:-}" in
        --list)
            list_services
            ;;
        --all)
            check_connectivity || exit 1
            deploy_all
            ;;
        --status)
            check_connectivity || exit 1
            check_status
            ;;
        -h|--help)
            usage
            ;;
        "")
            usage
            exit 1
            ;;
        *)
            check_connectivity || exit 1
            deploy_service "$1"
            ;;
    esac
}

main "$@"

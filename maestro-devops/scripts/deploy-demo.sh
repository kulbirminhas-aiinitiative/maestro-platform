#!/usr/bin/env bash
#
# Maestro Frontend Production - Demo Environment Deployment Script
#
# This script deploys the full-stack application to a demo server
# Similar to quality-fabric's DEMO_SERVER_SETUP.md approach
#
# Usage:
#   ./scripts/deploy-demo.sh
#
# Required Environment Variables:
#   DEMO_SERVER   - Demo server hostname or IP
#   DEMO_USER     - SSH username for demo server
#   SSH_KEY_PATH  - Path to SSH key (optional)
#

set -euo pipefail

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m'

# Configuration - can be overridden by environment variables
DEMO_SERVER="${DEMO_SERVER:-}"
DEMO_USER="${DEMO_USER:-ec2-user}"
SSH_KEY_PATH="${SSH_KEY_PATH:-}"
DEMO_PATH="${DEMO_PATH:-/opt/maestro-frontend-production}"
DEPLOYMENT_LOG="deployment-$(date +%Y%m%d-%H%M%S).log"

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1" | tee -a "$DEPLOYMENT_LOG"
}

log_success() {
    echo -e "${GREEN}[✓]${NC} $1" | tee -a "$DEPLOYMENT_LOG"
}

log_warning() {
    echo -e "${YELLOW}[⚠]${NC} $1" | tee -a "$DEPLOYMENT_LOG"
}

log_error() {
    echo -e "${RED}[✗]${NC} $1" | tee -a "$DEPLOYMENT_LOG"
}

log_step() {
    echo -e "${CYAN}[STEP]${NC} $1" | tee -a "$DEPLOYMENT_LOG"
}

log_phase() {
    echo -e "${MAGENTA}[PHASE]${NC} $1" | tee -a "$DEPLOYMENT_LOG"
}

# Check required variables
check_requirements() {
    log_step "Checking deployment requirements..."

    if [ -z "$DEMO_SERVER" ]; then
        log_error "DEMO_SERVER not set. Please export DEMO_SERVER=<server-hostname-or-ip>"
        echo ""
        echo "Example:"
        echo "  export DEMO_SERVER=demo.maestro.com"
        echo "  export DEMO_USER=ec2-user"
        echo "  export SSH_KEY_PATH=~/.ssh/demo-key.pem"
        echo "  ./scripts/deploy-demo.sh"
        exit 1
    fi

    log_success "Demo server: $DEMO_SERVER"
    log_success "Demo user: $DEMO_USER"

    if [ -n "$SSH_KEY_PATH" ]; then
        log_success "SSH key: $SSH_KEY_PATH"
    fi
}

# Construct SSH command
get_ssh_cmd() {
    if [ -n "$SSH_KEY_PATH" ]; then
        echo "ssh -i $SSH_KEY_PATH $DEMO_USER@$DEMO_SERVER"
    else
        echo "ssh $DEMO_USER@$DEMO_SERVER"
    fi
}

# Test SSH connectivity
test_ssh_connection() {
    log_step "Testing SSH connectivity to demo server..."

    SSH_CMD=$(get_ssh_cmd)

    if $SSH_CMD "echo 'SSH connection successful'" &>/dev/null; then
        log_success "SSH connection established"
    else
        log_error "Cannot connect to demo server via SSH"
        log_error "Please check:"
        log_error "  1. Server hostname/IP is correct"
        log_error "  2. SSH key has correct permissions (chmod 600)"
        log_error "  3. User has access to the server"
        exit 1
    fi
}

# Check remote prerequisites
check_remote_prerequisites() {
    log_step "Checking remote server prerequisites..."

    SSH_CMD=$(get_ssh_cmd)

    # Check Docker
    log_info "Checking Docker installation..."
    if $SSH_CMD "command -v docker" &>/dev/null; then
        DOCKER_VERSION=$($SSH_CMD "docker --version | awk '{print \$3}' | sed 's/,//'")
        log_success "Docker installed (version: $DOCKER_VERSION)"
    else
        log_error "Docker not installed on remote server"
        exit 1
    fi

    # Check Docker Compose
    log_info "Checking Docker Compose..."
    if $SSH_CMD "docker compose version" &>/dev/null; then
        log_success "Docker Compose available"
    elif $SSH_CMD "command -v docker-compose" &>/dev/null; then
        log_success "Docker Compose available"
    else
        log_error "Docker Compose not available on remote server"
        exit 1
    fi

    # Check available disk space
    log_info "Checking disk space..."
    AVAILABLE_SPACE=$($SSH_CMD "df -BG $DEMO_PATH | tail -1 | awk '{print \$4}' | sed 's/G//' || df -BG / | tail -1 | awk '{print \$4}' | sed 's/G//'")
    if [ "$AVAILABLE_SPACE" -lt 20 ]; then
        log_warning "Low disk space: ${AVAILABLE_SPACE}GB (recommended: 20GB+)"
    else
        log_success "Sufficient disk space: ${AVAILABLE_SPACE}GB"
    fi

    # Check required ports
    log_info "Checking required ports..."
    for PORT in 4300 3000 17432 6379; do
        if $SSH_CMD "lsof -Pi :$PORT -sTCP:LISTEN -t" &>/dev/null; then
            log_warning "Port $PORT is already in use on remote server"
        else
            log_success "Port $PORT is available"
        fi
    done
}

# Transfer files to demo server
transfer_files() {
    log_phase "Phase 1: Transferring files to demo server"

    SSH_CMD=$(get_ssh_cmd)

    # Create deployment directory
    log_step "Creating deployment directory..."
    $SSH_CMD "sudo mkdir -p $DEMO_PATH && sudo chown $DEMO_USER:$DEMO_USER $DEMO_PATH"
    log_success "Deployment directory created: $DEMO_PATH"

    # Prepare files for transfer
    log_step "Preparing files for transfer..."
    cd "$PROJECT_ROOT"

    # Create temporary transfer directory
    TRANSFER_DIR=$(mktemp -d)
    log_info "Using temporary directory: $TRANSFER_DIR"

    # Copy necessary files
    log_info "Copying project files..."
    rsync -av \
        --exclude 'node_modules' \
        --exclude 'dist' \
        --exclude '.git' \
        --exclude 'logs' \
        --exclude '*.log' \
        --exclude 'backend.pid' \
        --exclude 'frontend.pid' \
        ./ "$TRANSFER_DIR/" 2>&1 | tee -a "$DEPLOYMENT_LOG"

    # Transfer to demo server
    log_step "Transferring files to demo server..."
    if [ -n "$SSH_KEY_PATH" ]; then
        rsync -avz --progress \
            -e "ssh -i $SSH_KEY_PATH" \
            "$TRANSFER_DIR/" \
            "$DEMO_USER@$DEMO_SERVER:$DEMO_PATH/" 2>&1 | tee -a "$DEPLOYMENT_LOG"
    else
        rsync -avz --progress \
            "$TRANSFER_DIR/" \
            "$DEMO_USER@$DEMO_SERVER:$DEMO_PATH/" 2>&1 | tee -a "$DEPLOYMENT_LOG"
    fi

    log_success "Files transferred successfully"

    # Cleanup
    rm -rf "$TRANSFER_DIR"
}

# Setup environment on demo server
setup_remote_environment() {
    log_phase "Phase 2: Setting up environment on demo server"

    SSH_CMD=$(get_ssh_cmd)

    log_step "Configuring environment files..."

    # Setup frontend environment
    $SSH_CMD "cd $DEMO_PATH && \
        if [ -f frontend/.env.example ]; then \
            cp frontend/.env.example frontend/.env; \
            sed -i 's|http://localhost:3000|http://$DEMO_SERVER:3000|g' frontend/.env; \
            sed -i 's|http://localhost:8080|http://$DEMO_SERVER:8080|g' frontend/.env; \
            echo 'Frontend environment configured'; \
        fi"

    # Setup backend environment
    $SSH_CMD "cd $DEMO_PATH && \
        if [ -f backend/.env.example ]; then \
            cp backend/.env.example backend/.env; \
            sed -i 's|localhost:17432|$DEMO_SERVER:17432|g' backend/.env; \
            sed -i 's|http://localhost:4300|http://$DEMO_SERVER:4300|g' backend/.env; \
            echo 'Backend environment configured'; \
        fi"

    log_success "Environment configured"
}

# Build and deploy on demo server
build_and_deploy() {
    log_phase "Phase 3: Building and deploying applications"

    SSH_CMD=$(get_ssh_cmd)

    log_step "Installing dependencies..."
    $SSH_CMD "cd $DEMO_PATH/backend && npm install" 2>&1 | tee -a "$DEPLOYMENT_LOG"
    $SSH_CMD "cd $DEMO_PATH/frontend && npm install" 2>&1 | tee -a "$DEPLOYMENT_LOG"
    log_success "Dependencies installed"

    log_step "Building applications..."
    $SSH_CMD "cd $DEMO_PATH/backend && npm run build" 2>&1 | tee -a "$DEPLOYMENT_LOG"
    $SSH_CMD "cd $DEMO_PATH/backend && npx prisma generate" 2>&1 | tee -a "$DEPLOYMENT_LOG"
    $SSH_CMD "cd $DEMO_PATH/frontend && npm run build" 2>&1 | tee -a "$DEPLOYMENT_LOG"
    log_success "Applications built"

    log_step "Setting up database..."
    $SSH_CMD "cd $DEMO_PATH/backend && npx prisma db push --skip-generate" 2>&1 | tee -a "$DEPLOYMENT_LOG"
    log_success "Database setup complete"
}

# Start services
start_services() {
    log_phase "Phase 4: Starting services"

    SSH_CMD=$(get_ssh_cmd)

    log_step "Starting backend service..."
    $SSH_CMD "cd $DEMO_PATH && nohup npm --prefix backend run start > logs/backend.log 2>&1 & echo \$! > backend.pid"
    sleep 5
    log_success "Backend service started"

    log_step "Starting frontend service..."
    $SSH_CMD "cd $DEMO_PATH && nohup npm --prefix frontend run preview > logs/frontend.log 2>&1 & echo \$! > frontend.pid"
    sleep 5
    log_success "Frontend service started"
}

# Run health checks
run_health_checks() {
    log_phase "Phase 5: Running health checks"

    SSH_CMD=$(get_ssh_cmd)

    log_step "Checking backend health..."
    for i in {1..10}; do
        if $SSH_CMD "curl -sf http://localhost:3000/health" > /dev/null 2>&1; then
            log_success "Backend health check passed"
            break
        elif [ $i -eq 10 ]; then
            log_error "Backend health check failed"
            exit 1
        else
            sleep 3
        fi
    done

    log_step "Checking frontend health..."
    for i in {1..10}; do
        if $SSH_CMD "curl -sf http://localhost:4300" > /dev/null 2>&1; then
            log_success "Frontend health check passed"
            break
        elif [ $i -eq 10 ]; then
            log_error "Frontend health check failed"
            exit 1
        else
            sleep 3
        fi
    done
}

# Show deployment summary
show_summary() {
    echo "" | tee -a "$DEPLOYMENT_LOG"
    echo "═══════════════════════════════════════════════════════════════" | tee -a "$DEPLOYMENT_LOG"
    echo "  Maestro Frontend Production - Demo Deployment Successful!" | tee -a "$DEPLOYMENT_LOG"
    echo "═══════════════════════════════════════════════════════════════" | tee -a "$DEPLOYMENT_LOG"
    echo "" | tee -a "$DEPLOYMENT_LOG"
    log_success "Deployment completed at $(date)"
    echo "" | tee -a "$DEPLOYMENT_LOG"
    echo "Access URLs:" | tee -a "$DEPLOYMENT_LOG"
    echo "  Frontend:  ${CYAN}http://$DEMO_SERVER:4300${NC}" | tee -a "$DEPLOYMENT_LOG"
    echo "  Backend:   ${CYAN}http://$DEMO_SERVER:3000${NC}" | tee -a "$DEPLOYMENT_LOG"
    echo "  API Docs:  ${CYAN}http://$DEMO_SERVER:3000/api/docs${NC}" | tee -a "$DEPLOYMENT_LOG"
    echo "" | tee -a "$DEPLOYMENT_LOG"
    echo "SSH Access:" | tee -a "$DEPLOYMENT_LOG"
    echo "  ${CYAN}$(get_ssh_cmd)${NC}" | tee -a "$DEPLOYMENT_LOG"
    echo "" | tee -a "$DEPLOYMENT_LOG"
    echo "Remote Management:" | tee -a "$DEPLOYMENT_LOG"
    echo "  Stop:      ${CYAN}$(get_ssh_cmd) 'cd $DEMO_PATH && ./scripts/stop-services.sh'${NC}" | tee -a "$DEPLOYMENT_LOG"
    echo "  Restart:   ${CYAN}$(get_ssh_cmd) 'cd $DEMO_PATH && ./scripts/restart-services.sh'${NC}" | tee -a "$DEPLOYMENT_LOG"
    echo "  Logs:      ${CYAN}$(get_ssh_cmd) 'cd $DEMO_PATH && tail -f logs/*.log'${NC}" | tee -a "$DEPLOYMENT_LOG"
    echo "" | tee -a "$DEPLOYMENT_LOG"
    echo "Deployment log: ${DEPLOYMENT_LOG}" | tee -a "$DEPLOYMENT_LOG"
    echo "" | tee -a "$DEPLOYMENT_LOG"
    echo "═══════════════════════════════════════════════════════════════" | tee -a "$DEPLOYMENT_LOG"
    echo "" | tee -a "$DEPLOYMENT_LOG"
}

# Main deployment flow
main() {
    echo ""
    echo "═══════════════════════════════════════════════════════════════"
    echo "  Maestro Frontend Production - Demo Server Deployment"
    echo "═══════════════════════════════════════════════════════════════"
    echo ""
    echo "This script will deploy the full-stack application to: $DEMO_SERVER"
    echo ""
    echo "Estimated time: 8-15 minutes"
    echo ""
    read -p "Continue? (y/N) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_warning "Deployment cancelled"
        exit 0
    fi

    # Run deployment phases
    check_requirements
    test_ssh_connection
    check_remote_prerequisites
    transfer_files
    setup_remote_environment
    build_and_deploy
    start_services
    run_health_checks
    show_summary
}

# Run main function
main "$@"

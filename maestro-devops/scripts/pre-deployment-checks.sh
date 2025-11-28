#!/usr/bin/env bash
#
# Maestro Frontend Production - Pre-Deployment Checks (Version 2 - Robust)
#
# This script validates that the target environment meets all requirements
# before attempting deployment.
#
# Usage:
#   ./scripts/pre-deployment-checks-v2.sh [environment]
#
# Arguments:
#   environment: development|demo|production (default: development)
#

# Don't use set -e to avoid script exit on non-critical failures
set -uo pipefail

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
ENVIRONMENT="${1:-development}"
MIN_DISK_SPACE_GB=20
MIN_MEMORY_GB=4
REQUIRED_PORTS=(4300 3000 17432 6379)

# Check counters
CHECKS_PASSED=0
CHECKS_FAILED=0
CHECKS_WARNING=0

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[✓]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[⚠]${NC} $1"
}

log_error() {
    echo -e "${RED}[✗]${NC} $1"
}

# Check Docker installation
check_docker() {
    log_info "Checking Docker installation..."

    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed"
        ((CHECKS_FAILED++))
        return 1
    fi

    DOCKER_VERSION=$(docker --version 2>/dev/null | awk '{print $3}' | sed 's/,//' || echo "unknown")
    log_success "Docker is installed (version: $DOCKER_VERSION)"
    ((CHECKS_PASSED++))

    # Check if Docker daemon is running (with timeout and error handling)
    if timeout 5 docker info &> /dev/null 2>&1; then
        log_success "Docker daemon is running"
        ((CHECKS_PASSED++))
    else
        log_warning "Docker daemon not responding (skipping)"
        ((CHECKS_WARNING++))
    fi

    return 0
}

# Check Docker Compose installation
check_docker_compose() {
    log_info "Checking Docker Compose installation..."

    if docker compose version &> /dev/null 2>&1; then
        COMPOSE_VERSION=$(docker compose version 2>/dev/null | awk '{print $4}' || echo "unknown")
        log_success "Docker Compose is installed (version: $COMPOSE_VERSION)"
        ((CHECKS_PASSED++))
    elif command -v docker-compose &> /dev/null; then
        COMPOSE_VERSION=$(docker-compose --version 2>/dev/null | awk '{print $4}' | sed 's/,//' || echo "unknown")
        log_success "Docker Compose is installed (version: $COMPOSE_VERSION)"
        ((CHECKS_PASSED++))
    else
        log_error "Docker Compose is not installed"
        ((CHECKS_FAILED++))
        return 1
    fi

    return 0
}

# Check Node.js installation
check_nodejs() {
    log_info "Checking Node.js installation..."

    if ! command -v node &> /dev/null; then
        log_error "Node.js is not installed"
        ((CHECKS_FAILED++))
        return 1
    fi

    NODE_VERSION=$(node --version 2>/dev/null || echo "unknown")
    NODE_MAJOR=$(echo "$NODE_VERSION" | cut -d'.' -f1 | sed 's/v//')

    if [ "$NODE_MAJOR" -ge 18 ] 2>/dev/null; then
        log_success "Node.js is installed (version: $NODE_VERSION)"
        ((CHECKS_PASSED++))
    else
        log_error "Node.js version must be >= 18.0.0 (found: $NODE_VERSION)"
        ((CHECKS_FAILED++))
        return 1
    fi

    return 0
}

# Check npm installation
check_npm() {
    log_info "Checking npm installation..."

    if ! command -v npm &> /dev/null; then
        log_error "npm is not installed"
        ((CHECKS_FAILED++))
        return 1
    fi

    NPM_VERSION=$(npm --version 2>/dev/null || echo "unknown")
    log_success "npm is installed (version: $NPM_VERSION)"
    ((CHECKS_PASSED++))

    return 0
}

# Check available disk space
check_disk_space() {
    log_info "Checking available disk space..."

    AVAILABLE_SPACE=$(df -BG . 2>/dev/null | tail -1 | awk '{print $4}' | sed 's/G//' || echo "0")

    if [ "$AVAILABLE_SPACE" -ge "$MIN_DISK_SPACE_GB" ] 2>/dev/null; then
        log_success "Sufficient disk space available (${AVAILABLE_SPACE}GB)"
        ((CHECKS_PASSED++))
    else
        log_error "Insufficient disk space (required: ${MIN_DISK_SPACE_GB}GB, available: ${AVAILABLE_SPACE}GB)"
        ((CHECKS_FAILED++))
        return 1
    fi

    return 0
}

# Check available memory
check_memory() {
    log_info "Checking available memory..."

    TOTAL_MEMORY=$(free -g 2>/dev/null | grep Mem | awk '{print $2}' || echo "0")

    if [ "$TOTAL_MEMORY" -ge "$MIN_MEMORY_GB" ] 2>/dev/null; then
        log_success "Sufficient memory available (${TOTAL_MEMORY}GB)"
        ((CHECKS_PASSED++))
    else
        log_warning "Low memory (recommended: ${MIN_MEMORY_GB}GB, available: ${TOTAL_MEMORY}GB)"
        ((CHECKS_WARNING++))
    fi

    return 0
}

# Check if required ports are available
check_ports() {
    log_info "Checking required ports availability..."

    for PORT in "${REQUIRED_PORTS[@]}"; do
        # Use timeout to prevent hanging
        if timeout 2 lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
            log_warning "Port $PORT is already in use"
            ((CHECKS_WARNING++))
        else
            log_success "Port $PORT is available"
            ((CHECKS_PASSED++))
        fi
    done

    return 0
}

# Check environment file exists
check_environment_files() {
    log_info "Checking environment configuration files..."

    # Check frontend .env
    if [ ! -f "frontend/.env.${ENVIRONMENT}" ] && [ ! -f "frontend/.env" ]; then
        log_error "Frontend environment file not found (frontend/.env.${ENVIRONMENT} or frontend/.env)"
        ((CHECKS_FAILED++))
    else
        log_success "Frontend environment file found"
        ((CHECKS_PASSED++))
    fi

    # Check backend .env
    if [ ! -f "backend/.env" ]; then
        log_error "Backend environment file not found (backend/.env)"
        ((CHECKS_FAILED++))
    else
        log_success "Backend environment file found"
        ((CHECKS_PASSED++))
    fi

    return 0
}

# Check PostgreSQL availability
check_postgres() {
    log_info "Checking PostgreSQL availability..."

    if ! command -v psql &> /dev/null; then
        log_warning "PostgreSQL client (psql) not found - skipping database connection test"
        ((CHECKS_WARNING++))
        return 0
    fi

    # Try to connect to PostgreSQL (will use DATABASE_URL from backend/.env if available)
    if [ -f "backend/.env" ]; then
        # Source without failing
        set +u
        source backend/.env 2>/dev/null || true
        set -u

        if [ -n "${DATABASE_URL:-}" ]; then
            if timeout 5 psql "${DATABASE_URL}" -c "SELECT 1" &> /dev/null 2>&1; then
                log_success "PostgreSQL database is accessible"
                ((CHECKS_PASSED++))
            else
                log_warning "Cannot connect to PostgreSQL database - will be created during deployment"
                ((CHECKS_WARNING++))
            fi
        else
            log_warning "DATABASE_URL not set in backend/.env"
            ((CHECKS_WARNING++))
        fi
    fi

    return 0
}

# Check Redis availability
check_redis() {
    log_info "Checking Redis availability..."

    if ! command -v redis-cli &> /dev/null; then
        log_warning "Redis client (redis-cli) not found - skipping Redis connection test"
        ((CHECKS_WARNING++))
        return 0
    fi

    # Try to ping Redis
    if [ -f "backend/.env" ]; then
        # Source without failing
        set +u
        source backend/.env 2>/dev/null || true
        set -u

        REDIS_HOST="${REDIS_HOST:-localhost}"
        REDIS_PORT="${REDIS_PORT:-6379}"

        if timeout 3 redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" ping &> /dev/null 2>&1; then
            log_success "Redis is accessible"
            ((CHECKS_PASSED++))
        else
            log_warning "Cannot connect to Redis - will be created during deployment"
            ((CHECKS_WARNING++))
        fi
    fi

    return 0
}

# Check project dependencies
check_dependencies() {
    log_info "Checking project dependencies..."

    # Check frontend dependencies
    if [ ! -d "frontend/node_modules" ]; then
        log_warning "Frontend dependencies not installed - run 'cd frontend && npm install'"
        ((CHECKS_WARNING++))
    else
        log_success "Frontend dependencies installed"
        ((CHECKS_PASSED++))
    fi

    # Check backend dependencies
    if [ ! -d "backend/node_modules" ]; then
        log_warning "Backend dependencies not installed - run 'cd backend && npm install'"
        ((CHECKS_WARNING++))
    else
        log_success "Backend dependencies installed"
        ((CHECKS_PASSED++))
    fi

    return 0
}

# Main execution
main() {
    echo ""
    echo "═══════════════════════════════════════════════════════════════"
    echo "  Maestro Frontend Production - Pre-Deployment Checks"
    echo "  Environment: ${ENVIRONMENT}"
    echo "═══════════════════════════════════════════════════════════════"
    echo ""

    # Run all checks (each check handles its own errors)
    check_docker || true
    check_docker_compose || true
    check_nodejs || true
    check_npm || true
    check_disk_space || true
    check_memory || true
    check_ports || true
    check_environment_files || true
    check_postgres || true
    check_redis || true
    check_dependencies || true

    # Summary
    echo ""
    echo "═══════════════════════════════════════════════════════════════"
    echo "  Pre-Deployment Checks Summary"
    echo "═══════════════════════════════════════════════════════════════"
    echo ""
    log_success "Checks passed: $CHECKS_PASSED"

    if [ $CHECKS_WARNING -gt 0 ]; then
        log_warning "Warnings: $CHECKS_WARNING"
    fi

    if [ $CHECKS_FAILED -gt 0 ]; then
        log_error "Checks failed: $CHECKS_FAILED"
        echo ""
        log_error "Pre-deployment checks FAILED - please fix errors before deploying"
        exit 1
    fi

    echo ""
    log_success "All critical checks PASSED - ready for deployment!"
    echo ""

    if [ $CHECKS_WARNING -gt 0 ]; then
        log_warning "Some warnings were encountered - review them before proceeding"
        echo ""
    fi

    exit 0
}

# Run main function
main "$@"

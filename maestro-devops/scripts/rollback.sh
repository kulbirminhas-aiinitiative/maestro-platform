#!/usr/bin/env bash
#
# Maestro Automated Rollback Script
#
# Implements automatic rollback on health check failure
# Maintains last 3 successful deployments for rollback
#
# Usage:
#   ./scripts/rollback.sh                    # Interactive rollback selection
#   ./scripts/rollback.sh --auto             # Auto-rollback to previous version
#   ./scripts/rollback.sh --version <tag>    # Rollback to specific version
#   ./scripts/rollback.sh --list             # List available rollback points
#
# Environment Variables:
#   DEPLOYMENT_DIR - Directory containing deployment backups (default: /opt/maestro/deployments)
#   MAX_BACKUPS    - Maximum number of backups to keep (default: 3)
#

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DEPLOYMENT_DIR="${DEPLOYMENT_DIR:-/opt/maestro/deployments}"
CURRENT_DIR="${DEPLOYMENT_DIR}/current"
MAX_BACKUPS="${MAX_BACKUPS:-3}"

# Service URLs for health checks
FRONTEND_URL="${FRONTEND_URL:-http://localhost:4300}"
BACKEND_URL="${BACKEND_URL:-http://localhost:3100}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Logging functions
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[✓]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[⚠]${NC} $1"; }
log_error() { echo -e "${RED}[✗]${NC} $1"; }

# Check if services are healthy
check_health() {
    local max_attempts="${1:-3}"
    local wait_time="${2:-10}"

    for i in $(seq 1 $max_attempts); do
        log_info "Health check attempt $i/$max_attempts..."

        local frontend_ok=false
        local backend_ok=false

        # Check frontend
        if curl -sf --max-time 5 "${FRONTEND_URL}/health" > /dev/null 2>&1; then
            frontend_ok=true
        fi

        # Check backend
        if curl -sf --max-time 5 "${BACKEND_URL}/health" > /dev/null 2>&1; then
            backend_ok=true
        fi

        if $frontend_ok && $backend_ok; then
            log_success "All services healthy"
            return 0
        fi

        if [ $i -lt $max_attempts ]; then
            log_warning "Services not healthy yet, waiting ${wait_time}s..."
            sleep $wait_time
        fi
    done

    log_error "Health check failed after $max_attempts attempts"
    return 1
}

# List available rollback points
list_backups() {
    log_info "Available rollback points:"
    echo ""

    if [ ! -d "$DEPLOYMENT_DIR" ]; then
        log_error "Deployment directory not found: $DEPLOYMENT_DIR"
        return 1
    fi

    local backups=$(ls -1t "$DEPLOYMENT_DIR" 2>/dev/null | grep -E '^backup-' || true)

    if [ -z "$backups" ]; then
        log_warning "No backup deployments found"
        return 1
    fi

    local i=1
    while read -r backup; do
        local timestamp=$(echo "$backup" | sed 's/backup-//')
        local formatted_date=$(date -d "${timestamp:0:8} ${timestamp:9:2}:${timestamp:11:2}:${timestamp:13:2}" '+%Y-%m-%d %H:%M:%S' 2>/dev/null || echo "$timestamp")

        # Get git commit info if available
        local commit_info=""
        if [ -f "$DEPLOYMENT_DIR/$backup/GIT_COMMIT" ]; then
            commit_info=" ($(cat "$DEPLOYMENT_DIR/$backup/GIT_COMMIT"))"
        fi

        echo "  $i. $backup - $formatted_date$commit_info"
        ((i++))
    done <<< "$backups"

    echo ""
    return 0
}

# Create a backup of current deployment
create_backup() {
    local timestamp=$(date +%Y%m%d-%H%M%S)
    local backup_name="backup-$timestamp"
    local backup_path="$DEPLOYMENT_DIR/$backup_name"

    log_info "Creating backup: $backup_name"

    # Create backup directory
    mkdir -p "$DEPLOYMENT_DIR"

    # Check if there's a current deployment to backup
    if [ -L "$CURRENT_DIR" ] || [ -d "$CURRENT_DIR" ]; then
        cp -a "$CURRENT_DIR" "$backup_path"

        # Save git commit info
        if [ -d "$PROJECT_ROOT/.git" ]; then
            git -C "$PROJECT_ROOT" rev-parse --short HEAD > "$backup_path/GIT_COMMIT" 2>/dev/null || true
        fi

        log_success "Backup created: $backup_path"
    else
        log_warning "No current deployment to backup"
    fi

    # Cleanup old backups (keep only MAX_BACKUPS)
    cleanup_old_backups

    echo "$backup_name"
}

# Remove old backups keeping only MAX_BACKUPS
cleanup_old_backups() {
    log_info "Cleaning up old backups (keeping last $MAX_BACKUPS)..."

    local backups=$(ls -1t "$DEPLOYMENT_DIR" 2>/dev/null | grep -E '^backup-' || true)
    local count=0

    while read -r backup; do
        ((count++))
        if [ $count -gt $MAX_BACKUPS ]; then
            log_info "Removing old backup: $backup"
            rm -rf "$DEPLOYMENT_DIR/$backup"
        fi
    done <<< "$backups"
}

# Rollback to a specific backup
rollback_to() {
    local backup_name="$1"
    local backup_path="$DEPLOYMENT_DIR/$backup_name"

    if [ ! -d "$backup_path" ]; then
        log_error "Backup not found: $backup_path"
        return 1
    fi

    log_info "Rolling back to: $backup_name"

    # Stop current services
    log_info "Stopping services..."
    docker-compose -f "$PROJECT_ROOT/docker-compose.yml" down 2>/dev/null || true

    # Swap current with backup
    if [ -L "$CURRENT_DIR" ]; then
        rm "$CURRENT_DIR"
    elif [ -d "$CURRENT_DIR" ]; then
        local temp_backup="$DEPLOYMENT_DIR/backup-rollback-$(date +%Y%m%d-%H%M%S)"
        mv "$CURRENT_DIR" "$temp_backup"
        log_info "Saved current as: $temp_backup"
    fi

    # Link backup as current
    ln -sf "$backup_path" "$CURRENT_DIR"
    log_success "Linked $backup_name as current"

    # Restart services
    log_info "Starting services..."
    docker-compose -f "$PROJECT_ROOT/docker-compose.yml" up -d

    # Wait for services to start
    sleep 10

    # Verify health
    if check_health 5 15; then
        log_success "Rollback to $backup_name successful!"
        return 0
    else
        log_error "Rollback health check failed!"
        return 1
    fi
}

# Auto-rollback to previous version
auto_rollback() {
    log_info "Initiating auto-rollback..."

    # Get the most recent backup
    local latest_backup=$(ls -1t "$DEPLOYMENT_DIR" 2>/dev/null | grep -E '^backup-' | head -1)

    if [ -z "$latest_backup" ]; then
        log_error "No backup available for rollback"
        return 1
    fi

    log_info "Auto-rolling back to: $latest_backup"
    rollback_to "$latest_backup"
}

# Interactive rollback selection
interactive_rollback() {
    list_backups || return 1

    echo -n "Enter backup number to rollback (or 'q' to quit): "
    read -r selection

    if [ "$selection" = "q" ]; then
        log_info "Rollback cancelled"
        return 0
    fi

    # Get the selected backup
    local backup=$(ls -1t "$DEPLOYMENT_DIR" 2>/dev/null | grep -E '^backup-' | sed -n "${selection}p")

    if [ -z "$backup" ]; then
        log_error "Invalid selection"
        return 1
    fi

    rollback_to "$backup"
}

# Deploy with automatic rollback on failure
deploy_with_rollback() {
    log_info "Deploying with automatic rollback protection..."

    # Create backup of current state
    create_backup

    # Run deployment
    log_info "Running deployment..."
    if "$SCRIPT_DIR/deploy-demo.sh"; then
        log_success "Deployment completed"

        # Verify health
        if check_health 5 20; then
            log_success "Deployment successful and verified!"
            return 0
        else
            log_error "Health check failed after deployment"
            log_warning "Initiating automatic rollback..."
            auto_rollback
            return 1
        fi
    else
        log_error "Deployment failed"
        log_warning "Initiating automatic rollback..."
        auto_rollback
        return 1
    fi
}

# Show usage
usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --auto              Auto-rollback to previous version"
    echo "  --version <tag>     Rollback to specific backup version"
    echo "  --list              List available rollback points"
    echo "  --deploy            Deploy with automatic rollback on failure"
    echo "  --backup            Create a backup of current deployment"
    echo "  --health            Check current health status"
    echo "  -h, --help          Show this help message"
    echo ""
    echo "Without options, runs interactive rollback selection."
}

# Main
main() {
    case "${1:-}" in
        --auto)
            auto_rollback
            ;;
        --version)
            if [ -z "${2:-}" ]; then
                log_error "Please specify backup version"
                exit 1
            fi
            rollback_to "$2"
            ;;
        --list)
            list_backups
            ;;
        --deploy)
            deploy_with_rollback
            ;;
        --backup)
            create_backup
            ;;
        --health)
            check_health
            ;;
        -h|--help)
            usage
            ;;
        "")
            interactive_rollback
            ;;
        *)
            log_error "Unknown option: $1"
            usage
            exit 1
            ;;
    esac
}

main "$@"

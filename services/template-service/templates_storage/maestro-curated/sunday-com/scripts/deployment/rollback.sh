#!/bin/bash

# Sunday.com Rollback Script
# Emergency rollback functionality for production deployments

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Configuration
ENVIRONMENT=""
DRY_RUN=false
REVISION=""
FORCE=false

# Usage information
usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Rollback Sunday.com deployment

OPTIONS:
    -e, --environment ENV    Target environment (staging|production)
    -r, --revision REV       Specific revision to rollback to (optional)
    -d, --dry-run           Show what would be rolled back
    -f, --force             Force rollback without confirmation
    -h, --help              Show this help message

EXAMPLES:
    $0 -e staging
    $0 -e production -r 3
    $0 -e production --dry-run
    $0 -e production --force

EOF
}

# Parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -e|--environment)
                ENVIRONMENT="$2"
                shift 2
                ;;
            -r|--revision)
                REVISION="$2"
                shift 2
                ;;
            -d|--dry-run)
                DRY_RUN=true
                shift
                ;;
            -f|--force)
                FORCE=true
                shift
                ;;
            -h|--help)
                usage
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                usage
                exit 1
                ;;
        esac
    done

    # Validate required arguments
    if [[ -z "$ENVIRONMENT" ]]; then
        log_error "Environment is required"
        usage
        exit 1
    fi

    # Validate environment
    if [[ "$ENVIRONMENT" != "staging" && "$ENVIRONMENT" != "production" ]]; then
        log_error "Environment must be 'staging' or 'production'"
        exit 1
    fi
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."

    # Check kubectl
    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl is required"
        exit 1
    fi

    # Check aws CLI
    if ! command -v aws &> /dev/null; then
        log_error "AWS CLI is required"
        exit 1
    fi

    # Check AWS credentials
    if ! aws sts get-caller-identity &>/dev/null; then
        log_error "AWS credentials not configured or invalid"
        exit 1
    fi

    # Check kubectl context
    local current_context=$(kubectl config current-context 2>/dev/null || echo "none")
    log_info "Current kubectl context: $current_context"

    if [[ "$ENVIRONMENT" == "production" ]]; then
        if [[ "$current_context" != *"sunday-production"* ]]; then
            log_error "kubectl context must be set to production cluster"
            log_info "Run: aws eks update-kubeconfig --name sunday-production --region us-east-1"
            exit 1
        fi
    elif [[ "$ENVIRONMENT" == "staging" ]]; then
        if [[ "$current_context" != *"sunday-staging"* ]]; then
            log_error "kubectl context must be set to staging cluster"
            log_info "Run: aws eks update-kubeconfig --name sunday-staging --region us-east-1"
            exit 1
        fi
    fi

    log_success "Prerequisites check passed"
}

# Get rollout history
get_rollout_history() {
    local deployment="$1"
    local namespace="sunday-${ENVIRONMENT}"

    log_info "Getting rollout history for $deployment..."

    kubectl rollout history deployment/"$deployment" -n "$namespace"
}

# Confirm rollback
confirm_rollback() {
    if [[ "$FORCE" == true ]] || [[ "$DRY_RUN" == true ]]; then
        return 0
    fi

    echo
    log_warning "⚠️  ROLLBACK CONFIRMATION ⚠️"
    echo "Environment: $ENVIRONMENT"
    echo "Deployments to rollback: backend-deployment, frontend-deployment"
    if [[ -n "$REVISION" ]]; then
        echo "Target revision: $REVISION"
    else
        echo "Target revision: Previous revision"
    fi
    echo

    read -p "Are you sure you want to proceed with the rollback? (yes/no): " -r
    if [[ ! $REPLY =~ ^(yes|YES)$ ]]; then
        log_info "Rollback cancelled"
        exit 0
    fi
}

# Create backup before rollback
create_backup() {
    log_info "Creating backup before rollback..."

    local namespace="sunday-${ENVIRONMENT}"
    local backup_job_name="pre-rollback-backup-$(date +%s)"

    if [[ "$DRY_RUN" == true ]]; then
        log_info "[DRY RUN] Would create backup job: $backup_job_name"
        return
    fi

    # Only create backup for production
    if [[ "$ENVIRONMENT" == "production" ]]; then
        kubectl create job "$backup_job_name" --from=cronjob/database-backup -n "$namespace"

        log_info "Waiting for backup to complete..."
        kubectl wait --for=condition=complete job/"$backup_job_name" -n "$namespace" --timeout=300s

        if kubectl get job "$backup_job_name" -n "$namespace" -o jsonpath='{.status.conditions[?(@.type=="Failed")].status}' | grep -q True; then
            log_error "Backup failed, aborting rollback"
            exit 1
        fi

        log_success "Backup completed"
    else
        log_info "Skipping backup for staging environment"
    fi
}

# Perform rollback
perform_rollback() {
    local namespace="sunday-${ENVIRONMENT}"

    log_info "Performing rollback..."

    if [[ "$DRY_RUN" == true ]]; then
        log_info "[DRY RUN] Would rollback deployments in namespace: $namespace"
        if [[ -n "$REVISION" ]]; then
            log_info "[DRY RUN] Would rollback to revision: $REVISION"
        else
            log_info "[DRY RUN] Would rollback to previous revision"
        fi
        return
    fi

    # Rollback backend deployment
    log_info "Rolling back backend deployment..."
    if [[ -n "$REVISION" ]]; then
        kubectl rollout undo deployment/backend-deployment --to-revision="$REVISION" -n "$namespace"
    else
        kubectl rollout undo deployment/backend-deployment -n "$namespace"
    fi

    # Rollback frontend deployment
    log_info "Rolling back frontend deployment..."
    if [[ -n "$REVISION" ]]; then
        kubectl rollout undo deployment/frontend-deployment --to-revision="$REVISION" -n "$namespace"
    else
        kubectl rollout undo deployment/frontend-deployment -n "$namespace"
    fi

    # Wait for rollback to complete
    log_info "Waiting for rollback to complete..."
    kubectl rollout status deployment/backend-deployment -n "$namespace" --timeout=600s
    kubectl rollout status deployment/frontend-deployment -n "$namespace" --timeout=600s

    log_success "Rollback completed"
}

# Verify rollback
verify_rollback() {
    log_info "Verifying rollback..."

    if [[ "$DRY_RUN" == true ]]; then
        log_info "[DRY RUN] Would verify rollback"
        return
    fi

    # Wait for services to stabilize
    sleep 30

    # Run health checks
    local health_script="$(dirname "$0")/../monitoring/health-check.sh"
    if [[ -f "$health_script" ]]; then
        log_info "Running health checks..."
        bash "$health_script" -e "$ENVIRONMENT"
    else
        log_warning "Health check script not found, performing basic checks..."

        # Basic API health check
        local api_url=""
        if [[ "$ENVIRONMENT" == "staging" ]]; then
            api_url="https://staging-api.sunday.com"
        else
            api_url="https://api.sunday.com"
        fi

        if curl -f "${api_url}/health" >/dev/null 2>&1; then
            log_success "API health check passed"
        else
            log_error "API health check failed"
            exit 1
        fi
    fi

    log_success "Rollback verification completed"
}

# Send notification
send_notification() {
    local status="$1"

    if [[ -z "$SLACK_WEBHOOK_URL" ]]; then
        log_warning "SLACK_WEBHOOK_URL not set, skipping notification"
        return
    fi

    local emoji="✅"
    local color="good"
    if [[ "$status" != "success" ]]; then
        emoji="❌"
        color="danger"
    fi

    local message="${emoji} Rollback ${status} for ${ENVIRONMENT} environment"

    if [[ "$DRY_RUN" == true ]]; then
        log_info "[DRY RUN] Would send notification: $message"
        return
    fi

    curl -X POST -H 'Content-type: application/json' \
        --data "{\"attachments\":[{\"color\":\"${color}\",\"text\":\"${message}\"}]}" \
        "$SLACK_WEBHOOK_URL" >/dev/null 2>&1 || true
}

# Show current deployment status
show_deployment_status() {
    local namespace="sunday-${ENVIRONMENT}"

    log_info "Current deployment status:"
    echo

    # Show deployments
    kubectl get deployments -n "$namespace" -o wide

    echo

    # Show rollout history for both deployments
    echo "Backend deployment history:"
    get_rollout_history "backend-deployment"

    echo
    echo "Frontend deployment history:"
    get_rollout_history "frontend-deployment"
}

# Main rollback function
main() {
    log_info "🔄 Starting rollback for $ENVIRONMENT environment"

    if [[ "$DRY_RUN" == true ]]; then
        log_warning "Running in DRY RUN mode - no actual changes will be made"
    fi

    check_prerequisites
    show_deployment_status
    confirm_rollback
    create_backup
    perform_rollback
    verify_rollback

    log_success "🎉 Rollback completed successfully!"
    send_notification "success"
}

# Error handling
cleanup() {
    local exit_code=$?
    if [[ $exit_code -ne 0 ]]; then
        log_error "Rollback failed"
        send_notification "failed"
    fi
}

trap cleanup EXIT

# Parse arguments and run
parse_args "$@"
main
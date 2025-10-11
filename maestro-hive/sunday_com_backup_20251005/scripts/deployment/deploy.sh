#!/bin/bash

# Sunday.com Deployment Script
# This script handles deployment to different environments

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
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
ENVIRONMENT=""
VERSION=""
DRY_RUN=false
SKIP_TESTS=false
BACKUP_DB=true

# Usage information
usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Deploy Sunday.com to specified environment

OPTIONS:
    -e, --environment ENV    Target environment (staging|production)
    -v, --version VERSION    Version/tag to deploy
    -d, --dry-run           Show what would be deployed without actually deploying
    -s, --skip-tests        Skip running tests before deployment
    -n, --no-backup         Skip database backup (production only)
    -h, --help              Show this help message

EXAMPLES:
    $0 -e staging -v main
    $0 -e production -v v1.2.3
    $0 -e staging -v main --dry-run
    $0 -e production -v v1.2.3 --skip-tests --no-backup

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
            -v|--version)
                VERSION="$2"
                shift 2
                ;;
            -d|--dry-run)
                DRY_RUN=true
                shift
                ;;
            -s|--skip-tests)
                SKIP_TESTS=true
                shift
                ;;
            -n|--no-backup)
                BACKUP_DB=false
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

    if [[ -z "$VERSION" ]]; then
        log_error "Version is required"
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

    local missing_tools=()

    # Check kubectl
    if ! command -v kubectl &> /dev/null; then
        missing_tools+=("kubectl")
    fi

    # Check aws CLI
    if ! command -v aws &> /dev/null; then
        missing_tools+=("aws")
    fi

    # Check docker
    if ! command -v docker &> /dev/null; then
        missing_tools+=("docker")
    fi

    # Check helm (if using Helm charts)
    if ! command -v helm &> /dev/null; then
        missing_tools+=("helm")
    fi

    if [ ${#missing_tools[@]} -ne 0 ]; then
        log_error "Missing required tools: ${missing_tools[*]}"
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
            log_error "kubectl context must be set to production cluster for production deployment"
            log_info "Run: aws eks update-kubeconfig --name sunday-production --region us-east-1"
            exit 1
        fi
    elif [[ "$ENVIRONMENT" == "staging" ]]; then
        if [[ "$current_context" != *"sunday-staging"* ]]; then
            log_error "kubectl context must be set to staging cluster for staging deployment"
            log_info "Run: aws eks update-kubeconfig --name sunday-staging --region us-east-1"
            exit 1
        fi
    fi

    log_success "Prerequisites check passed"
}

# Run tests
run_tests() {
    if [[ "$SKIP_TESTS" == true ]]; then
        log_warning "Skipping tests as requested"
        return
    fi

    log_info "Running tests..."

    cd "$PROJECT_ROOT"

    # Backend tests
    log_info "Running backend tests..."
    cd backend
    npm test
    cd ..

    # Frontend tests
    log_info "Running frontend tests..."
    cd frontend
    npm test
    cd ..

    log_success "All tests passed"
}

# Create database backup (production only)
create_backup() {
    if [[ "$ENVIRONMENT" != "production" || "$BACKUP_DB" != true ]]; then
        log_info "Skipping database backup"
        return
    fi

    log_info "Creating database backup..."

    local backup_job_name="backup-$(date +%s)"

    if [[ "$DRY_RUN" == true ]]; then
        log_info "[DRY RUN] Would create backup job: $backup_job_name"
        return
    fi

    kubectl create job "$backup_job_name" --from=cronjob/database-backup -n sunday-production

    # Wait for backup to complete
    log_info "Waiting for backup to complete..."
    kubectl wait --for=condition=complete job/"$backup_job_name" -n sunday-production --timeout=600s

    if kubectl get job "$backup_job_name" -n sunday-production -o jsonpath='{.status.conditions[?(@.type=="Failed")].status}' | grep -q True; then
        log_error "Backup failed"
        exit 1
    fi

    log_success "Database backup completed"
}

# Build and push Docker images
build_and_push_images() {
    log_info "Building and pushing Docker images..."

    cd "$PROJECT_ROOT"

    local image_tag="${VERSION}"
    local registry="ghcr.io/sunday-com/sunday"

    if [[ "$DRY_RUN" == true ]]; then
        log_info "[DRY RUN] Would build and push:"
        log_info "  ${registry}/backend:${image_tag}"
        log_info "  ${registry}/frontend:${image_tag}"
        return
    fi

    # Login to GitHub Container Registry
    echo "$GITHUB_TOKEN" | docker login ghcr.io -u "$GITHUB_ACTOR" --password-stdin

    # Build backend image
    log_info "Building backend image..."
    docker build -t "${registry}/backend:${image_tag}" ./backend

    # Build frontend image
    log_info "Building frontend image..."
    docker build -t "${registry}/frontend:${image_tag}" ./frontend

    # Push images
    log_info "Pushing images..."
    docker push "${registry}/backend:${image_tag}"
    docker push "${registry}/frontend:${image_tag}"

    log_success "Images built and pushed"
}

# Deploy to Kubernetes
deploy_to_kubernetes() {
    log_info "Deploying to Kubernetes..."

    cd "$PROJECT_ROOT/k8s/${ENVIRONMENT}"

    if [[ "$DRY_RUN" == true ]]; then
        log_info "[DRY RUN] Would deploy to $ENVIRONMENT with version $VERSION"
        kustomize build . | sed "s|IMAGE_TAG|${VERSION}|g"
        return
    fi

    # Update image tags in kustomization
    sed -i "s|IMAGE_TAG|${VERSION}|g" kustomization.yaml

    # Apply Kubernetes manifests
    kubectl apply -k .

    # Wait for deployments to be ready
    log_info "Waiting for deployments to be ready..."

    kubectl rollout status deployment/backend-deployment -n "sunday-${ENVIRONMENT}" --timeout=600s
    kubectl rollout status deployment/frontend-deployment -n "sunday-${ENVIRONMENT}" --timeout=600s

    log_success "Deployment completed"
}

# Run smoke tests
run_smoke_tests() {
    log_info "Running smoke tests..."

    local api_url=""
    local web_url=""

    if [[ "$ENVIRONMENT" == "staging" ]]; then
        api_url="https://staging-api.sunday.com"
        web_url="https://staging.sunday.com"
    else
        api_url="https://api.sunday.com"
        web_url="https://sunday.com"
    fi

    if [[ "$DRY_RUN" == true ]]; then
        log_info "[DRY RUN] Would run smoke tests against:"
        log_info "  API: $api_url"
        log_info "  Web: $web_url"
        return
    fi

    # Wait for services to be ready
    sleep 30

    # Test API health
    log_info "Testing API health..."
    if ! curl -f "${api_url}/health" >/dev/null 2>&1; then
        log_error "API health check failed"
        exit 1
    fi

    # Test web application
    log_info "Testing web application..."
    if ! curl -f "${web_url}/" >/dev/null 2>&1; then
        log_error "Web application check failed"
        exit 1
    fi

    log_success "Smoke tests passed"
}

# Send notification
send_notification() {
    if [[ -z "$SLACK_WEBHOOK_URL" ]]; then
        log_warning "SLACK_WEBHOOK_URL not set, skipping notification"
        return
    fi

    local status="$1"
    local color="good"
    local emoji="✅"

    if [[ "$status" != "success" ]]; then
        color="danger"
        emoji="❌"
    fi

    local message="${emoji} Deployment to ${ENVIRONMENT} ${status}"
    if [[ "$status" == "success" ]]; then
        message="$message\nVersion: ${VERSION}\nEnvironment: ${ENVIRONMENT}"
    fi

    if [[ "$DRY_RUN" == true ]]; then
        log_info "[DRY RUN] Would send notification: $message"
        return
    fi

    curl -X POST -H 'Content-type: application/json' \
        --data "{\"attachments\":[{\"color\":\"${color}\",\"text\":\"${message}\"}]}" \
        "$SLACK_WEBHOOK_URL"
}

# Rollback function
rollback() {
    log_info "Rolling back deployment..."

    cd "$PROJECT_ROOT/k8s/${ENVIRONMENT}"

    kubectl rollout undo deployment/backend-deployment -n "sunday-${ENVIRONMENT}"
    kubectl rollout undo deployment/frontend-deployment -n "sunday-${ENVIRONMENT}"

    kubectl rollout status deployment/backend-deployment -n "sunday-${ENVIRONMENT}" --timeout=600s
    kubectl rollout status deployment/frontend-deployment -n "sunday-${ENVIRONMENT}" --timeout=600s

    log_success "Rollback completed"
}

# Cleanup on exit
cleanup() {
    local exit_code=$?
    if [[ $exit_code -ne 0 ]]; then
        log_error "Deployment failed"
        send_notification "failed"

        if [[ "$ENVIRONMENT" == "production" ]]; then
            read -p "Do you want to rollback? (y/N): " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                rollback
            fi
        fi
    fi
}

# Set up error handling
trap cleanup EXIT

# Main deployment function
main() {
    log_info "🚀 Starting deployment to $ENVIRONMENT (version: $VERSION)"

    if [[ "$DRY_RUN" == true ]]; then
        log_warning "Running in DRY RUN mode - no actual changes will be made"
    fi

    check_prerequisites
    run_tests
    create_backup
    build_and_push_images
    deploy_to_kubernetes
    run_smoke_tests

    log_success "🎉 Deployment completed successfully!"
    send_notification "success"
}

# Parse arguments and run
parse_args "$@"
main
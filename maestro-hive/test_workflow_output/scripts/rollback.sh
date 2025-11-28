#!/bin/bash
set -euo pipefail

# Rollback script for User Management API
# Usage: ./rollback.sh [environment] [revision]

ENVIRONMENT=${1:-dev}
REVISION=${2:-0}  # 0 means previous revision
NAMESPACE="user-management"
APP_NAME="user-mgmt-api"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

configure_kubectl() {
    log_info "Configuring kubectl for environment: $ENVIRONMENT"

    if [ "$ENVIRONMENT" == "prod" ]; then
        aws eks update-kubeconfig --name prod-cluster --region us-east-1
    else
        aws eks update-kubeconfig --name dev-cluster --region us-east-1
    fi
}

show_rollout_history() {
    log_info "Rollout history for $APP_NAME:"
    kubectl rollout history deployment/$APP_NAME -n $NAMESPACE
}

perform_rollback() {
    if [ "$REVISION" -eq 0 ]; then
        log_info "Rolling back to previous revision..."
        kubectl rollout undo deployment/$APP_NAME -n $NAMESPACE
    else
        log_info "Rolling back to revision $REVISION..."
        kubectl rollout undo deployment/$APP_NAME -n $NAMESPACE --to-revision=$REVISION
    fi

    kubectl rollout status deployment/$APP_NAME -n $NAMESPACE --timeout=10m

    if [ $? -eq 0 ]; then
        log_info "Rollback completed successfully"
    else
        log_error "Rollback failed"
        exit 1
    fi
}

verify_rollback() {
    log_info "Verifying rollback..."

    kubectl get pods -n $NAMESPACE -l app=$APP_NAME

    # Health check
    kubectl run verify-test --rm -i --restart=Never \
        --image=curlimages/curl:latest \
        --namespace=$NAMESPACE \
        -- curl -f http://${APP_NAME}-service/health || {
        log_error "Health check failed after rollback"
        exit 1
    }

    log_info "Rollback verification passed"
}

main() {
    log_info "Starting rollback for environment: $ENVIRONMENT"

    configure_kubectl
    show_rollout_history

    read -p "Are you sure you want to rollback? (yes/no): " confirmation
    if [ "$confirmation" != "yes" ]; then
        log_info "Rollback cancelled"
        exit 0
    fi

    perform_rollback
    verify_rollback

    log_info "Rollback completed successfully!"
}

main

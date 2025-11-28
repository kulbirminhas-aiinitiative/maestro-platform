#!/bin/bash
set -euo pipefail

# Deployment script for User Management API
# Usage: ./deploy.sh [environment] [image-tag]

ENVIRONMENT=${1:-dev}
IMAGE_TAG=${2:-latest}
NAMESPACE="user-management"
APP_NAME="user-mgmt-api"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_prerequisites() {
    log_info "Checking prerequisites..."

    command -v kubectl >/dev/null 2>&1 || { log_error "kubectl is required but not installed."; exit 1; }
    command -v docker >/dev/null 2>&1 || { log_error "docker is required but not installed."; exit 1; }

    log_info "Prerequisites check passed"
}

configure_kubectl() {
    log_info "Configuring kubectl for environment: $ENVIRONMENT"

    if [ "$ENVIRONMENT" == "prod" ]; then
        aws eks update-kubeconfig --name prod-cluster --region us-east-1
    else
        aws eks update-kubeconfig --name dev-cluster --region us-east-1
    fi

    kubectl cluster-info >/dev/null 2>&1 || { log_error "Cannot connect to cluster"; exit 1; }
}

apply_secrets() {
    log_info "Applying secrets..."

    # Retrieve secrets from AWS Secrets Manager
    DB_PASSWORD=$(aws secretsmanager get-secret-value --secret-id user-management-${ENVIRONMENT}-secrets --query SecretString --output text | jq -r .database_password)
    SECRET_KEY=$(aws secretsmanager get-secret-value --secret-id user-management-${ENVIRONMENT}-secrets --query SecretString --output text | jq -r .secret_key)

    # Create/update secrets in Kubernetes
    kubectl create secret generic user-mgmt-secrets \
        --from-literal=DATABASE_PASSWORD="$DB_PASSWORD" \
        --from-literal=SECRET_KEY="$SECRET_KEY" \
        --namespace=$NAMESPACE \
        --dry-run=client -o yaml | kubectl apply -f -

    log_info "Secrets applied successfully"
}

apply_manifests() {
    log_info "Applying Kubernetes manifests..."

    kubectl apply -f k8s/namespace.yaml
    kubectl apply -f k8s/configmap.yaml
    kubectl apply -f k8s/secrets.yaml
    kubectl apply -f k8s/postgres-deployment.yaml
    kubectl apply -f k8s/redis-deployment.yaml

    log_info "Waiting for database services to be ready..."
    kubectl wait --for=condition=ready pod -l app=postgres -n $NAMESPACE --timeout=300s
    kubectl wait --for=condition=ready pod -l app=redis -n $NAMESPACE --timeout=300s

    log_info "Applying API deployment..."
    kubectl apply -f k8s/api-deployment.yaml
    kubectl apply -f k8s/ingress.yaml
    kubectl apply -f k8s/hpa.yaml
    kubectl apply -f k8s/network-policy.yaml
}

update_image() {
    log_info "Updating application image to: $IMAGE_TAG"

    kubectl set image deployment/$APP_NAME \
        api=ghcr.io/your-org/user-management-api:$IMAGE_TAG \
        -n $NAMESPACE
}

wait_for_rollout() {
    log_info "Waiting for deployment rollout..."

    kubectl rollout status deployment/$APP_NAME -n $NAMESPACE --timeout=10m

    if [ $? -eq 0 ]; then
        log_info "Deployment rolled out successfully"
    else
        log_error "Deployment rollout failed"
        log_warn "Rolling back deployment..."
        kubectl rollout undo deployment/$APP_NAME -n $NAMESPACE
        exit 1
    fi
}

run_smoke_tests() {
    log_info "Running smoke tests..."

    # Get service endpoint
    SERVICE_IP=$(kubectl get svc ${APP_NAME}-service -n $NAMESPACE -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')

    if [ -z "$SERVICE_IP" ]; then
        SERVICE_IP="user-mgmt-api-service"
    fi

    # Health check
    kubectl run smoke-test --rm -i --restart=Never \
        --image=curlimages/curl:latest \
        --namespace=$NAMESPACE \
        -- curl -f http://${SERVICE_IP}/health || {
        log_error "Smoke tests failed"
        exit 1
    }

    log_info "Smoke tests passed"
}

show_deployment_info() {
    log_info "Deployment Information:"
    echo "======================================"
    kubectl get pods -n $NAMESPACE
    echo "======================================"
    kubectl get svc -n $NAMESPACE
    echo "======================================"
    log_info "Deployment completed successfully!"
}

# Main execution
main() {
    log_info "Starting deployment for environment: $ENVIRONMENT with image tag: $IMAGE_TAG"

    check_prerequisites
    configure_kubectl
    apply_secrets
    apply_manifests
    update_image
    wait_for_rollout
    run_smoke_tests
    show_deployment_info
}

main

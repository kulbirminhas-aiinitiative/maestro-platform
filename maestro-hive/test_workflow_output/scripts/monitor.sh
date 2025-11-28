#!/bin/bash

# Monitoring script for User Management API
# Usage: ./monitor.sh [environment]

ENVIRONMENT=${1:-dev}
NAMESPACE="user-management"
APP_NAME="user-mgmt-api"

GREEN='\033[0;32m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

configure_kubectl() {
    if [ "$ENVIRONMENT" == "prod" ]; then
        aws eks update-kubeconfig --name prod-cluster --region us-east-1 >/dev/null 2>&1
    else
        aws eks update-kubeconfig --name dev-cluster --region us-east-1 >/dev/null 2>&1
    fi
}

show_status() {
    clear
    echo "========================================="
    echo "User Management API - Monitoring Dashboard"
    echo "Environment: $ENVIRONMENT"
    echo "Timestamp: $(date)"
    echo "========================================="
    echo ""

    log_info "Pod Status:"
    kubectl get pods -n $NAMESPACE -o wide
    echo ""

    log_info "Service Status:"
    kubectl get svc -n $NAMESPACE
    echo ""

    log_info "HPA Status:"
    kubectl get hpa -n $NAMESPACE
    echo ""

    log_info "Resource Usage:"
    kubectl top pods -n $NAMESPACE 2>/dev/null || echo "Metrics server not available"
    echo ""

    log_info "Recent Events:"
    kubectl get events -n $NAMESPACE --sort-by='.lastTimestamp' | tail -10
    echo ""

    log_info "Endpoint Health:"
    kubectl run health-check --rm -i --restart=Never \
        --image=curlimages/curl:latest \
        --namespace=$NAMESPACE \
        -- curl -s http://${APP_NAME}-service/health | jq '.' || echo "Health check failed"
}

configure_kubectl
show_status

# Continuous monitoring
while true; do
    sleep 30
    show_status
done

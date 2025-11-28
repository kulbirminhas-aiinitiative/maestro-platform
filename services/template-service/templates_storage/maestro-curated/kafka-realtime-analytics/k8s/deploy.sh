#!/bin/bash
# Kubernetes Deployment Script for Real-Time Analytics Platform

set -e

echo "==================================="
echo "Deploying Analytics Platform to K8s"
echo "==================================="

# Color output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if kubectl is available
if ! command -v kubectl &> /dev/null; then
    echo "Error: kubectl is not installed"
    exit 1
fi

echo -e "${YELLOW}Step 1: Creating namespace${NC}"
kubectl apply -f namespace.yaml

echo -e "${YELLOW}Step 2: Deploying Zookeeper and Kafka${NC}"
kubectl apply -f kafka-deployment.yaml

echo -e "${YELLOW}Step 3: Deploying PostgreSQL${NC}"
kubectl apply -f postgres-deployment.yaml

echo -e "${YELLOW}Step 4: Deploying Redis${NC}"
kubectl apply -f redis-deployment.yaml

echo -e "${YELLOW}Step 5: Waiting for infrastructure services to be ready...${NC}"
kubectl wait --for=condition=ready pod -l app=zookeeper -n analytics-platform --timeout=300s || true
kubectl wait --for=condition=ready pod -l app=kafka -n analytics-platform --timeout=300s || true
kubectl wait --for=condition=ready pod -l app=postgres -n analytics-platform --timeout=300s || true
kubectl wait --for=condition=ready pod -l app=redis -n analytics-platform --timeout=300s || true

echo -e "${YELLOW}Step 6: Deploying Producer service${NC}"
kubectl apply -f producer-deployment.yaml

echo -e "${YELLOW}Step 7: Deploying Stream Processor${NC}"
kubectl apply -f stream-processor-deployment.yaml

echo -e "${YELLOW}Step 8: Deploying API service${NC}"
kubectl apply -f api-deployment.yaml

echo -e "${YELLOW}Step 9: Deploying Monitoring (Prometheus & Grafana)${NC}"
kubectl apply -f monitoring-deployment.yaml

echo -e "${YELLOW}Step 10: Waiting for application services to be ready...${NC}"
kubectl wait --for=condition=ready pod -l app=producer -n analytics-platform --timeout=300s || true
kubectl wait --for=condition=ready pod -l app=api -n analytics-platform --timeout=300s || true

echo ""
echo -e "${GREEN}==================================="
echo "Deployment Complete!"
echo -e "===================================${NC}"
echo ""
echo "Service endpoints:"
echo ""
echo "Get service URLs:"
echo "  kubectl get svc -n analytics-platform"
echo ""
echo "Check pod status:"
echo "  kubectl get pods -n analytics-platform"
echo ""
echo "View logs:"
echo "  kubectl logs -f <pod-name> -n analytics-platform"
echo ""
echo "Access Grafana (after LoadBalancer is provisioned):"
echo "  kubectl get svc grafana -n analytics-platform"
echo "  Default credentials: admin/admin"
echo ""
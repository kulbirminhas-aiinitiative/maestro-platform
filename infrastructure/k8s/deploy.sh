#!/bin/bash
# Kubernetes Deployment Script for Maestro Platform
# Usage: ./deploy.sh [demo|staging|prod]

set -e

ENVIRONMENT=${1:-demo}
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "🚀 Deploying Maestro Platform to Kubernetes ($ENVIRONMENT)"
echo "=============================================="

# Check prerequisites
if ! command -v kubectl &> /dev/null; then
    echo "❌ kubectl not found. Please install kubectl first."
    exit 1
fi

if ! command -v kustomize &> /dev/null; then
    echo "❌ kustomize not found. Please install kustomize first."
    exit 1
fi

# Check cluster connectivity
if ! kubectl cluster-info &> /dev/null; then
    echo "❌ Cannot connect to Kubernetes cluster."
    echo "Please configure kubectl to connect to your cluster."
    exit 1
fi

echo "✅ Prerequisites OK"
echo ""

# Deploy using kustomize
echo "📦 Applying Kubernetes manifests..."
kubectl apply -k "$SCRIPT_DIR/overlays/$ENVIRONMENT"

echo ""
echo "⏳ Waiting for deployments to be ready..."

# Wait for StatefulSets
kubectl wait --for=condition=ready pod \
  -l app=postgres \
  -n maestro-$ENVIRONMENT \
  --timeout=300s || true

kubectl wait --for=condition=ready pod \
  -l app=redis \
  -n maestro-$ENVIRONMENT \
  --timeout=300s || true

# Wait for Deployments
kubectl wait --for=condition=available deployment \
  -l app=prometheus \
  -n maestro-$ENVIRONMENT \
  --timeout=300s || true

kubectl wait --for=condition=available deployment \
  -l app=grafana \
  -n maestro-$ENVIRONMENT \
  --timeout=300s || true

echo ""
echo "✅ Deployment Complete!"
echo ""
echo "📊 Status:"
kubectl get pods -n maestro-$ENVIRONMENT
echo ""
echo "🌐 Services:"
kubectl get svc -n maestro-$ENVIRONMENT
echo ""
echo "💾 Storage:"
kubectl get pvc -n maestro-$ENVIRONMENT
echo ""

# Get Grafana URL
if [ "$ENVIRONMENT" == "prod" ]; then
    GRAFANA_IP=$(kubectl get svc maestro-grafana -n maestro-$ENVIRONMENT -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "pending...")
    echo "📈 Grafana URL: http://$GRAFANA_IP:3000"
else
    echo "📈 To access Grafana:"
    echo "   kubectl port-forward -n maestro-$ENVIRONMENT svc/maestro-grafana 3000:3000"
fi

echo ""
echo "✨ Done! Maestro Platform is running on Kubernetes"

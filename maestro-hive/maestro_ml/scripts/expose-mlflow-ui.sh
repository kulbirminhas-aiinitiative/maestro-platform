#!/bin/bash
# expose-mlflow-ui.sh - Quick script to expose MLflow UI

set -e

echo "🚀 Exposing MLflow UI for Maestro ML Platform"
echo "=============================================="
echo ""

# Check if kubectl is available
if ! command -v kubectl &> /dev/null; then
    echo "❌ kubectl not found. Please install kubectl first."
    exit 1
fi

# Check if mlflow service exists
if ! kubectl get svc mlflow-tracking -n ml-platform &> /dev/null; then
    echo "❌ MLflow tracking service not found in ml-platform namespace"
    echo "   Please ensure MLflow is deployed first."
    exit 1
fi

# Option 1: Port-forward (development)
echo "Option 1: Port-forward (Development)"
echo "------------------------------------"
echo "Command: kubectl port-forward -n ml-platform svc/mlflow-tracking 5000:5000"
echo ""

# Option 2: NodePort (testing)
echo "Option 2: NodePort Service (Testing)"
echo "------------------------------------"
echo "Applying NodePort configuration..."
kubectl apply -f infrastructure/kubernetes/mlflow-ui-ingress.yaml

# Get the node IP
NODE_IP=$(kubectl get nodes -o jsonpath='{.items[0].status.addresses[?(@.type=="InternalIP")].address}')
echo "✅ MLflow UI available at: http://$NODE_IP:30500"
echo ""

# Option 3: Ingress (production)
echo "Option 3: Ingress (Production)"
echo "------------------------------------"
echo "Add this to /etc/hosts:"
echo "$NODE_IP mlflow.maestro-ml.local"
echo ""
echo "Then access: http://mlflow.maestro-ml.local"
echo ""

echo "📝 Choose your preferred access method:"
echo "   - Port-forward: Quick development access"
echo "   - NodePort: Testing with team members"
echo "   - Ingress: Production deployment with custom domain"
echo ""

# Show current status
echo "Current MLflow Service Status:"
kubectl get svc mlflow-tracking -n ml-platform

echo ""
echo "✅ MLflow UI exposure configured!"
echo ""
echo "Next steps:"
echo "1. Access the UI using one of the methods above"
echo "2. Verify you can browse models and experiments"
echo "3. Proceed with React wrapper development"

#!/bin/bash
# Test Kubernetes Connectivity and Resources

echo "Testing Kubernetes connectivity..."

# Check if kubectl is available
if ! command -v kubectl &> /dev/null; then
    echo "⚠️  kubectl not found - skipping Kubernetes tests"
    exit 0
fi

# Check if cluster is accessible
if ! kubectl cluster-info &> /dev/null; then
    echo "⚠️  Kubernetes cluster not accessible - skipping tests"
    exit 0
fi

echo "✅ Kubernetes cluster accessible"

# Check for ML platform namespaces
for ns in ml-platform ml-serving kubeflow-training observability security; do
    if kubectl get namespace "$ns" &> /dev/null; then
        echo "✅ Namespace exists: $ns"
    else
        echo "ℹ️  Namespace not found: $ns (may need to be created)"
    fi
done

echo "✅ Kubernetes connectivity tests passed"

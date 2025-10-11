#!/bin/bash
# Maestro ML Platform - Minikube Local Test Environment Setup
# Complete local testing before production deployment

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo "========================================="
echo "ML Platform - Minikube Test Environment"
echo "========================================="
echo ""

# Check prerequisites
echo "Step 1: Checking prerequisites..."

if ! command -v minikube &> /dev/null; then
    echo -e "${RED}ERROR: minikube is not installed${NC}"
    echo "Install from: https://minikube.sigs.k8s.io/docs/start/"
    exit 1
fi

if ! command -v kubectl &> /dev/null; then
    echo -e "${RED}ERROR: kubectl is not installed${NC}"
    exit 1
fi

if ! command -v helm &> /dev/null; then
    echo -e "${YELLOW}WARNING: helm is not installed (optional but recommended)${NC}"
fi

echo -e "${GREEN}✓ Prerequisites satisfied${NC}"
echo ""

# Minikube configuration
CPU_CORES=${MINIKUBE_CPUS:-4}
MEMORY_MB=${MINIKUBE_MEMORY:-8192}
DISK_SIZE=${MINIKUBE_DISK:-40g}
DRIVER=${MINIKUBE_DRIVER:-docker}

echo "Step 2: Starting minikube cluster..."
echo "  CPUs: $CPU_CORES"
echo "  Memory: $MEMORY_MB MB"
echo "  Disk: $DISK_SIZE"
echo "  Driver: $DRIVER"
echo ""

# Check if minikube is already running
if minikube status &> /dev/null; then
    echo -e "${YELLOW}Minikube is already running${NC}"
    read -p "Delete and recreate? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        minikube delete
        minikube start --cpus=$CPU_CORES --memory=$MEMORY_MB --disk-size=$DISK_SIZE --driver=$DRIVER
    fi
else
    minikube start --cpus=$CPU_CORES --memory=$MEMORY_MB --disk-size=$DISK_SIZE --driver=$DRIVER
fi

echo -e "${GREEN}✓ Minikube cluster started${NC}"
echo ""

# Enable addons
echo "Step 3: Enabling minikube addons..."
minikube addons enable metrics-server
minikube addons enable ingress
minikube addons enable storage-provisioner
echo -e "${GREEN}✓ Addons enabled${NC}"
echo ""

# Install Prometheus & Grafana (if helm available)
echo "Step 4: Installing monitoring stack..."
if command -v helm &> /dev/null; then
    # Add repos
    helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
    helm repo update

    # Install kube-prometheus-stack
    kubectl create namespace monitoring --dry-run=client -o yaml | kubectl apply -f -

    if helm list -n monitoring | grep -q kube-prometheus-stack; then
        echo -e "${YELLOW}Prometheus stack already installed${NC}"
    else
        echo "Installing kube-prometheus-stack (this may take a few minutes)..."
        helm install kube-prometheus-stack prometheus-community/kube-prometheus-stack \
            -n monitoring \
            --set prometheus.prometheusSpec.serviceMonitorSelectorNilUsesHelmValues=false \
            --set prometheus.prometheusSpec.podMonitorSelectorNilUsesHelmValues=false \
            --set grafana.adminPassword=admin
    fi

    echo -e "${GREEN}✓ Monitoring stack installed${NC}"
else
    echo -e "${YELLOW}Skipping monitoring stack (helm not available)${NC}"
fi
echo ""

# Deploy local storage services
echo "Step 5: Deploying local storage services..."
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# PostgreSQL
echo "  - PostgreSQL (for MLflow + Feast registry)..."
kubectl apply -f "$SCRIPT_DIR/../infrastructure/minikube/postgresql.yaml"

# Redis
echo "  - Redis (for Feast online store)..."
kubectl apply -f "$SCRIPT_DIR/../infrastructure/minikube/redis.yaml"

# MinIO (S3 replacement)
echo "  - MinIO (S3-compatible storage)..."
kubectl apply -f "$SCRIPT_DIR/../infrastructure/minikube/minio.yaml"

echo -e "${GREEN}✓ Storage services deployed${NC}"
echo ""

# Wait for storage services
echo "Step 6: Waiting for storage services to be ready..."
kubectl wait --for=condition=ready pod -l app=postgresql -n storage --timeout=300s
kubectl wait --for=condition=ready pod -l app=redis -n storage --timeout=300s
kubectl wait --for=condition=ready pod -l app=minio -n storage --timeout=300s
echo -e "${GREEN}✓ Storage services ready${NC}"
echo ""

# Deploy MLflow
echo "Step 7: Deploying MLflow tracking server..."
kubectl apply -f "$SCRIPT_DIR/../infrastructure/minikube/mlflow.yaml"
kubectl wait --for=condition=ready pod -l app=mlflow -n mlflow --timeout=300s
echo -e "${GREEN}✓ MLflow deployed${NC}"
echo ""

# Deploy Feast
echo "Step 8: Deploying Feast feature store..."
kubectl apply -f "$SCRIPT_DIR/../infrastructure/minikube/feast.yaml"
kubectl wait --for=condition=ready pod -l app=feast -n feast --timeout=300s
echo -e "${GREEN}✓ Feast deployed${NC}"
echo ""

# Deploy Airflow
echo "Step 9: Deploying Airflow orchestration..."
kubectl apply -f "$SCRIPT_DIR/../infrastructure/minikube/airflow.yaml"
echo "  Waiting for PostgreSQL to be ready..."
kubectl wait --for=condition=ready pod -l app=airflow-postgresql -n airflow --timeout=300s
echo "  Waiting for Airflow to be ready (this may take 2-3 minutes)..."
kubectl wait --for=condition=ready pod -l app=airflow -n airflow --timeout=600s
echo -e "${GREEN}✓ Airflow deployed${NC}"
echo ""

# Copy DAGs to Airflow
echo "Step 10: Deploying Airflow DAGs..."
AIRFLOW_POD=$(kubectl get pod -n airflow -l app=airflow -o jsonpath='{.items[0].metadata.name}')
if [ -d "$SCRIPT_DIR/../mlops/airflow/dags" ]; then
    echo "  Copying DAGs to Airflow pod..."
    kubectl cp "$SCRIPT_DIR/../mlops/airflow/dags/." "airflow/$AIRFLOW_POD:/opt/airflow/dags/" || echo "  Note: DAGs will be loaded on first access"
    echo -e "${GREEN}✓ DAGs deployed${NC}"
else
    echo -e "${YELLOW}  Warning: DAGs directory not found${NC}"
fi
echo ""

# Deploy monitoring configuration
echo "Step 11: Deploying monitoring configuration..."
kubectl apply -f "$SCRIPT_DIR/../infrastructure/monitoring/prometheus/servicemonitors.yaml" || echo "ServiceMonitors require Prometheus Operator"
kubectl apply -f "$SCRIPT_DIR/../infrastructure/monitoring/prometheus/alerts.yaml" || echo "Alerts require Prometheus Operator"
kubectl apply -f "$SCRIPT_DIR/../infrastructure/monitoring/grafana-dashboards-configmap.yaml" || true
echo -e "${GREEN}✓ Monitoring configured${NC}"
echo ""

# Get access URLs
echo "========================================="
echo "Deployment Complete!"
echo "========================================="
echo ""
echo -e "${BLUE}Access URLs (run in separate terminals):${NC}"
echo ""

echo "1. MLflow Tracking Server:"
echo "   kubectl port-forward -n mlflow svc/mlflow-service 5000:80"
echo "   → http://localhost:5000"
echo ""

echo "2. Feast Feature Server:"
echo "   kubectl port-forward -n feast svc/feast-feature-server 6566:80"
echo "   → http://localhost:6566"
echo ""

echo "3. MinIO Console (S3):"
echo "   kubectl port-forward -n storage svc/minio 9001:9001"
echo "   → http://localhost:9001 (admin/minioadmin)"
echo ""

echo "4. PostgreSQL:"
echo "   kubectl port-forward -n storage svc/postgresql 5432:5432"
echo "   → localhost:5432 (user: maestro, password: maestro123)"
echo ""

echo "5. Redis:"
echo "   kubectl port-forward -n storage svc/redis 6379:6379"
echo "   → localhost:6379"
echo ""

echo "6. Airflow Webserver:"
echo "   kubectl port-forward -n airflow svc/airflow-webserver 8080:80"
echo "   → http://localhost:8080 (admin/admin)"
echo ""

fi

echo -e "${BLUE}Quick commands:${NC}"
echo ""
echo "View all pods:"
echo "  kubectl get pods --all-namespaces"
echo ""
echo "View logs:"
echo "  kubectl logs -n mlflow -l app=mlflow -f"
echo "  kubectl logs -n feast -l app=feast -f"
echo ""
echo "Run validation tests:"
echo "  ./scripts/validate-minikube.sh"
echo ""
echo "Stop minikube:"
echo "  minikube stop"
echo ""
echo "Delete minikube:"
echo "  minikube delete"
echo ""

# Save minikube IP for reference
MINIKUBE_IP=$(minikube ip)
echo -e "${GREEN}Minikube IP: $MINIKUBE_IP${NC}"
echo ""

echo "========================================="
echo -e "${GREEN}✓ Minikube test environment ready!${NC}"
echo "========================================="

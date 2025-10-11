#!/bin/bash
# Maestro ML Platform - Monitoring Deployment Script
# Phase 1.1.9 - Deploy Prometheus and Grafana monitoring

set -e

echo "========================================="
echo "ML Platform Monitoring Deployment"
echo "========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check prerequisites
echo "Checking prerequisites..."
if ! command_exists kubectl; then
    echo -e "${RED}ERROR: kubectl is not installed${NC}"
    exit 1
fi

if ! command_exists helm; then
    echo -e "${YELLOW}WARNING: helm is not installed (optional)${NC}"
fi

# Check cluster connectivity
if ! kubectl cluster-info >/dev/null 2>&1; then
    echo -e "${RED}ERROR: Cannot connect to Kubernetes cluster${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Prerequisites satisfied${NC}"
echo ""

# Navigate to infrastructure directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
INFRA_DIR="$SCRIPT_DIR/../infrastructure"

# Step 1: Create ml-monitoring namespace
echo "Step 1: Creating ml-monitoring namespace..."
kubectl create namespace ml-monitoring --dry-run=client -o yaml | kubectl apply -f -
echo -e "${GREEN}✓ Namespace created/verified${NC}"
echo ""

# Step 2: Deploy Prometheus ServiceMonitors
echo "Step 2: Deploying Prometheus ServiceMonitors..."
kubectl apply -f "$INFRA_DIR/monitoring/prometheus/servicemonitors.yaml"
echo -e "${GREEN}✓ ServiceMonitors deployed${NC}"
echo ""

# Step 3: Deploy Prometheus Alerts
echo "Step 3: Deploying Prometheus alerting rules..."
kubectl apply -f "$INFRA_DIR/monitoring/prometheus/alerts.yaml"
echo -e "${GREEN}✓ Alerting rules deployed${NC}"
echo ""

# Step 4: Deploy Grafana Dashboards ConfigMap
echo "Step 4: Deploying Grafana dashboards..."
kubectl apply -f "$INFRA_DIR/monitoring/grafana-dashboards-configmap.yaml"
echo -e "${GREEN}✓ Grafana dashboards deployed${NC}"
echo ""

# Step 5: Verify deployments
echo "Step 5: Verifying deployments..."
echo ""

echo "ServiceMonitors:"
kubectl get servicemonitor -n ml-monitoring
echo ""

echo "PrometheusRules:"
kubectl get prometheusrule -n ml-monitoring
echo ""

echo "ConfigMaps:"
kubectl get configmap -n monitoring -l grafana_dashboard=1
echo ""

# Step 6: Check Prometheus targets (if accessible)
echo "Step 6: Checking Prometheus configuration..."
echo ""
echo "To verify Prometheus is scraping targets:"
echo "1. Port-forward Prometheus: kubectl port-forward -n monitoring svc/prometheus-operated 9090:9090"
echo "2. Visit http://localhost:9090/targets"
echo "3. Verify all ML platform targets are UP"
echo ""

# Step 7: Access Grafana dashboards
echo "Step 7: Accessing Grafana dashboards..."
echo ""
echo "To access Grafana:"
echo "1. Port-forward Grafana: kubectl port-forward -n monitoring svc/grafana 3000:80"
echo "2. Visit http://localhost:3000"
echo "3. Navigate to Dashboards → ML Platform folder"
echo ""

# Optional: Deploy DCGM exporter for GPU monitoring
echo "========================================="
echo "Optional: NVIDIA GPU Monitoring"
echo "========================================="
echo ""
echo "To enable GPU metrics (if not already deployed):"
echo ""
echo "1. Install NVIDIA GPU Operator:"
echo "   helm repo add nvidia https://helm.ngc.nvidia.com/nvidia"
echo "   helm install gpu-operator nvidia/gpu-operator -n gpu-operator --create-namespace"
echo ""
echo "2. Verify DCGM exporter is running:"
echo "   kubectl get pods -n gpu-operator -l app=nvidia-dcgm-exporter"
echo ""

# Summary
echo "========================================="
echo "Deployment Summary"
echo "========================================="
echo ""
echo -e "${GREEN}✓ Monitoring configuration deployed successfully!${NC}"
echo ""
echo "Deployed components:"
echo "  • 10 ServiceMonitors + 2 PodMonitors"
echo "  • 50+ Prometheus alerting rules"
echo "  • 2 Grafana dashboards (ML Platform Overview, GPU Monitoring)"
echo ""
echo "Next steps:"
echo "1. Verify Prometheus is scraping all targets"
echo "2. Import Grafana dashboards via UI (if not auto-loaded)"
echo "3. Configure alert notification channels in Prometheus/Alertmanager"
echo "4. Review and adjust alert thresholds as needed"
echo ""
echo "For troubleshooting, see:"
echo "  $INFRA_DIR/monitoring/grafana-dashboards-configmap.yaml (README section)"
echo ""

#!/bin/bash
# Run Phase 1 Infrastructure Tests
# Usage: ./run_phase1_tests.sh [test-type]
# test-type: smoke, integration, e2e, all (default: smoke)

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
TEST_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$TEST_DIR")"
TEST_TYPE="${1:-smoke}"

echo "====================================================================="
echo "  ML Platform Phase 1 Test Suite"
echo "====================================================================="
echo "Test Directory: $TEST_DIR"
echo "Test Type: $TEST_TYPE"
echo "====================================================================="
echo ""

# Check prerequisites
echo "Checking prerequisites..."

# Check minikube
if ! command -v minikube &> /dev/null; then
    echo -e "${RED}✗ minikube not found${NC}"
    exit 1
fi

# Check if minikube is running
if ! minikube status &> /dev/null; then
    echo -e "${YELLOW}⚠ minikube is not running${NC}"
    echo "Starting minikube..."
    minikube start
fi

# Get minikube IP
MINIKUBE_IP=$(minikube ip)
echo -e "${GREEN}✓ Minikube running at $MINIKUBE_IP${NC}"

# Check kubectl
if ! command -v kubectl &> /dev/null; then
    echo -e "${RED}✗ kubectl not found${NC}"
    exit 1
fi
echo -e "${GREEN}✓ kubectl found${NC}"

# Check Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}✗ python3 not found${NC}"
    exit 1
fi
echo -e "${GREEN}✓ python3 found${NC}"

# Install test dependencies
echo ""
echo "Installing test dependencies..."
pip install -q pytest requests || {
    echo -e "${RED}✗ Failed to install dependencies${NC}"
    exit 1
}
echo -e "${GREEN}✓ Dependencies installed${NC}"

# Export environment variables
export MINIKUBE_IP="$MINIKUBE_IP"
export MLFLOW_TRACKING_URI="http://$MINIKUBE_IP:30500"
export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"

echo ""
echo "Environment:"
echo "  MINIKUBE_IP=$MINIKUBE_IP"
echo "  MLFLOW_TRACKING_URI=$MLFLOW_TRACKING_URI"
echo ""

# Run tests based on type
cd "$TEST_DIR"

case "$TEST_TYPE" in
  smoke)
    echo "====================================================================="
    echo "  Running Smoke Tests (Quick Health Checks)"
    echo "====================================================================="
    pytest integration/test_phase1_smoke.py -v -m smoke --html=reports/smoke_test_report.html --self-contained-html
    ;;

  integration)
    echo "====================================================================="
    echo "  Running Integration Tests"
    echo "====================================================================="
    pytest integration/ -v -m integration --html=reports/integration_test_report.html --self-contained-html
    ;;

  e2e)
    echo "====================================================================="
    echo "  Running End-to-End Tests"
    echo "====================================================================="
    pytest integration/ -v -m e2e --html=reports/e2e_test_report.html --self-contained-html
    ;;

  all)
    echo "====================================================================="
    echo "  Running All Tests"
    echo "====================================================================="
    pytest integration/ -v --html=reports/full_test_report.html --self-contained-html
    ;;

  *)
    echo -e "${RED}Unknown test type: $TEST_TYPE${NC}"
    echo "Usage: $0 [smoke|integration|e2e|all]"
    exit 1
    ;;
esac

# Test results
TEST_EXIT_CODE=$?

echo ""
echo "====================================================================="
if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}✓ All tests passed!${NC}"
else
    echo -e "${RED}✗ Some tests failed (exit code: $TEST_EXIT_CODE)${NC}"
fi
echo "====================================================================="
echo ""
echo "Test report: $TEST_DIR/reports/${TEST_TYPE}_test_report.html"
echo ""

# Service URLs
echo "====================================================================="
echo "  Service URLs (Minikube)"
echo "====================================================================="
echo "MLflow:          http://$MINIKUBE_IP:30500"
echo "Feast:           http://$MINIKUBE_IP:30501"
echo "Airflow:         http://$MINIKUBE_IP:30502"
echo "Prometheus:      http://$MINIKUBE_IP:30503"
echo "Grafana:         http://$MINIKUBE_IP:30504"
echo "MinIO Console:   http://$MINIKUBE_IP:30505"
echo "Registry:        http://$MINIKUBE_IP:30506"
echo "Registry UI:     http://$MINIKUBE_IP:30507"
echo "Loki:            http://$MINIKUBE_IP:30508"
echo "====================================================================="

exit $TEST_EXIT_CODE

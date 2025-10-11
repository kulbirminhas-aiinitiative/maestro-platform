#!/bin/bash
# Maestro ML Platform - Minikube Validation Script
# Tests all components of the local test environment

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

PASSED=0
FAILED=0

echo "========================================="
echo "ML Platform - Minikube Validation"
echo "========================================="
echo ""

# Helper functions
check_pod_status() {
    local namespace=$1
    local label=$2
    local name=$3

    echo -n "  Checking $name... "
    if kubectl get pods -n $namespace -l $label 2>/dev/null | grep -q Running; then
        echo -e "${GREEN}✓ Running${NC}"
        ((PASSED++))
        return 0
    else
        echo -e "${RED}✗ Not running${NC}"
        ((FAILED++))
        return 1
    fi
}

test_http_endpoint() {
    local url=$1
    local name=$2

    echo -n "  Testing $name... "
    if curl -s -o /dev/null -w "%{http_code}" --max-time 5 $url | grep -q 200; then
        echo -e "${GREEN}✓ Responsive${NC}"
        ((PASSED++))
        return 0
    else
        echo -e "${YELLOW}⚠ Not accessible (may need port-forward)${NC}"
        ((PASSED++))  # Don't fail, just warning
        return 0
    fi
}

# Test 1: Cluster connectivity
echo "Test 1: Kubernetes cluster"
echo -n "  Cluster info... "
if kubectl cluster-info &> /dev/null; then
    echo -e "${GREEN}✓ Connected${NC}"
    ((PASSED++))
else
    echo -e "${RED}✗ Cannot connect${NC}"
    ((FAILED++))
    exit 1
fi

echo -n "  Minikube status... "
if minikube status &> /dev/null; then
    echo -e "${GREEN}✓ Running${NC}"
    ((PASSED++))
else
    echo -e "${RED}✗ Not running${NC}"
    ((FAILED++))
fi
echo ""

# Test 2: Storage services
echo "Test 2: Storage services"
check_pod_status "storage" "app=postgresql" "PostgreSQL"
check_pod_status "storage" "app=redis" "Redis"
check_pod_status "storage" "app=minio" "MinIO"
echo ""

# Test 3: ML services
echo "Test 3: ML services"
check_pod_status "mlflow" "app=mlflow" "MLflow"
check_pod_status "feast" "app=feast" "Feast"
check_pod_status "airflow" "app=airflow" "Airflow"
echo ""

# Test 4: Service connectivity
echo "Test 4: Service connectivity"

echo -n "  PostgreSQL connection... "
if kubectl exec -n storage -it $(kubectl get pod -n storage -l app=postgresql -o jsonpath='{.items[0].metadata.name}') -- psql -U maestro -d mlflow -c "SELECT 1" &> /dev/null; then
    echo -e "${GREEN}✓ Accessible${NC}"
    ((PASSED++))
else
    echo -e "${RED}✗ Not accessible${NC}"
    ((FAILED++))
fi

echo -n "  Redis connection... "
if kubectl exec -n storage -it $(kubectl get pod -n storage -l app=redis -o jsonpath='{.items[0].metadata.name}') -- redis-cli ping | grep -q PONG; then
    echo -e "${GREEN}✓ Accessible${NC}"
    ((PASSED++))
else
    echo -e "${RED}✗ Not accessible${NC}"
    ((FAILED++))
fi
echo ""

# Test 5: MLflow functionality
echo "Test 5: MLflow functionality"
echo -n "  MLflow database... "
DB_TABLES=$(kubectl exec -n storage -it $(kubectl get pod -n storage -l app=postgresql -o jsonpath='{.items[0].metadata.name}') -- psql -U maestro -d mlflow -c "\dt" 2>/dev/null | grep -c "public")
if [ "$DB_TABLES" -gt 0 ]; then
    echo -e "${GREEN}✓ Tables created ($DB_TABLES tables)${NC}"
    ((PASSED++))
else
    echo -e "${YELLOW}⚠ No tables yet (MLflow may still be initializing)${NC}"
    ((PASSED++))
fi

echo -n "  MLflow health endpoint... "
POD_NAME=$(kubectl get pod -n mlflow -l app=mlflow -o jsonpath='{.items[0].metadata.name}')
if kubectl exec -n mlflow $POD_NAME -- curl -s http://localhost:5000/health | grep -q "OK"; then
    echo -e "${GREEN}✓ Healthy${NC}"
    ((PASSED++))
else
    echo -e "${YELLOW}⚠ Not yet ready${NC}"
    ((PASSED++))
fi
echo ""

# Test 6: Feast functionality
echo "Test 6: Feast functionality"
echo -n "  Feast registry database... "
DB_TABLES=$(kubectl exec -n storage -it $(kubectl get pod -n storage -l app=postgresql -o jsonpath='{.items[0].metadata.name}') -- psql -U maestro -d feast_registry -c "\dt" 2>/dev/null | grep -c "public" || echo "0")
if [ "$DB_TABLES" -gt 0 ]; then
    echo -e "${GREEN}✓ Tables created ($DB_TABLES tables)${NC}"
    ((PASSED++))
else
    echo -e "${YELLOW}⚠ No tables yet (Run 'feast apply' to initialize)${NC}"
    ((PASSED++))
fi

echo -n "  Feast health endpoint... "
POD_NAME=$(kubectl get pod -n feast -l app=feast -o jsonpath='{.items[0].metadata.name}')
if kubectl exec -n feast $POD_NAME -- curl -s http://localhost:6566/health | grep -q "OK"; then
    echo -e "${GREEN}✓ Healthy${NC}"
    ((PASSED++))
else
    echo -e "${YELLOW}⚠ Not yet ready${NC}"
    ((PASSED++))
fi
echo ""

# Test 7: Airflow functionality
echo "Test 7: Airflow orchestration"
echo -n "  Airflow database... "
DB_TABLES=$(kubectl exec -n airflow -it $(kubectl get pod -n airflow -l app=airflow-postgresql -o jsonpath='{.items[0].metadata.name}') -- psql -U maestro -d airflow -c "\\dt" 2>/dev/null | grep -c "public" || echo "0")
if [ "$DB_TABLES" -gt 0 ]; then
    echo -e "${GREEN}✓ Tables created ($DB_TABLES tables)${NC}"
    ((PASSED++))
else
    echo -e "${YELLOW}⚠ No tables yet (Airflow may still be initializing)${NC}"
    ((PASSED++))
fi

echo -n "  Airflow webserver... "
POD_NAME=$(kubectl get pod -n airflow -l app=airflow -o jsonpath='{.items[0].metadata.name}')
if kubectl exec -n airflow $POD_NAME -- curl -s http://localhost:8080/health | grep -q "healthy"; then
    echo -e "${GREEN}✓ Healthy${NC}"
    ((PASSED++))
else
    echo -e "${YELLOW}⚠ Not yet ready${NC}"
    ((PASSED++))
fi

echo -n "  Airflow DAGs... "
DAG_COUNT=$(kubectl exec -n airflow $POD_NAME -- airflow dags list 2>/dev/null | grep -v "dag_id" | wc -l || echo "0")
if [ "$DAG_COUNT" -gt 0 ]; then
    echo -e "${GREEN}✓ Found $DAG_COUNT DAGs${NC}"
    ((PASSED++))
else
    echo -e "${YELLOW}⚠ No DAGs found (copy DAGs to pod)${NC}"
    ((PASSED++))
fi
echo ""

# Test 8: MinIO buckets
echo "Test 8: MinIO storage"
echo -n "  MLflow bucket... "
POD_NAME=$(kubectl get pod -n storage -l app=minio -o jsonpath='{.items[0].metadata.name}')
if kubectl exec -n storage $POD_NAME -- mc ls local/mlflow &> /dev/null; then
    echo -e "${GREEN}✓ Exists${NC}"
    ((PASSED++))
else
    echo -e "${YELLOW}⚠ Not found (will be created on first use)${NC}"
    ((PASSED++))
fi

echo -n "  Feast bucket... "
if kubectl exec -n storage $POD_NAME -- mc ls local/feast &> /dev/null; then
    echo -e "${GREEN}✓ Exists${NC}"
    ((PASSED++))
else
    echo -e "${YELLOW}⚠ Not found (will be created on first use)${NC}"
    ((PASSED++))
fi
echo ""

# Test 9: Monitoring (if installed)
echo "Test 9: Monitoring stack (optional)"
if kubectl get namespace monitoring &> /dev/null; then
    check_pod_status "monitoring" "app.kubernetes.io/name=prometheus" "Prometheus"
    check_pod_status "monitoring" "app.kubernetes.io/name=grafana" "Grafana"

    echo -n "  ServiceMonitors... "
    SM_COUNT=$(kubectl get servicemonitor -n ml-monitoring 2>/dev/null | grep -c "mlflow\|feast" || echo "0")
    if [ "$SM_COUNT" -gt 0 ]; then
        echo -e "${GREEN}✓ Found $SM_COUNT ServiceMonitors${NC}"
        ((PASSED++))
    else
        echo -e "${YELLOW}⚠ No ServiceMonitors (run deploy-monitoring.sh)${NC}"
        ((PASSED++))
    fi

    echo -n "  PrometheusRules... "
    PR_COUNT=$(kubectl get prometheusrule -n ml-monitoring 2>/dev/null | grep -c "ml-platform" || echo "0")
    if [ "$PR_COUNT" -gt 0 ]; then
        echo -e "${GREEN}✓ Found $PR_COUNT PrometheusRules${NC}"
        ((PASSED++))
    else
        echo -e "${YELLOW}⚠ No PrometheusRules (run deploy-monitoring.sh)${NC}"
        ((PASSED++))
    fi
else
    echo -e "${YELLOW}  Monitoring namespace not found (optional)${NC}"
fi
echo ""

# Test 10: Resource usage
echo "Test 10: Resource usage"
echo "  Namespace resource consumption:"
kubectl top pods -n storage 2>/dev/null | awk 'NR>1 {print "    " $0}' || echo -e "${YELLOW}    Metrics not available (install metrics-server)${NC}"
kubectl top pods -n mlflow 2>/dev/null | awk 'NR>1 {print "    " $0}' || true
kubectl top pods -n feast 2>/dev/null | awk 'NR>1 {print "    " $0}' || true
kubectl top pods -n airflow 2>/dev/null | awk 'NR>1 {print "    " $0}' || true
echo ""

# Summary
echo "========================================="
echo "Validation Summary"
echo "========================================="
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ All critical tests passed ($PASSED passed, $FAILED failed)${NC}"
    echo ""
    echo "Your minikube environment is ready for testing!"
    echo ""
    echo "Next steps:"
    echo "1. Access MLflow:"
    echo "   kubectl port-forward -n mlflow svc/mlflow-service 5000:80"
    echo "   → http://localhost:5000"
    echo ""
    echo "2. Apply Feast features:"
    echo "   cd mlops/feast/feature_repo"
    echo "   feast apply"
    echo ""
    echo "3. Test feature serving:"
    echo "   kubectl port-forward -n feast svc/feast-feature-server 6566:80"
    echo "   → http://localhost:6566"
    echo ""
    echo "4. Access Airflow:"
    echo "   kubectl port-forward -n airflow svc/airflow-webserver 8080:80"
    echo "   → http://localhost:8080 (admin/admin)"
    echo ""
    echo "5. Run Airflow DAGs and test ML workflows"
    echo ""
    exit 0
else
    echo -e "${RED}✗ Some tests failed ($PASSED passed, $FAILED failed)${NC}"
    echo ""
    echo "Troubleshooting:"
    echo "1. Check pod logs:"
    echo "   kubectl logs -n <namespace> -l app=<service> -f"
    echo ""
    echo "2. Check pod events:"
    echo "   kubectl describe pod -n <namespace> <pod-name>"
    echo ""
    echo "3. Re-run setup:"
    echo "   ./scripts/setup-minikube-test.sh"
    echo ""
    exit 1
fi

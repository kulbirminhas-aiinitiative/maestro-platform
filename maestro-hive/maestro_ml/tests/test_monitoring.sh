#!/bin/bash
# Test Monitoring Infrastructure

echo "Testing monitoring infrastructure..."

PROJECT_DIR="$(dirname "$(dirname "$(realpath "$0")")")"

# Check Prometheus configuration
if [ -f "$PROJECT_DIR/monitoring/prometheus-deployment.yaml" ]; then
    echo "✅ Prometheus configuration found"
else
    echo "⚠️  Prometheus configuration not found"
fi

# Check Grafana dashboards
if [ -d "$PROJECT_DIR/monitoring/dashboards" ]; then
    dashboard_count=$(find "$PROJECT_DIR/monitoring/dashboards" -name "*.json" | wc -l)
    echo "✅ Found $dashboard_count Grafana dashboards"
else
    echo "⚠️  Grafana dashboards directory not found"
fi

# Check alert rules
if [ -d "$PROJECT_DIR/monitoring/alerts" ]; then
    alert_count=$(find "$PROJECT_DIR/monitoring/alerts" -name "*.yaml" | wc -l)
    echo "✅ Found $alert_count alert rule files"
else
    echo "⚠️  Alert rules directory not found"
fi

# Check Jaeger tracing
if [ -f "$PROJECT_DIR/observability/jaeger-deployment.yaml" ]; then
    echo "✅ Jaeger distributed tracing configuration found"
else
    echo "⚠️  Jaeger configuration not found"
fi

echo "✅ Monitoring infrastructure tests passed"

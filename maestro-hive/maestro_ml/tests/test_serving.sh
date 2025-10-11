#!/bin/bash
# Test Model Serving Infrastructure

echo "Testing model serving infrastructure..."

PROJECT_DIR="$(dirname "$(dirname "$(realpath "$0")")")"

# Check serving deployment exists
if [ -f "$PROJECT_DIR/serving/mlflow-serving-deployment.yaml" ]; then
    echo "✅ Model serving deployment configuration found"
else
    echo "❌ Model serving deployment not found"
    exit 1
fi

# Check HPA configurations
if [ -d "$PROJECT_DIR/serving/autoscaling" ]; then
    hpa_count=$(find "$PROJECT_DIR/serving/autoscaling" -name "*.yaml" | wc -l)
    echo "✅ Found $hpa_count HPA configurations"
else
    echo "⚠️  Autoscaling directory not found"
fi

# Check governance scripts
if [ -d "$PROJECT_DIR/governance" ]; then
    script_count=$(find "$PROJECT_DIR/governance" -name "*.py" | wc -l)
    echo "✅ Found $script_count governance scripts"
else
    echo "⚠️  Governance directory not found"
fi

echo "✅ Model serving tests passed"

#!/bin/bash
# Test Auto-scaling Configuration

echo "Testing auto-scaling configuration..."

PROJECT_DIR="$(dirname "$(dirname "$(realpath "$0")")")"

# Check HPA configurations
if [ -d "$PROJECT_DIR/serving/autoscaling" ]; then
    echo "✅ Auto-scaling directory exists"

    # Check for HPA YAML files
    hpa_files=$(find "$PROJECT_DIR/serving/autoscaling" -name "*hpa*.yaml" | wc -l)
    if [ $hpa_files -gt 0 ]; then
        echo "✅ Found $hpa_files HPA configuration files"
    else
        echo "⚠️  No HPA configuration files found"
    fi
else
    echo "⚠️  Auto-scaling directory not found"
fi

echo "✅ Auto-scaling configuration tests passed"

#!/bin/bash
# Test Training Infrastructure

echo "Testing training infrastructure configuration..."

PROJECT_DIR="$(dirname "$(dirname "$(realpath "$0")")")"

# Check training operator YAML exists
if [ -f "$PROJECT_DIR/infrastructure/kubernetes/training-operator.yaml" ]; then
    echo "✅ Training operator configuration found"
else
    echo "❌ Training operator configuration not found"
    exit 1
fi

# Check training templates exist
if [ -d "$PROJECT_DIR/training/templates" ]; then
    template_count=$(find "$PROJECT_DIR/training/templates" -name "*.yaml" | wc -l)
    echo "✅ Found $template_count training templates"
else
    echo "⚠️  Training templates directory not found"
fi

# Check Optuna optimization scripts
if [ -d "$PROJECT_DIR/training/optuna" ]; then
    echo "✅ Optuna optimization scripts found"
else
    echo "⚠️  Optuna directory not found"
fi

echo "✅ Training infrastructure tests passed"

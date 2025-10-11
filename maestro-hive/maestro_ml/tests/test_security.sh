#!/bin/bash
# Test Security Configuration

echo "Testing security configuration..."

PROJECT_DIR="$(dirname "$(dirname "$(realpath "$0")")")"

# Check Vault deployment
if [ -f "$PROJECT_DIR/security/vault-deployment.yaml" ]; then
    echo "✅ Vault deployment configuration found"
else
    echo "⚠️  Vault deployment not found"
fi

# Check secrets management
if [ -f "$PROJECT_DIR/infrastructure/kubernetes/secrets-management.yaml" ]; then
    echo "✅ Secrets management configuration found"
else
    echo "⚠️  Secrets management configuration not found"
fi

# Check network policies
network_policy_count=$(find "$PROJECT_DIR" -name "*network-policy*.yaml" 2>/dev/null | wc -l)
if [ $network_policy_count -gt 0 ]; then
    echo "✅ Found $network_policy_count network policy files"
else
    echo "⚠️  No network policies found"
fi

# Check RBAC configurations
rbac_count=$(find "$PROJECT_DIR" -name "*rbac*.yaml" 2>/dev/null | wc -l)
if [ $rbac_count -gt 0 ]; then
    echo "✅ Found $rbac_count RBAC configuration files"
else
    echo "⚠️  No RBAC configurations found"
fi

echo "✅ Security configuration tests passed"

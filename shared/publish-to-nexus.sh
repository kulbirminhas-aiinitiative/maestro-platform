#!/bin/bash
# Publish maestro shared packages to Nexus OSS
# Migrated from pypiserver to Nexus

set -e

# Nexus OSS uses port 8081 for all repositories (not 8083)
NEXUS_URL="http://localhost:28081/repository/pypi-hosted/"
NEXUS_USER="${NEXUS_USER:-admin}"
# Try to get password from env, temp file, or container
NEXUS_PASS="${NEXUS_ADMIN_PASSWORD:-nexus_admin_2025_change_me}"

# Check if deployer user credentials are provided (recommended for CI/CD)
if [ -n "${NEXUS_DEPLOY_USER}" ]; then
    NEXUS_USER="${NEXUS_DEPLOY_USER}"
    NEXUS_PASS="${NEXUS_DEPLOY_PASSWORD}"
fi

# Packages needed by quality-fabric (core shared libraries)
PACKAGES=(
    "core-logging"
    "core-config"
    "monitoring"
    "core-db"
    "core-api"
    "core-auth"
)

echo "=================================================="
echo "Publishing Maestro Shared Packages to Nexus OSS"
echo "=================================================="
echo "Target: $NEXUS_URL"
echo "User: $NEXUS_USER"
echo ""

# Check if Nexus is accessible
echo "Checking Nexus availability..."
if ! curl -s -f -u "$NEXUS_USER:$NEXUS_PASS" "http://localhost:28081/service/rest/v1/status" > /dev/null 2>&1; then
    echo "❌ ERROR: Cannot connect to Nexus or authentication failed"
    echo ""
    echo "Please complete Nexus setup first:"
    echo "  1. Open http://localhost:28081 in browser"
    echo "  2. Login with admin / nexus_admin_2025_change_me"
    echo "  3. Follow setup guide: /infrastructure/docs/NEXUS_PYPI_SETUP.md"
    echo ""
    echo "Key step: Enable 'npm Bearer Token Realm' in Security → Realms"
    echo ""
    exit 1
fi
echo "✓ Nexus is accessible"
echo ""

# Check if twine is installed
if ! command -v twine &> /dev/null; then
    echo "Installing twine..."
    pip install twine
fi

# Build and publish each package
for package_name in "${PACKAGES[@]}"; do
    package_dir="/home/ec2-user/projects/maestro-platform/shared/packages/$package_name"

    if [ ! -d "$package_dir" ]; then
        echo "⚠️  Package not found: $package_name"
        continue
    fi

    echo "========================================="
    echo "Processing: $package_name"
    echo "========================================="

    cd "$package_dir"

    # Clean old builds
    rm -rf dist/ build/ *.egg-info 2>/dev/null || true

    # Build the package
    echo "Building $package_name..."
    if [ -f "pyproject.toml" ]; then
        # Use poetry if pyproject.toml exists
        if command -v poetry &> /dev/null; then
            poetry build || {
                echo "⚠️  Poetry build failed, falling back to pip..."
                pip install build
                python -m build
            }
        else
            echo "Poetry not found, using pip build..."
            pip install build
            python -m build
        fi
    elif [ -f "setup.py" ]; then
        # Use setup.py
        python setup.py sdist bdist_wheel
    else
        echo "❌ No build configuration found for $package_name"
        continue
    fi

    # Check if dist/ has files
    if [ ! -d "dist" ] || [ -z "$(ls -A dist 2>/dev/null)" ]; then
        echo "❌ No distribution files created for $package_name"
        continue
    fi

    # Upload to Nexus
    echo "Uploading to Nexus..."
    twine upload \
        --repository-url "$NEXUS_URL" \
        --username "$NEXUS_USER" \
        --password "$NEXUS_PASS" \
        --verbose \
        dist/* 2>&1 | tee /tmp/twine-upload.log || {
        # Check if error is due to existing package
        if grep -q "already exists" /tmp/twine-upload.log; then
            echo "⚠️  $package_name already exists in Nexus (skipping)"
        else
            echo "⚠️  Upload failed for $package_name"
            cat /tmp/twine-upload.log
        fi
    }

    echo "✓ $package_name processed"
    echo ""
done

echo "========================================="
echo "✓ Package publishing complete!"
echo "========================================="
echo ""
echo "Packages available at: http://localhost:28081/repository/pypi-group/simple/"
echo ""
echo "To install:"
echo "  pip install --index-url http://localhost:28081/repository/pypi-group/simple --trusted-host localhost <package-name>"
echo ""
echo "Or configure pip globally:"
echo "  cd /home/ec2-user/projects/maestro-platform/infrastructure"
echo "  ./scripts/configure-registries.sh --pip"

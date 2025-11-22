#!/bin/bash
# Publish ONLY the packages needed by quality-fabric

set -e

PYPI_URL="http://localhost:8888"
PYPI_DIR="/home/ec2-user/projects/maestro-platform/pypi-server/packages"

# Packages needed by quality-fabric
PACKAGES=(
    "core-logging"
    "core-config"
    "monitoring"
    "core-db"
    "core-api"
    "core-auth"
)

echo "Building and copying maestro shared packages for quality-fabric..."

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
    poetry build || {
        echo "⚠️  Poetry build failed, trying pip setup..."
        python setup.py sdist bdist_wheel 2>/dev/null || {
            echo "❌ Failed to build $package_name"
            continue
        }
    }

    # Copy to PyPI server directory
    echo "Copying to PyPI server..."
    cp dist/* "$PYPI_DIR/" 2>/dev/null || echo "No dist files to copy"

    echo "✓ $package_name built and copied"
done

echo "========================================="
echo "Packages available at: $PYPI_URL/simple/"
echo "========================================="

# Show what's in the PyPI server
echo "Files in PyPI server:"
ls -lh "$PYPI_DIR/" | tail -20

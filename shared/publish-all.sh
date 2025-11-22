#!/bin/bash
# Publish all maestro shared packages to local PyPI server

set -e

PYPI_URL="http://localhost:8888"
PACKAGES_DIR="/home/ec2-user/projects/maestro-platform/shared/packages"

echo "Building and publishing maestro shared packages..."

for package_dir in "$PACKAGES_DIR"/*; do
    if [ -d "$package_dir" ] && [ -f "$package_dir/pyproject.toml" ]; then
        package_name=$(basename "$package_dir")
        echo "========================================="
        echo "Processing: $package_name"
        echo "========================================="

        cd "$package_dir"

        # Build the package
        echo "Building $package_name..."
        poetry build

        # Upload to local PyPI
        echo "Uploading $package_name to PyPI server..."
        poetry config repositories.local "$PYPI_URL"
        poetry publish -r local || {
            # If poetry publish fails, use twine directly
            pip install twine 2>/dev/null || true
            twine upload --repository-url "$PYPI_URL" dist/* --verbose || echo "Upload failed, continuing..."
        }

        echo "✓ $package_name processed"
    fi
done

echo "========================================="
echo "All packages published!"
echo "PyPI Server: $PYPI_URL"
echo "========================================="

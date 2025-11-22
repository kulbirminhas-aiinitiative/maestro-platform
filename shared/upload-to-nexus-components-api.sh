#!/bin/bash
# Upload maestro packages to Nexus using Components API
# This method works when twine fails with 401

set -e

NEXUS_URL="http://localhost:28081"
NEXUS_USER="admin"
NEXUS_PASS='DJ6J&hGH!B#u*J'

PACKAGES=(
    "core-logging"
    "core-config"
    "monitoring"
    "core-db"
    "core-api"
    "core-auth"
)

echo "=================================================="
echo "Uploading Maestro Packages via Components API"
echo "=================================================="
echo ""

UPLOAD_COUNT=0
SKIP_COUNT=0

for package_name in "${PACKAGES[@]}"; do
    package_dir="/home/ec2-user/projects/maestro-platform/shared/packages/$package_name"

    if [ ! -d "$package_dir/dist" ]; then
        echo "⚠️  No dist/ directory for $package_name, skipping"
        continue
    fi

    echo "========================================="
    echo "Uploading: $package_name"
    echo "========================================="

    cd "$package_dir"

    for wheel in dist/*.whl; do
        if [ ! -f "$wheel" ]; then
            continue
        fi

        filename=$(basename "$wheel")
        echo "  Uploading $filename..."

        response=$(curl -s -w "\n%{http_code}" \
            -u "$NEXUS_USER:$NEXUS_PASS" \
            -F "pypi.asset=@$wheel" \
            "$NEXUS_URL/service/rest/v1/components?repository=pypi-hosted")

        http_code=$(echo "$response" | tail -n1)

        if [ "$http_code" = "204" ]; then
            echo "  ✓ Uploaded successfully"
            ((UPLOAD_COUNT++))
        else
            echo "  ⚠️  Upload returned HTTP $http_code"
            if echo "$response" | head -n-1 | grep -q "already exists"; then
                echo "  (Package already exists, skipping)"
                ((SKIP_COUNT++))
            fi
        fi
    done

    echo ""
done

echo "=================================================="
echo "Upload Complete"
echo "=================================================="
echo ""
echo "Uploaded: $UPLOAD_COUNT packages"
echo "Skipped:  $SKIP_COUNT packages (already exist)"
echo ""
echo "Packages are now available at:"
echo "  http://localhost:28081/repository/pypi-group/simple/"
echo ""
echo "Test installation:"
echo "  pip install --index-url http://localhost:28081/repository/pypi-group/simple \\"
echo "              --trusted-host localhost \\"
echo "              maestro-core-logging==1.0.0"
echo ""

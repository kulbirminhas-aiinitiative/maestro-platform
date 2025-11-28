#!/bin/bash
# Nexus OSS - Automated PyPI Repository Setup
# Creates PyPI proxy, hosted, and group repositories

set -e

NEXUS_URL="http://localhost:28081"
NEXUS_USER="admin"

echo "=================================================="
echo "Nexus OSS - PyPI Repository Setup"
echo "=================================================="

# Get initial admin password
if [ -f "/tmp/nexus-admin-password" ]; then
    NEXUS_PASS=$(cat /tmp/nexus-admin-password)
else
    echo "Getting initial admin password from container..."
    NEXUS_PASS=$(docker exec maestro-nexus cat /nexus-data/admin.password 2>/dev/null || echo "admin123")
fi

echo "Nexus URL: $NEXUS_URL"
echo "Username: $NEXUS_USER"
echo "Password: $NEXUS_PASS"
echo ""

# Wait for Nexus to be ready
echo "Waiting for Nexus to be ready..."
for i in {1..30}; do
    if curl -s -f "$NEXUS_URL/service/rest/v1/status" > /dev/null; then
        echo "✓ Nexus is ready"
        break
    fi
    echo "Waiting... ($i/30)"
    sleep 5
done

echo ""
echo "Creating PyPI repositories..."
echo ""

# Function to create repository
create_repo() {
    local repo_type=$1
    local repo_name=$2
    local repo_config=$3

    echo "Creating $repo_name ($repo_type)..."

    response=$(curl -s -w "\n%{http_code}" -X POST "$NEXUS_URL/service/rest/v1/repositories/$repo_type" \
        -u "$NEXUS_USER:$NEXUS_PASS" \
        -H "Content-Type: application/json" \
        -d "$repo_config")

    http_code=$(echo "$response" | tail -n1)

    if [ "$http_code" = "201" ]; then
        echo "  ✓ $repo_name created successfully"
    elif [ "$http_code" = "400" ]; then
        echo "  ⚠️  $repo_name already exists"
    else
        echo "  ❌ Failed to create $repo_name (HTTP $http_code)"
        echo "$response" | head -n-1
    fi
}

# 1. Create PyPI Proxy Repository
create_repo "pypi/proxy" "pypi-proxy" '{
  "name": "pypi-proxy",
  "online": true,
  "storage": {
    "blobStoreName": "default",
    "strictContentTypeValidation": true
  },
  "proxy": {
    "remoteUrl": "https://pypi.org",
    "contentMaxAge": 1440,
    "metadataMaxAge": 1440
  },
  "negativeCache": {
    "enabled": true,
    "timeToLive": 1440
  },
  "httpClient": {
    "blocked": false,
    "autoBlock": true
  }
}'

# 2. Create PyPI Hosted Repository
create_repo "pypi/hosted" "pypi-hosted" '{
  "name": "pypi-hosted",
  "online": true,
  "storage": {
    "blobStoreName": "default",
    "strictContentTypeValidation": true,
    "writePolicy": "ALLOW_ONCE"
  }
}'

# 3. Create PyPI Group Repository
create_repo "pypi/group" "pypi-group" '{
  "name": "pypi-group",
  "online": true,
  "storage": {
    "blobStoreName": "default",
    "strictContentTypeValidation": true
  },
  "group": {
    "memberNames": [
      "pypi-hosted",
      "pypi-proxy"
    ]
  }
}'

echo ""
echo "=================================================="
echo "✓ PyPI repositories setup complete!"
echo "=================================================="
echo ""
echo "Repositories created:"
echo "  - pypi-proxy:  Caches packages from PyPI.org"
echo "  - pypi-hosted: For your internal packages"
echo "  - pypi-group:  Combines both (use this URL)"
echo ""
echo "PyPI Group URL:"
echo "  http://localhost:28083/repository/pypi-group/simple"
echo ""
echo "Configure pip:"
echo "  pip config set global.index-url http://localhost:28083/repository/pypi-group/simple"
echo "  pip config set global.trusted-host localhost"
echo ""
echo "Or use configure-registries.sh:"
echo "  cd /home/ec2-user/projects/maestro-platform/infrastructure"
echo "  ./scripts/configure-registries.sh --pip"
echo ""
echo "Upload packages:"
echo "  twine upload --repository-url http://localhost:28083/repository/pypi-hosted/ dist/*"
echo ""

# Save password for future use
echo "$NEXUS_PASS" > /tmp/nexus-admin-password
chmod 600 /tmp/nexus-admin-password

echo "Nexus admin password saved to: /tmp/nexus-admin-password"
echo ""

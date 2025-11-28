#!/bin/bash
# Configure Nexus authentication for PyPI uploads
# This script properly sets up Nexus for production use

set -e

NEXUS_URL="${NEXUS_URL:-http://localhost:28081}"
INITIAL_ADMIN_PASS=$(cat /tmp/nexus-admin-password 2>/dev/null || docker exec maestro-nexus cat /nexus-data/admin.password 2>/dev/null || echo "")
NEW_ADMIN_PASS="${NEXUS_ADMIN_PASSWORD:-maestro_nexus_admin_2025}"
DEPLOY_USER="${NEXUS_DEPLOY_USER:-deployer}"
DEPLOY_PASS="${NEXUS_DEPLOY_PASSWORD:-deployer_secure_2025}"

echo "=================================================="
echo "Nexus Authentication Configuration"
echo "=================================================="
echo ""

# Check if Nexus is ready
echo "Checking Nexus availability..."
for i in {1..30}; do
    if curl -s -f "$NEXUS_URL/service/rest/v1/status" > /dev/null 2>&1; then
        echo "✓ Nexus is ready"
        break
    fi
    echo "Waiting for Nexus... ($i/30)"
    sleep 5
done

if [ -z "$INITIAL_ADMIN_PASS" ]; then
    echo "ERROR: Could not find initial admin password"
    echo "Please check /nexus-data/admin.password in the container"
    exit 1
fi

echo ""
echo "Initial admin password: $INITIAL_ADMIN_PASS"
echo "New admin password will be: $NEW_ADMIN_PASS"
echo ""

# Step 1: Change admin password
echo "Step 1: Changing admin password..."
change_password_response=$(curl -s -w "\n%{http_code}" -X PUT \
    "$NEXUS_URL/service/rest/v1/security/users/admin/change-password" \
    -u "admin:$INITIAL_ADMIN_PASS" \
    -H "Content-Type: text/plain" \
    -d "$NEW_ADMIN_PASS")

http_code=$(echo "$change_password_response" | tail -n1)

if [ "$http_code" = "204" ] || [ "$http_code" = "200" ]; then
    echo "✓ Admin password changed successfully"
    # Save new password
    echo "$NEW_ADMIN_PASS" > /tmp/nexus-admin-password
    chmod 600 /tmp/nexus-admin-password
    ADMIN_PASS="$NEW_ADMIN_PASS"
elif [ "$http_code" = "403" ]; then
    echo "⚠️  Password already changed, using new password"
    ADMIN_PASS="$NEW_ADMIN_PASS"
else
    echo "❌ Failed to change password (HTTP $http_code)"
    echo "Trying with new password in case it was already changed..."
    ADMIN_PASS="$NEW_ADMIN_PASS"
fi

echo ""
echo "Step 2: Creating deployment user..."

# Create deployment user JSON
deploy_user_json=$(cat <<EOF
{
  "userId": "$DEPLOY_USER",
  "firstName": "Deployment",
  "lastName": "User",
  "emailAddress": "deployer@maestro.local",
  "password": "$DEPLOY_PASS",
  "status": "active",
  "roles": ["nx-admin"]
}
EOF
)

create_user_response=$(curl -s -w "\n%{http_code}" -X POST \
    "$NEXUS_URL/service/rest/v1/security/users" \
    -u "admin:$ADMIN_PASS" \
    -H "Content-Type: application/json" \
    -d "$deploy_user_json")

http_code=$(echo "$create_user_response" | tail -n1)

if [ "$http_code" = "200" ] || [ "$http_code" = "201" ]; then
    echo "✓ Deployment user created successfully"
elif echo "$create_user_response" | grep -q "already exists"; then
    echo "⚠️  Deployment user already exists"
else
    echo "⚠️  User creation response (HTTP $http_code)"
    # Continue anyway, user might already exist
fi

echo ""
echo "Step 3: Verifying authentication..."

# Test with deployment user
test_response=$(curl -s -w "\n%{http_code}" \
    -u "$DEPLOY_USER:$DEPLOY_PASS" \
    "$NEXUS_URL/service/rest/v1/status")

http_code=$(echo "$test_response" | tail -n1)

if [ "$http_code" = "200" ]; then
    echo "✓ Deployment user authentication successful"
else
    echo "❌ Deployment user authentication failed (HTTP $http_code)"
fi

# Test with admin user
test_response=$(curl -s -w "\n%{http_code}" \
    -u "admin:$ADMIN_PASS" \
    "$NEXUS_URL/service/rest/v1/status")

http_code=$(echo "$test_response" | tail -n1)

if [ "$http_code" = "200" ]; then
    echo "✓ Admin authentication successful"
else
    echo "❌ Admin authentication failed (HTTP $http_code)"
fi

echo ""
echo "=================================================="
echo "✓ Nexus authentication configured!"
echo "=================================================="
echo ""
echo "Credentials:"
echo "  Admin:"
echo "    Username: admin"
echo "    Password: $NEW_ADMIN_PASS"
echo ""
echo "  Deployer:"
echo "    Username: $DEPLOY_USER"
echo "    Password: $DEPLOY_PASS"
echo ""
echo "Saved to: /tmp/nexus-admin-password"
echo ""
echo "Next step: Run publish-to-nexus.sh to upload packages"
echo ""

#!/bin/bash
# Fix Nexus admin user permissions
# This resolves the "permission was not present" errors in the UI

set -e

NEXUS_URL="${NEXUS_URL:-http://localhost:28081}"
NEXUS_USER="admin"
NEXUS_PASS="${NEXUS_ADMIN_PASSWORD:-nexus_admin_2025_change_me}"

echo "=================================================="
echo "Nexus Permission Fix"
echo "=================================================="
echo ""
echo "Fixing admin user permissions..."
echo ""

# The issue: admin user exists but doesn't have proper role assignments
# Solution: Ensure admin user has nx-admin role

# Method 1: Via Groovy script (if API allows)
echo "Attempting to fix permissions via API..."

# Create a Groovy script to fix permissions
GROOVY_SCRIPT='
import org.sonatype.nexus.security.user.UserManager
import org.sonatype.nexus.security.role.RoleIdentifier

def userManager = security.securitySystem.getUser("admin")
def roles = new HashSet()
roles.add(new RoleIdentifier("default", "nx-admin"))

security.securitySystem.setUsersRoles(userManager.userId, userManager.source, roles)

log.info("Admin user roles updated")
return "OK"
'

# Try to upload and run the script
SCRIPT_NAME="fix-admin-permissions"

# First, try to create the script
CREATE_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST \
  "$NEXUS_URL/service/rest/v1/script" \
  -u "$NEXUS_USER:$NEXUS_PASS" \
  -H "Content-Type: application/json" \
  -d "{
    \"name\": \"$SCRIPT_NAME\",
    \"type\": \"groovy\",
    \"content\": $(echo "$GROOVY_SCRIPT" | jq -Rs .)
  }" 2>&1)

HTTP_CODE=$(echo "$CREATE_RESPONSE" | tail -n1)

if [ "$HTTP_CODE" = "204" ] || [ "$HTTP_CODE" = "200" ]; then
    echo "✓ Script created successfully"

    # Run the script
    RUN_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST \
      "$NEXUS_URL/service/rest/v1/script/$SCRIPT_NAME/run" \
      -u "$NEXUS_USER:$NEXUS_PASS" \
      -H "Content-Type: text/plain")

    RUN_HTTP_CODE=$(echo "$RUN_RESPONSE" | tail -n1)

    if [ "$RUN_HTTP_CODE" = "200" ]; then
        echo "✓ Permissions fixed successfully"

        # Clean up the script
        curl -s -X DELETE \
          "$NEXUS_URL/service/rest/v1/script/$SCRIPT_NAME" \
          -u "$NEXUS_USER:$NEXUS_PASS" > /dev/null 2>&1
    else
        echo "⚠️  Script execution returned HTTP $RUN_HTTP_CODE"
    fi
else
    echo "⚠️  API method not available (HTTP $HTTP_CODE)"
fi

echo ""
echo "=================================================="
echo "Manual Fix (If API method failed)"
echo "=================================================="
echo ""
echo "Since Nexus OSS Community Edition has limited API access,"
echo "you may need to fix this via the UI:"
echo ""
echo "1. Access Nexus UI: $NEXUS_URL"
echo "2. Login as admin"
echo "3. Click Settings (gear icon)"
echo "4. Go to Security → Users"
echo "5. Click on 'admin' user"
echo "6. In 'Granted Roles', ensure these are present:"
echo "   - nx-admin (Administrator)"
echo "   - nx-anonymous"
echo "7. Click 'Save'"
echo ""

echo "=================================================="
echo "Alternative: Create Fresh Admin User"
echo "=================================================="
echo ""
echo "If the above doesn't work, create a new admin user:"
echo ""
echo "1. In Nexus UI: Security → Users → Create local user"
echo "2. Fill in:"
echo "   ID: admin2"
echo "   First Name: Admin"
echo "   Last Name: User"
echo "   Email: admin@maestro.local"
echo "   Password: [secure-password]"
echo "   Status: Active"
echo "   Granted Roles: nx-admin"
echo "3. Click Create"
echo "4. Test with new user"
echo ""

echo "=================================================="
echo "Database Method (Advanced - Use with Caution)"
echo "=================================================="
echo ""
echo "If all else fails, we can directly fix the database:"
echo ""
cat <<'DBFIX'
# Stop Nexus
docker stop maestro-nexus

# Backup database
docker run --rm -v maestro_nexus_data:/data -v $(pwd):/backup \
  alpine tar czf /backup/nexus-data-backup.tar.gz /data

# The issue is in the OrientDB database
# This requires specialized tools and is risky

# Better approach: Delete data and start fresh
# docker volume rm maestro_nexus_data
# docker-compose -f docker-compose.artifacts-minimal.yml up -d

# Then complete first-time setup properly
DBFIX

echo ""
echo "=================================================="
echo "Recommended Approach"
echo "=================================================="
echo ""
echo "Given the permission issues, the cleanest solution is:"
echo ""
echo "1. **Reset Nexus** (if acceptable - loses existing data):"
echo "   cd /home/ec2-user/projects/maestro-platform/infrastructure"
echo "   docker-compose -f docker-compose.artifacts-minimal.yml down"
echo "   docker volume rm maestro_nexus_data"
echo "   docker-compose -f docker-compose.artifacts-minimal.yml up -d"
echo ""
echo "2. **Complete first-time setup properly**:"
echo "   - Wait 2 minutes for Nexus to start"
echo "   - Get initial password:"
echo "     docker exec maestro-nexus cat /nexus-data/admin.password"
echo "   - Access UI and complete wizard"
echo "   - Change password"
echo "   - Enable realms"
echo "   - Create PyPI repositories"
echo ""
echo "3. **Upload packages**:"
echo "   cd /home/ec2-user/projects/maestro-platform/shared"
echo "   ./publish-to-nexus.sh"
echo ""

echo "=================================================="
echo "Status Check"
echo "=================================================="
echo ""
echo "Current admin user status:"
curl -s -u "$NEXUS_USER:$NEXUS_PASS" \
  "$NEXUS_URL/service/rest/v1/security/users?userId=admin" 2>/dev/null | \
  python3 -c "import sys, json; data=sys.stdin.read(); print(json.dumps(json.loads(data) if data else {}, indent=2))" 2>/dev/null || \
  echo "Could not retrieve user info (API may be restricted)"

echo ""
echo "For more help, see:"
echo "  /infrastructure/docs/NEXUS_PYPI_SETUP.md"
echo ""

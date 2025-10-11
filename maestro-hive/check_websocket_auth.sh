#!/bin/bash

# Sunday.com WebSocket Authentication Troubleshooter
# This script helps diagnose WebSocket authentication issues

set -e

BACKEND_URL="${BACKEND_URL:-http://3.10.213.208:8006}"
BACKEND_HOST="${BACKEND_HOST:-3.10.213.208}"
BACKEND_PORT="${BACKEND_PORT:-8006}"
FRONTEND_PORT="${FRONTEND_PORT:-3006}"

echo "============================================"
echo "Sunday.com WebSocket Authentication Checker"
echo "============================================"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_status() {
    local status=$1
    local message=$2
    
    if [ "$status" = "ok" ]; then
        echo -e "${GREEN}✅ $message${NC}"
    elif [ "$status" = "fail" ]; then
        echo -e "${RED}❌ $message${NC}"
    elif [ "$status" = "warn" ]; then
        echo -e "${YELLOW}⚠️  $message${NC}"
    else
        echo -e "ℹ️  $message"
    fi
}

# Step 1: Check Backend Health
echo "📍 Step 1: Checking Backend Status"
echo "-----------------------------------"

if curl -s -f "${BACKEND_URL}/api/v1/health" > /dev/null 2>&1; then
    HEALTH_DATA=$(curl -s "${BACKEND_URL}/api/v1/health")
    print_status "ok" "Backend is running at ${BACKEND_URL}"
    echo "   Health data: ${HEALTH_DATA}"
else
    print_status "fail" "Backend is NOT accessible at ${BACKEND_URL}"
    echo ""
    echo "   Please start the backend:"
    echo "   cd sunday_com/backend && npm run dev"
    exit 1
fi

echo ""

# Step 2: Check if Backend Process is Running
echo "📍 Step 2: Checking Backend Process"
echo "-----------------------------------"

BACKEND_PROCESS=$(ps aux | grep -E "[n]ode.*${BACKEND_PORT}|[n]ode.*backend" | head -1)
if [ -n "$BACKEND_PROCESS" ]; then
    print_status "ok" "Backend process is running"
    echo "   Process: $(echo $BACKEND_PROCESS | awk '{print $11, $12, $13}')"
else
    print_status "warn" "Cannot find backend process (might be using a different pattern)"
fi

echo ""

# Step 3: Test Authentication Endpoint
echo "📍 Step 3: Testing Authentication Endpoint"
echo "-----------------------------------"

# Test with intentionally invalid credentials to check if endpoint works
AUTH_TEST=$(curl -s -w "\n%{http_code}" -X POST "${BACKEND_URL}/api/v1/auth/login" \
    -H "Content-Type: application/json" \
    -d '{"email":"test@test.com","password":"short"}' 2>&1)

HTTP_CODE=$(echo "$AUTH_TEST" | tail -1)
if [ "$HTTP_CODE" = "400" ] || [ "$HTTP_CODE" = "401" ] || [ "$HTTP_CODE" = "422" ]; then
    print_status "ok" "Authentication endpoint is responding (status: $HTTP_CODE)"
    echo "   Endpoint: ${BACKEND_URL}/api/v1/auth/login"
else
    print_status "fail" "Authentication endpoint returned unexpected status: $HTTP_CODE"
fi

echo ""

# Step 4: Test Token Refresh Endpoint
echo "📍 Step 4: Testing Token Refresh Endpoint"
echo "-----------------------------------"

REFRESH_TEST=$(curl -s -w "\n%{http_code}" -X POST "${BACKEND_URL}/api/v1/auth/refresh" \
    -H "Content-Type: application/json" \
    -d '{"refreshToken":"invalid"}' 2>&1)

HTTP_CODE=$(echo "$REFRESH_TEST" | tail -1)
if [ "$HTTP_CODE" = "401" ] || [ "$HTTP_CODE" = "400" ]; then
    print_status "ok" "Token refresh endpoint is responding (status: $HTTP_CODE)"
else
    print_status "warn" "Token refresh endpoint returned status: $HTTP_CODE"
fi

echo ""

# Step 5: Check Frontend Process
echo "📍 Step 5: Checking Frontend Status"
echo "-----------------------------------"

FRONTEND_PROCESS=$(ps aux | grep -E "[n]ode.*${FRONTEND_PORT}|[n]pm.*dev" | grep -v grep | head -1)
if [ -n "$FRONTEND_PROCESS" ]; then
    print_status "ok" "Frontend process is running on port ${FRONTEND_PORT}"
    echo "   Process: $(echo $FRONTEND_PROCESS | awk '{print $11, $12, $13}')"
else
    print_status "warn" "Cannot find frontend process on port ${FRONTEND_PORT}"
    echo "   Frontend might be running on a different port"
fi

echo ""

# Step 6: Check JWT Configuration
echo "📍 Step 6: Checking JWT Configuration"
echo "-----------------------------------"

BACKEND_ENV="sunday_com/backend/.env"
if [ -f "$BACKEND_ENV" ]; then
    JWT_SECRET=$(grep "^JWT_SECRET=" "$BACKEND_ENV" | cut -d'=' -f2)
    JWT_EXPIRES=$(grep "^JWT_EXPIRES_IN=" "$BACKEND_ENV" | cut -d'=' -f2)
    
    if [ -n "$JWT_SECRET" ]; then
        print_status "ok" "JWT_SECRET is configured"
        echo "   Secret length: ${#JWT_SECRET} characters"
        
        if [ "$JWT_SECRET" = "dev-secret-key-for-testing-only" ]; then
            print_status "warn" "Using development JWT secret (OK for testing)"
        fi
    else
        print_status "fail" "JWT_SECRET is missing in .env"
    fi
    
    if [ -n "$JWT_EXPIRES" ]; then
        print_status "ok" "JWT expiration set to: $JWT_EXPIRES"
    fi
else
    print_status "fail" "Backend .env file not found at: $BACKEND_ENV"
fi

echo ""

# Step 7: Provide Manual Testing Instructions
echo "📍 Step 7: Manual Testing Instructions"
echo "-----------------------------------"
echo ""
echo "To test WebSocket authentication manually:"
echo ""
echo "1️⃣  Open the debug tool in your browser:"
echo "   file://$(pwd)/sunday_com/websocket_debug.html"
echo ""
echo "2️⃣  Or test in browser console on the frontend (port ${FRONTEND_PORT}):"
echo "   // Check if token exists"
echo "   localStorage.getItem('sunday_auth_token')"
echo ""
echo "   // Check if authenticated"
echo "   webSocketService.isConnected()"
echo ""
echo "3️⃣  If no token, perform login:"
echo "   - Navigate to: http://localhost:${FRONTEND_PORT}/auth/login"
echo "   - Login with valid credentials (password must be 8+ chars)"
echo "   - WebSocket should connect automatically after login"
echo ""
echo "4️⃣  Test login via curl:"
cat << 'EOF'
   curl -X POST http://3.10.213.208:8006/api/v1/auth/login \
     -H "Content-Type: application/json" \
     -d '{
       "email": "testuser@example.com",
       "password": "password123"
     }'
EOF
echo ""

# Step 8: Summary
echo ""
echo "============================================"
echo "Summary"
echo "============================================"
echo ""

ISSUES_FOUND=0

# Backend check
if curl -s -f "${BACKEND_URL}/api/v1/health" > /dev/null 2>&1; then
    print_status "ok" "Backend: Running and accessible"
else
    print_status "fail" "Backend: Not accessible"
    ISSUES_FOUND=$((ISSUES_FOUND + 1))
fi

# JWT config check
if [ -f "$BACKEND_ENV" ] && grep -q "^JWT_SECRET=" "$BACKEND_ENV"; then
    print_status "ok" "Configuration: JWT secret configured"
else
    print_status "fail" "Configuration: JWT secret missing"
    ISSUES_FOUND=$((ISSUES_FOUND + 1))
fi

echo ""
echo "-----------------------------------"

if [ $ISSUES_FOUND -eq 0 ]; then
    echo -e "${GREEN}✅ All checks passed!${NC}"
    echo ""
    echo "If WebSocket authentication is still failing, the most likely cause is:"
    echo "  1. User is not logged in (no token in localStorage)"
    echo "  2. Token has expired (default: 24 hours)"
    echo "  3. Token is invalid or corrupted"
    echo ""
    echo "✅ Next steps:"
    echo "  • Log in to the frontend application"
    echo "  • Verify token is stored: localStorage.getItem('sunday_auth_token')"
    echo "  • Check WebSocket connection: webSocketService.isConnected()"
    echo ""
    echo "📄 For detailed guidance, see:"
    echo "  • sunday_com_websocket_fix_action_plan.md"
    echo "  • sunday_com_websocket_authentication_analysis.md"
else
    echo -e "${RED}❌ Found $ISSUES_FOUND issue(s) that need to be fixed${NC}"
    echo ""
    echo "Please address the issues above before testing WebSocket authentication."
fi

echo ""
echo "============================================"

#!/bin/bash

# Health Check Script for Sunday.com Platform
# Checks both frontend (nginx) and backend (API) health

set -euo pipefail

# Configuration
FRONTEND_URL="http://localhost:80"
BACKEND_URL="http://localhost:3000"
HEALTH_ENDPOINT="/health"
MAX_RETRIES=3
RETRY_DELAY=5
DAEMON_MODE=false

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "$(date '+%Y-%m-%d %H:%M:%S') - $1"
}

# Check if daemon mode is requested
if [[ "${1:-}" == "--daemon" ]]; then
    DAEMON_MODE=true
fi

# Health check function
check_service() {
    local service_name=$1
    local url=$2
    local retries=0

    while [ $retries -lt $MAX_RETRIES ]; do
        if curl -f -s --max-time 10 "$url" > /dev/null 2>&1; then
            log "${GREEN}✅ $service_name is healthy${NC}"
            return 0
        else
            retries=$((retries + 1))
            if [ $retries -lt $MAX_RETRIES ]; then
                log "${YELLOW}⚠️  $service_name check failed (attempt $retries/$MAX_RETRIES), retrying in ${RETRY_DELAY}s...${NC}"
                sleep $RETRY_DELAY
            fi
        fi
    done

    log "${RED}❌ $service_name is unhealthy after $MAX_RETRIES attempts${NC}"
    return 1
}

# Detailed health check function
detailed_health_check() {
    local backend_healthy=false
    local frontend_healthy=false

    # Check backend health endpoint
    log "🔍 Checking backend health..."
    if response=$(curl -s --max-time 10 "$BACKEND_URL$HEALTH_ENDPOINT" 2>/dev/null); then
        if echo "$response" | grep -q '"status":"healthy"'; then
            backend_healthy=true
            log "${GREEN}✅ Backend API is healthy${NC}"

            # Extract additional info if available
            if uptime=$(echo "$response" | grep -o '"uptime":[0-9.]*' | cut -d':' -f2); then
                log "   📊 Backend uptime: ${uptime}s"
            fi
        else
            log "${RED}❌ Backend API returned unhealthy status${NC}"
            log "   Response: $response"
        fi
    else
        log "${RED}❌ Backend API is not responding${NC}"
    fi

    # Check frontend
    log "🔍 Checking frontend..."
    if check_service "Frontend" "$FRONTEND_URL"; then
        frontend_healthy=true
    fi

    # Overall health status
    if $backend_healthy && $frontend_healthy; then
        log "${GREEN}🎉 All services are healthy${NC}"
        return 0
    else
        log "${RED}💥 One or more services are unhealthy${NC}"
        return 1
    fi
}

# Daemon mode function
run_daemon() {
    log "🚀 Starting health check daemon..."
    while true; do
        if ! detailed_health_check; then
            log "${RED}🚨 Health check failed - services may need attention${NC}"
        fi
        sleep 30  # Check every 30 seconds
    done
}

# Main execution
if $DAEMON_MODE; then
    run_daemon
else
    detailed_health_check
fi
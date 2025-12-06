#!/bin/bash
# ==============================================================================
# Status Dashboard Runner
# MD-2033: Web-Based Service Status Dashboard
# ==============================================================================

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}   Maestro Status Dashboard${NC}"
echo -e "${GREEN}============================================${NC}"
echo ""

# Check for Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}ERROR: Python 3 is required${NC}"
    exit 1
fi

# Check/install dependencies
echo -e "${YELLOW}Checking dependencies...${NC}"
pip3 install -q -r requirements.txt 2>/dev/null || pip install -q -r requirements.txt 2>/dev/null || {
    echo -e "${YELLOW}Installing dependencies...${NC}"
    pip3 install flask flask-cors requests
}

# Set environment variables
export PORT=${PORT:-8080}
export DEBUG=${DEBUG:-false}
export SECRET_KEY=${SECRET_KEY:-maestro-status-dashboard-secret-2024}
export ADMIN_USERNAME=${ADMIN_USERNAME:-admin}
export ADMIN_PASSWORD=${ADMIN_PASSWORD:-maestro_status_2024}

echo ""
echo -e "${GREEN}Starting Status Dashboard on port ${PORT}...${NC}"
echo ""
echo "Access URLs:"
echo "  Dashboard: http://localhost:${PORT}"
echo "  Health:    http://localhost:${PORT}/health"
echo ""
echo "Credentials:"
echo "  Username: ${ADMIN_USERNAME}"
echo "  Password: ${ADMIN_PASSWORD}"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop${NC}"
echo ""

# Run the app
python3 app.py

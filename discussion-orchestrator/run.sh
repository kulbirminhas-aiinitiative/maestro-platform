#!/bin/bash

# Discussion Orchestrator Service Startup Script

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting Discussion Orchestrator Service${NC}"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Virtual environment not found. Creating one...${NC}"
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Check if dependencies are installed
if ! python -c "import fastapi" 2>/dev/null; then
    echo -e "${YELLOW}Installing dependencies...${NC}"
    pip install -r requirements.txt
fi

# Check if .env exists
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}.env file not found. Copying from .env.example${NC}"
    cp .env.example .env
    echo -e "${RED}Please configure .env file before starting the service${NC}"
    exit 1
fi

# Check if Redis is running
if ! redis-cli ping &>/dev/null; then
    echo -e "${RED}Redis is not running. Please start Redis first:${NC}"
    echo "  sudo systemctl start redis"
    echo "  or"
    echo "  redis-server"
    exit 1
fi

echo -e "${GREEN}Starting service on port 5000...${NC}"
echo -e "${GREEN}API Documentation: http://localhost:5000/docs${NC}"
echo -e "${GREEN}Health Check: http://localhost:5000/health${NC}"
echo ""

# Run the service
python -m uvicorn src.main:app --host 0.0.0.0 --port 5000 --reload
